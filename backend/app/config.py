"""
Application configuration — reads from .env
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str = "llama3-70b-8192"
    faiss_index_path: str = "data/faiss_index"
    pdf_upload_dir: str = "data/pdfs"
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    chunk_size: int = 700
    chunk_overlap: int = 80
    top_k_retrieval: int = 10
    top_k_rerank: int = 4

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure required directories exist
Path(settings.faiss_index_path).mkdir(parents=True, exist_ok=True)
Path(settings.pdf_upload_dir).mkdir(parents=True, exist_ok=True)
