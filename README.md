---
title: HR Policy RAG Assistant
emoji: 🏢
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# HR Policy RAG Assistant

> **AI Engineering Masters Program — Phase 1: RAG Foundations**

A production-grade, single-source **Retrieval-Augmented Generation (RAG)** assistant for HR policy documents.  
Upload any HR policy PDF and ask natural-language questions. Answers are grounded strictly in the document with cited page numbers.

---

## Scope

**In scope:** Questions about HR policies contained in the uploaded PDF documents (leave entitlement, disciplinary procedures, remote work, compensation, onboarding, etc.).

**Out of scope:** Legal advice, medical advice, questions that require cross-document synthesis across unrelated domains, or real-time regulatory lookup. The assistant will explicitly state when a question falls outside the indexed documents.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         User (Browser)                       │
└─────────────────────────┬────────────────────────────────────┘
                          │  HTTP / JSON
┌─────────────────────────▼────────────────────────────────────┐
│                  Next.js Frontend (Port 3000)                 │
│  UploadBox │ QuestionBox │ AnswerDisplay │ SourcesPanel        │
└─────────────────────────┬────────────────────────────────────┘
                          │  REST API
┌─────────────────────────▼────────────────────────────────────┐
│               FastAPI Backend (Port 8000)                     │
│                                                              │
│   POST /ingest ──► ingestion.py ──► vector_store.py          │
│                    (PyPDF + RecursiveCharacterTextSplitter)   │
│                    (SentenceTransformers + FAISS-CPU)         │
│                                                              │
│   POST /query  ──► query_router.py (classify / decompose)    │
│               ──► vector_store.query_index()  (FAISS k-NN)   │
│               ──► reranker.py  (CrossEncoder ms-marco)       │
│               ──► rag_chain.py (LCEL + GPT-4o-mini)          │
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

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS | UI: upload, question, answer, sources |
| Backend API | FastAPI 0.111 + Uvicorn | REST endpoints |
| PDF Ingestion | PyPDF 4 | Page-level text extraction |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | 700-token chunks, 80-token overlap |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Local, zero-cost, 384-dim vectors |
| Vector Store | FAISS-CPU `IndexFlatIP` (cosine on normalised vecs) | Nearest-neighbour retrieval |
| Re-ranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | CE re-scoring of top-10 → top-4 |
| LLM | Groq `llama3-8b-8192` via LangChain LCEL | Answer generation (free tier) |
| Query Routing | LangChain + Groq LLaMA3 | single_fact / multi_part / summarization |
| Evaluation | RAGAS 0.1 | faithfulness, answer_relevancy, context_precision |

---

## Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Groq API key (free — see [console.groq.com](https://console.groq.com))

### 1. Clone & configure

```bash
git clone <your-repo-url>
cd rag-hr-assistant
```

```bash
cd backend
cp .env.example .env
# Edit .env — set GROQ_API_KEY
```

```bash
cd ../frontend
cp .env.example .env.local
# NEXT_PUBLIC_API_URL defaults to http://localhost:8000
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev                         # http://localhost:3000
```

### 4. Ingest a PDF

Either drag-and-drop in the browser, or via curl:

```bash
curl -X POST http://localhost:8000/ingest \
     -F "file=@/path/to/hr-policy.pdf"
```

### 5. Query

```bash
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"question": "How many annual leave days do I get?"}'
```

### 6. Run RAGAS evaluation

```bash
cd backend
python -m app.evaluation
# Results appended to eval/results.jsonl
```

---

## API Reference

### `GET /health`
Returns `{"status": "ok"}`.

### `GET /status`
Returns index statistics.

**Response:**
```json
{
  "total_chunks": 142,
  "indexed": 142,
  "sources": ["hr-policy-2024.pdf"]
}
```

### `POST /ingest`
Upload a PDF for chunking and indexing.

**Request:** `multipart/form-data` with field `file` (PDF only).

