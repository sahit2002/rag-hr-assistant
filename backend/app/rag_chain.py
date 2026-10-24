"""
Step 5 — LCEL RAG Chain

Wires: query_router → FAISS retrieval → cross-encoder re-rank → LLM generation.
Returns structured output: answer text + source chunks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq

from app.config import settings
from app.query_router import route_and_expand
from app.reranker import rerank
from app.vector_store import query_index

_llm: ChatGroq | None = None


def _get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
            raise RuntimeError(
                "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your environment variables."
            )
        _llm = ChatGroq(
            model=settings.groq_model,
            temperature=0.2,
            groq_api_key=settings.groq_api_key,
        )
    return _llm


_RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an HR Policy assistant.
Answer the question using ONLY the provided context.
If the context does not contain the answer, say exactly:
  "I could not find this information in the provided HR policy documents."
Be concise and factual. Do not speculate beyond the context.""",
        ),
        (
            "human",
            """Context:
{context}

Question: {question}""",
        ),
    ]
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_context(docs: List[Document]) -> str:
    parts = []
    for doc in docs:
        src = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        parts.append(f"[{src}, p.{page}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def _source_dicts(ranked: List[Tuple[Document, float]]) -> List[Dict[str, Any]]:
    sources = []
    for doc, score in ranked:
        sources.append(
            {
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page", "?"),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "doc_id": doc.metadata.get("doc_id", ""),
                "score": round(score, 4),
                "text": doc.page_content[:400],
            }
        )
    return sources


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_rag(question: str) -> Dict[str, Any]:
    """
    Full RAG pipeline for a single user question.

    Returns:
      {
        "answer": str,
        "sources": [{"source", "page", "chunk_index", "doc_id", "score", "text"}],
        "query_type": str,
        "sub_queries": list[str],
      }
    """
    # Step 6: routing & decomposition
    sub_queries = route_and_expand(question)

    # Retrieve for every sub-query and merge (deduplicate by doc_id)
    seen_ids: set = set()
    all_candidates: List[Tuple[Document, float]] = []
    for sq in sub_queries:
        try:
            hits = query_index(sq, k=settings.top_k_retrieval)
        except RuntimeError:
            raise
        for doc, score in hits:
            did = doc.metadata.get("doc_id", "")
            if did not in seen_ids:
                seen_ids.add(did)
                all_candidates.append((doc, score))

    # Step 7: re-rank
    ranked = rerank(question, all_candidates, top_k=settings.top_k_rerank)
    top_docs = [doc for doc, _ in ranked]

    # Step 5: LCEL chain for generation
    context_str = _format_context(top_docs)

    chain = (
        RunnablePassthrough()
        | _RAG_PROMPT
        | _get_llm()
        | StrOutputParser()
    )
    answer: str = chain.invoke({"context": context_str, "question": question})

    return {
        "answer": answer,
        "sources": _source_dicts(ranked),
        "query_type": "multi_part" if len(sub_queries) > 1 else "single_fact",
        "sub_queries": sub_queries,
    }
