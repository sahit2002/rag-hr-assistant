"""
Step 6 — Query Routing & Decomposition

Classifies a user query into one of three types:
  - single_fact   : straightforward lookup
  - multi_part    : compound question with multiple sub-questions
  - summarization : asks for a summary / overview

Multi-part queries are decomposed into sub-queries before retrieval.
"""
from __future__ import annotations

import re
from typing import List, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.config import settings

QueryType = Literal["single_fact", "multi_part", "summarization"]

_llm = ChatGroq(
    model=settings.groq_model,
    temperature=0,
    groq_api_key=settings.groq_api_key,
)

# ── Routing ──────────────────────────────────────────────────────────────────

_ROUTE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a query classifier for an HR Policy assistant.
Classify the user query into exactly one of:
  single_fact    — asks for one specific fact, rule, or policy detail
  multi_part     — contains multiple distinct sub-questions
  summarization  — asks for a summary or overview of a topic

Reply with ONLY the label, nothing else.""",
        ),
        ("human", "{query}"),
    ]
)


def classify_query(query: str) -> QueryType:
    chain = _ROUTE_PROMPT | _llm
    result = chain.invoke({"query": query})
    label = result.content.strip().lower()
    if label in ("single_fact", "multi_part", "summarization"):
        return label  # type: ignore[return-value]
    # Fallback: heuristic
    if "?" in query and query.count("?") > 1:
        return "multi_part"
    if any(w in query.lower() for w in ("summarize", "overview", "describe", "explain all")):
        return "summarization"
    return "single_fact"


# ── Decomposition ─────────────────────────────────────────────────────────────

_DECOMPOSE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a query decomposer for an HR Policy assistant.
Break the user question into individual sub-questions, one per line.
Output ONLY the sub-questions, numbered 1. 2. 3. etc.
Do not add any commentary.""",
        ),
        ("human", "{query}"),
    ]
)


def decompose_query(query: str) -> List[str]:
    chain = _DECOMPOSE_PROMPT | _llm
    result = chain.invoke({"query": query})
    lines = result.content.strip().splitlines()
    sub_queries: List[str] = []
    for line in lines:
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
        if cleaned:
            sub_queries.append(cleaned)
    return sub_queries or [query]


# ── Public entry-point ────────────────────────────────────────────────────────

def route_and_expand(query: str) -> List[str]:
    """
    Returns a list of queries to retrieve for.
    - single_fact / summarization: returns [query]
    - multi_part: returns the decomposed sub-queries
    """
    qtype = classify_query(query)
    if qtype == "multi_part":
        return decompose_query(query)
    return [query]