**Response:**
```json
{
  "filename": "hr-policy-2024.pdf",
  "chunks_added": 142,
  "total_indexed": 142
}
```

### `POST /query`
Ask a question against the indexed documents.

**Request:**
```json
{ "question": "What is the notice period for resignation?" }
```

**Response:**
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

---

## Re-Ranking: Before vs After

Cross-encoder re-ranking re-orders chunks retrieved by FAISS (cosine similarity) using a query-document relevance model. Example for *"What is the disciplinary procedure?"*:

| Rank | Pre-Rerank Source | FAISS Score | Post-Rerank Source | CE Score |
|---|---|---|---|---|
| 1 | hr-policy.pdf p.3 | 0.741 | hr-policy.pdf p.8 | 4.21 |
| 2 | hr-policy.pdf p.8 | 0.735 | hr-policy.pdf p.9 | 3.88 |
| 3 | hr-policy.pdf p.1 | 0.721 | hr-policy.pdf p.3 | 2.74 |
| 4 | hr-policy.pdf p.9 | 0.714 | hr-policy.pdf p.1 | 1.05 |

The cross-encoder promotes deeply relevant but embedding-distant chunks (p.8, p.9) above surface-similar but less relevant passages (p.1, p.3).

---

## RAGAS Evaluation Results

Logged to `backend/eval/results.jsonl`. Example result:

```json
{
  "timestamp": "2024-11-01T10:00:00+00:00",
  "n_questions": 10,
  "faithfulness": 0.91,
  "answer_relevancy": 0.87,
  "context_precision": 0.84
}
```

| Metric | Description | Target |
|---|---|---|
| Faithfulness | Answer claims grounded in retrieved context | > 0.80 |
| Answer Relevancy | Answer addresses the question asked | > 0.80 |
| Context Precision | Retrieved chunks are relevant to the question | > 0.75 |

---

## Deployment (Vercel + Render)

### Backend → Render / Railway

```bash
# Render build command
pip install -r requirements.txt

# Start command
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set environment variables in the Render dashboard matching `backend/.env.example`.

### Frontend → Vercel

```bash
npm install -g vercel
cd frontend
vercel --prod
```

Set `NEXT_PUBLIC_API_URL` in the Vercel project settings to point to your deployed backend URL.

---

## Project Structure

```
rag-hr-assistant/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Pydantic settings
│   │   ├── ingestion.py       # PDF loading & chunking  (Step 3)
│   │   ├── vector_store.py    # FAISS index management  (Step 4)
│   │   ├── rag_chain.py       # LCEL RAG pipeline       (Step 5)
│   │   ├── query_router.py    # Routing & decomposition (Step 6)
│   │   ├── reranker.py        # Cross-encoder re-rank   (Step 7)
│   │   ├── evaluation.py      # RAGAS evaluation        (Step 8)
│   │   └── main.py            # FastAPI app & endpoints
│   ├── data/
│   │   ├── pdfs/              # Uploaded PDFs
│   │   └── faiss_index/       # Persisted FAISS index
│   ├── eval/
│   │   └── results.jsonl      # Evaluation log
│   ├── main.py                # Uvicorn entry point
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx
    │   │   ├── page.tsx        # Main page
    │   │   └── globals.css
    │   └── components/
    │       ├── UploadBox.tsx   # PDF upload (Step 9)
    │       ├── QuestionBox.tsx # Question input
    │       ├── AnswerDisplay.tsx
    │       ├── SourcesPanel.tsx # Expandable sources
    │       └── StatusBadge.tsx  # Index status
    ├── package.json
    ├── tailwind.config.js
    ├── next.config.js
    └── .env.example
```

---

## Scope Note

This assistant answers questions **strictly** based on HR policy content found in the indexed PDF documents. It does not provide legal or medical advice, does not access live databases, and will explicitly state when a question falls outside the available content. Multi-document hybrid search and GraphRAG are out of scope for this phase.
