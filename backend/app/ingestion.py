"""
Step 3 — PDF Ingestion & Chunking

Loads a PDF, extracts text page-by-page (preserving page numbers),
then splits into overlapping chunks with full metadata.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.config import settings


def _doc_id(filename: str, page: int, idx: int) -> str:
    """Stable, unique ID for a chunk."""
    raw = f"{filename}|p{page}|c{idx}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def load_and_chunk(pdf_path: str | Path) -> List[Document]:
    """
    Load a PDF and return a list of chunked Documents with metadata:
      - source: original filename
      - page: 1-based page number
      - chunk_index: position within the page split
      - doc_id: stable unique ID
    """
    pdf_path = Path(pdf_path)
    loader = PyPDFLoader(str(pdf_path))
    pages: List[Document] = loader.load()  # one doc per page

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: List[Document] = []
    for page_doc in pages:
        page_number = page_doc.metadata.get("page", 0) + 1  # 1-based
        sub_chunks = splitter.split_documents([page_doc])
        for idx, chunk in enumerate(sub_chunks):
            chunk.metadata.update(
                {
                    "source": pdf_path.name,
                    "page": page_number,
                    "chunk_index": idx,
                    "doc_id": _doc_id(pdf_path.name, page_number, idx),
                }
            )
            chunks.append(chunk)

    return chunks
