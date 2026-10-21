"""
Step 4 — Local Embeddings & FAISS Index

Uses sentence-transformers/all-MiniLM-L6-v2 (zero API cost).
Builds / updates a FAISS index persisted to disk.
Exposes query_index(question, k) → list of (Document, score).
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer

from app.config import settings

_EMBED_MODEL: SentenceTransformer | None = None
_INDEX: faiss.Index | None = None
_DOCS: List[Document] = []

_INDEX_FILE = Path(settings.faiss_index_path) / "index.faiss"
_DOCS_FILE = Path(settings.faiss_index_path) / "docs.pkl"
_META_FILE = Path(settings.faiss_index_path) / "meta.json"


def _get_embed_model() -> SentenceTransformer:
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer(settings.embed_model)
    return _EMBED_MODEL


def _embed(texts: List[str]) -> np.ndarray:
    model = _get_embed_model()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vecs.astype(np.float32)


# ── Persistence ──────────────────────────────────────────────────────────────

def save_index() -> None:
    faiss.write_index(_INDEX, str(_INDEX_FILE))
    with open(_DOCS_FILE, "wb") as f:
        pickle.dump(_DOCS, f)
    with open(_META_FILE, "w") as f:
        json.dump({"total_chunks": len(_DOCS)}, f)


def load_index() -> bool:
    """Load persisted index from disk.  Returns True if successful."""
    global _INDEX, _DOCS
    if _INDEX_FILE.exists() and _DOCS_FILE.exists():
        _INDEX = faiss.read_index(str(_INDEX_FILE))
        with open(_DOCS_FILE, "rb") as f:
            _DOCS = pickle.load(f)
        return True
    return False


# ── Build / Update ────────────────────────────────────────────────────────────

def build_index(chunks: List[Document]) -> None:
    """
    Embed chunks and build (or extend) the FAISS flat-IP index.
    Duplicate doc_ids are skipped to allow incremental ingestion.
    """
    global _INDEX, _DOCS

    # Load existing if present
    if _INDEX is None:
        load_index()

    existing_ids = {d.metadata["doc_id"] for d in _DOCS}
    new_chunks = [c for c in chunks if c.metadata["doc_id"] not in existing_ids]
    if not new_chunks:
        return

    texts = [c.page_content for c in new_chunks]
    vecs = _embed(texts)
    dim = vecs.shape[1]

    if _INDEX is None:
        _INDEX = faiss.IndexFlatIP(dim)  # inner-product on normalised vecs == cosine

    _INDEX.add(vecs)
    _DOCS.extend(new_chunks)
    save_index()


# ── Query ─────────────────────────────────────────────────────────────────────

def query_index(question: str, k: int | None = None) -> List[Tuple[Document, float]]:
    """
    Return top-k (Document, cosine_score) pairs for the given question.
    Raises RuntimeError if the index has not been built yet.
    """
    global _INDEX, _DOCS
    if _INDEX is None:
        loaded = load_index()
        if not loaded or _INDEX is None:
            raise RuntimeError(
                "FAISS index is empty. Please upload and index a PDF first."
            )

    k = k or settings.top_k_retrieval
    k = min(k, _INDEX.ntotal)

    q_vec = _embed([question])
    scores, indices = _INDEX.search(q_vec, k)

    results: List[Tuple[Document, float]] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        results.append((_DOCS[idx], float(score)))
    return results


def get_index_stats() -> dict:
    global _INDEX, _DOCS
    if _INDEX is None:
        load_index()
    return {
        "total_chunks": len(_DOCS),
        "indexed": _INDEX.ntotal if _INDEX else 0,
        "sources": list({d.metadata.get("source", "unknown") for d in _DOCS}),
    }
