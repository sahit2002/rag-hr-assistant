"""
Step 7 — Lightweight Scoring

Ranks candidate chunks using FAISS cosine similarity scores directly.
Eliminates second heavy transformer model to save ~180MB of RAM.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


def rerank(
    question: str,
    candidates: List[Tuple[Document, float]],
    top_k: int | None = None,
) -> List[Tuple[Document, float]]:
    """
    Lightweight scoring: sorts candidate (Document, similarity_score)
    pairs by score descending and returns the top_k chunks.
    Zero extra model loading and ultra-low RAM footprint.
    """
    if not candidates:
        return []

    top_k = top_k or settings.top_k_rerank

    # Sort candidates by similarity score descending
    ranked = sorted(candidates, key=lambda x: x[1], reverse=True)

    results = [(doc, float(score)) for doc, score in ranked[:top_k]]
    logger.debug(f"Retrieved top {len(results)} chunks using cosine similarity.")
    return results
