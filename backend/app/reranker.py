"""
Step 7 — Cross-Encoder Re-Ranking

Uses cross-encoder/ms-marco-MiniLM-L-6-v2 to re-score the top-N
chunks retrieved from FAISS, then returns top_k_rerank chunks.

Logs pre-rank and post-rank ordering for README comparison.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from app.config import settings

logger = logging.getLogger(__name__)

_CROSS_ENCODER: CrossEncoder | None = None


def _get_reranker() -> CrossEncoder:
    global _CROSS_ENCODER
    if _CROSS_ENCODER is None:
        _CROSS_ENCODER = CrossEncoder(settings.reranker_model)
    return _CROSS_ENCODER


def rerank(
    question: str,
    candidates: List[Tuple[Document, float]],
    top_k: int | None = None,
) -> List[Tuple[Document, float]]:
    """
    Re-rank candidate (Document, retrieval_score) pairs using a cross-encoder.

    Returns top_k (Document, cross_encoder_score) pairs, highest first.
    Also logs pre- vs post-rerank ordering at DEBUG level.
    """
    if not candidates:
        return []

    top_k = top_k or settings.top_k_rerank
    reranker = _get_reranker()

    pairs = [(question, doc.page_content) for doc, _ in candidates]
    ce_scores: List[float] = reranker.predict(pairs).tolist()

    # Log pre-rerank order
    pre_order = [
        f"[{i+1}] src={doc.metadata.get('source','?')} p={doc.metadata.get('page','?')} score={s:.4f}"
        for i, ((doc, s), _) in enumerate(zip(candidates, ce_scores))
    ]
    logger.debug("Pre-rerank order:\n  " + "\n  ".join(pre_order))

    # Sort by cross-encoder score descending
    ranked = sorted(
        zip(candidates, ce_scores),
        key=lambda x: x[1],
        reverse=True,
    )

    results = [(doc, float(ce_score)) for (doc, _), ce_score in ranked[:top_k]]

    # Log post-rerank order
    post_order = [
        f"[{i+1}] src={doc.metadata.get('source','?')} p={doc.metadata.get('page','?')} ce_score={s:.4f}"
        for i, (doc, s) in enumerate(results)
    ]
    logger.debug("Post-rerank order:\n  " + "\n  ".join(post_order))

    return results
