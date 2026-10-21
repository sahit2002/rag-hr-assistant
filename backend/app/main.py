"""
FastAPI application — HR Policy RAG Assistant

Endpoints:
  POST /ingest          Upload & index a PDF
  POST /query           Ask a question
  GET  /status          Index stats
  GET  /health          Health check
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.ingestion import load_and_chunk
from app.rag_chain import run_rag
from app.vector_store import build_index, get_index_stats

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HR Policy RAG Assistant",
    description="Single-source RAG for HR Policy documents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    source: str
    page: Any
    chunk_index: int
    doc_id: str
    score: float
    text: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    query_type: str
    sub_queries: List[str]


class IngestResponse(BaseModel):
    filename: str
    chunks_added: int
    total_indexed: int


class StatusResponse(BaseModel):
    total_chunks: int
    indexed: int
    sources: List[str]


# ── Endpoints ──────────────────────────────────────────────────────────────────

router = APIRouter()


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    stats = get_index_stats()
    return StatusResponse(**stats)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_pdf(file: UploadFile = File(...)) -> IngestResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    dest = Path(settings.pdf_upload_dir) / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    chunks = load_and_chunk(dest)
    before = get_index_stats()["total_chunks"]
    build_index(chunks)
    after = get_index_stats()["total_chunks"]

    return IngestResponse(
        filename=file.filename,
        chunks_added=after - before,
        total_indexed=after,
    )


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    try:
        result = run_rag(request.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("RAG pipeline error")
        raise HTTPException(status_code=500, detail=str(exc))

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
        query_type=result["query_type"],
        sub_queries=result["sub_queries"],
    )


app.include_router(router)
app.include_router(router, prefix="/api")
