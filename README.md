# HR Policy RAG Assistant

A **Retrieval-Augmented Generation (RAG)** assistant for HR policy documents. Upload an HR policy PDF, ask natural-language questions, and get answers grounded strictly in the document, with cited page numbers.

## Table of contents

- [Scope](#scope)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Re-ranking: before vs after](#re-ranking-before-vs-after)
- [Deployment](#deployment)
- [Project structure](#project-structure)
- [Known gaps](#known-gaps)

## Scope

**In scope:** questions about HR policies in the uploaded PDF documents, such as leave entitlement, disciplinary procedures, remote work, compensation and onboarding.

**Out of scope:** legal or medical advice, cross-document synthesis across unrelated domains, real-time regulatory lookup, multi-document hybrid search and GraphRAG. The assistant states explicitly when a question falls outside the indexed documents.

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                        User (Browser)                        │
└─────────────────────────┬────────────────────────────────────┘
                          │  HTTP / JSON
┌─────────────────────────▼────────────────────────────────────┐
│                 Next.js Frontend (port 3000)                 │
│   UploadBox │ QuestionBox │ AnswerDisplay │ SourcesPanel       │
└─────────────────────────┬────────────────────────────────────┘
                          │  REST API
┌─────────────────────────▼────────────────────────────────────┐
│                 FastAPI Backend (port 8000)                  │
│                                                              │
│  POST /ingest ──► ingestion.py ──► vector_store.py           │
│                   (PyPDF + RecursiveCharacterTextSplitter)   │
│                   (SentenceTransformers + FAISS-CPU)         │
│                                                              │
│  POST /query  ──► query_router.py  (classify / decompose)    │
│               ──► vector_store.query_index()  (FAISS k-NN)   │
│               ──► reranker.py      (CrossEncoder ms-marco)   │
│               ──► rag_chain.py     (LCEL + Groq LLM)         │
│               ◄── structured JSON (answer + sources)         │
└──────────────────────────────────────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │  data/faiss_index/    │
              │  ├── index.faiss      │
              │  ├── docs.pkl         │
              │  └── meta.json        │
              └───────────────────────┘
```

## Tech stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS | Upload, question, answer and sources UI |
| Backend API | FastAPI 0.111 + Uvicorn | REST endpoints |
| PDF ingestion | PyPDF 4 | Page-level text extraction |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | 700-character chunks, 80-character overlap (configurable) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Local, zero-cost, 384-dim vectors |
| Vector store | FAISS-CPU `IndexFlatIP` | Cosine similarity on normalised vectors |
| Re-ranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder re-scoring of the top 10, keeping the top 4 |
| LLM | Groq `llama-3.3-70b-versatile` via LangChain LCEL | Answer generation (free tier available) |
| Query routing | LangChain + Groq | `single_fact` / `multi_part` / `summarization` |

## Quickstart

### Prerequisites

- Python 3.10+
- Node.js 18+
- A Groq API key (free, from [console.groq.com](https://console.groq.com))

### Fastest way: `app.sh`

```bash
./app.sh            # set up (first run) and start backend + frontend; Ctrl+C stops both
./app.sh backend    # backend only
./app.sh frontend   # frontend only
./app.sh setup      # create env files, venv and install dependencies only
```

Set `GROQ_API_KEY` in `backend/.env` after the first run. Change ports with `BACKEND_PORT` and `FRONTEND_PORT`. The manual steps follow.


### 1. Clone and configure

```bash
git clone <your-repo-url>
cd rag-hr-assistant

cp backend/.env.example backend/.env           # then set GROQ_API_KEY
cp frontend/.env.example frontend/.env.local   # NEXT_PUBLIC_API_URL defaults to http://localhost:8000
```

### 2. Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Run the frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:3000
```

### 4. Ingest a PDF

Drag and drop a PDF in the browser, or use curl:

```bash
curl -X POST http://localhost:8000/ingest \
     -F "file=@/path/to/hr-policy.pdf"
```

### 5. Ask a question

```bash
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"question": "How many annual leave days do I get?"}'
```

### 6. Lint and type-check

```bash
# Backend
cd backend && flake8 --max-line-length=120 app main.py

# Frontend
cd frontend && npx tsc --noEmit && npm run lint
```

## Configuration

Backend settings are read from `backend/.env` (see [`backend/.env.example`](backend/.env.example)).

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | **Required.** Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model used for routing and answers |
| `FAISS_INDEX_PATH` | `data/faiss_index` | Where the index is persisted |
| `PDF_UPLOAD_DIR` | `data/pdfs` | Where uploaded PDFs are stored |
| `EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder model |
| `CHUNK_SIZE` | `700` | Chunk size |
| `CHUNK_OVERLAP` | `80` | Chunk overlap |
| `TOP_K_RETRIEVAL` | `10` | Candidates retrieved from FAISS |
| `TOP_K_RERANK` | `4` | Chunks kept after re-ranking |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

Frontend: set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` (default `http://localhost:8000`).

## API reference

All routes are served at the root and also under the `/api` prefix (for example `/query` and `/api/query`). Interactive docs are at `/docs`.

### `GET /health`

Returns `{"status": "ok"}`.

### `GET /status`

Returns index statistics.

```json
{
  "total_chunks": 142,
  "indexed": 142,
  "sources": ["hr-policy-2024.pdf"]
}
```

### `POST /ingest`

Uploads a PDF for chunking and indexing.

- **Request:** `multipart/form-data` with field `file` (PDF only; other types return `400`).
- **Response:**

```json
{
  "filename": "hr-policy-2024.pdf",
  "chunks_added": 142,
  "total_indexed": 142
}
```

### `POST /query`

Asks a question against the indexed documents. An empty question returns `400`; an unconfigured API key or empty index returns `503`.

- **Request:**

```json
{ "question": "What is the notice period for resignation?" }
```

- **Response:**

```json
{
  "answer": "The notice period is 4 weeks for staff and 8 weeks for managers, as stated in Section 7.",
  "sources": [
    {
      "source": "hr-policy-2024.pdf",
      "page": 12,
      "chunk_index": 2,
      "doc_id": "a1b2c3d4e5f6",
      "score": 0.8923,
      "text": "…excerpt of the relevant chunk…"
    }
  ],
  "query_type": "single_fact",
  "sub_queries": ["What is the notice period for resignation?"]
}
```

## Re-ranking: before vs after

Cross-encoder re-ranking re-orders the chunks retrieved by FAISS using a query-document relevance model. Illustrative example for *"What is the disciplinary procedure?"*:

| Rank | Pre-rerank source | FAISS score | Post-rerank source | CE score |
|---|---|---|---|---|
| 1 | hr-policy.pdf p.3 | 0.741 | hr-policy.pdf p.8 | 4.21 |
| 2 | hr-policy.pdf p.8 | 0.735 | hr-policy.pdf p.9 | 3.88 |
| 3 | hr-policy.pdf p.1 | 0.721 | hr-policy.pdf p.3 | 2.74 |
| 4 | hr-policy.pdf p.9 | 0.714 | hr-policy.pdf p.1 | 1.05 |

The cross-encoder promotes relevant but embedding-distant chunks (p.8, p.9) above surface-similar but less relevant passages (p.1, p.3).

## Deployment

The repository supports two backend targets. Set the variables from [Configuration](#configuration) in each platform's dashboard.

### Hugging Face Spaces (Docker)

The root [`Dockerfile`](Dockerfile) builds the backend and serves it on port `7860` (see the front matter at the top of this file).

### Render

[`render.yaml`](render.yaml) defines the backend service (root directory `backend`, health check `/health`):

```bash
# Build command
pip install --upgrade pip && pip install -r requirements.txt

# Start command
uvicorn main:app --host 0.0.0.0 --port $PORT
```

`GROQ_API_KEY` is not synced; set it in the Render dashboard.

### Frontend → Vercel

```bash
npm install -g vercel
cd frontend
vercel --prod
```

Set `NEXT_PUBLIC_API_URL` in the Vercel project settings to your deployed backend URL.

## Project structure

```text
rag-hr-assistant/
├── Dockerfile                 # Hugging Face Spaces image (backend)
├── render.yaml                # Render service definition (backend)
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Pydantic settings
│   │   ├── ingestion.py       # PDF loading and chunking
│   │   ├── vector_store.py    # FAISS index management
│   │   ├── query_router.py    # Query routing and decomposition
│   │   ├── reranker.py        # Cross-encoder re-ranking
│   │   ├── rag_chain.py       # LCEL RAG pipeline
│   │   └── main.py            # FastAPI app and endpoints
│   ├── data/
│   │   ├── pdfs/              # Uploaded PDFs (git-ignored)
│   │   └── faiss_index/       # Persisted FAISS index (git-ignored)
│   ├── main.py                # Uvicorn entry point
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx
    │   │   ├── page.tsx
    │   │   └── globals.css
    │   └── components/
    │       ├── UploadBox.tsx
    │       ├── QuestionBox.tsx
    │       ├── AnswerDisplay.tsx
    │       ├── SourcesPanel.tsx
    │       └── StatusBadge.tsx
    ├── package.json
    ├── tailwind.config.js
    ├── next.config.js
    └── .env.example
```

## Known gaps

- **Evaluation:** RAGAS evaluation (faithfulness, answer relevancy, context precision) is planned but not implemented. There is no `app/evaluation.py` and `ragas` is not in `requirements.txt`.
