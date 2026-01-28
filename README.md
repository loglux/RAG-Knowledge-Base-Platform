# Knowledge Base Platform

![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-FF6B6B?logo=qdrant&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![OpenSearch](https://img.shields.io/badge/OpenSearch-005EB8?logo=opensearch&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-111111?logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-191919?logo=anthropic&logoColor=white)
![Voyage](https://img.shields.io/badge/Voyage-1B1F23?logo=voyage&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-000000?logo=ollama&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=111111)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

Knowledge Base Platform is a production-ready RAG backend with a clean API and a modern web UI. It ingests documents, builds a semantic index in Qdrant, and answers questions with grounded citations. It also generates document structure (TOC metadata) to enable section-aware retrieval and precise "show me question X" queries.

It can be used as a standalone service or integrated into other products via its API (plugin-style: you bring the data, it provides retrieval, citations, and answers).

## Why it is useful

- **High-signal retrieval**: Vector search with Qdrant and configurable chunking.
- **Structured navigation**: LLM-based TOC extraction enables section-aware search.
- **API-first**: Use the backend independently from the UI.
- **Provider-flexible**: OpenAI by default, with optional Anthropic, Voyage, or Ollama.
- **Grounded answers**: Responses are built from your documents, not guesses.

## Key features

- Document ingestion and chunking (txt, md)
- Embedding-based semantic search over unstructured documents
- Qdrant-backed vector index for fast similarity search
- Optional BM25 lexical index (OpenSearch) for hybrid retrieval
- Structured document analysis and TOC metadata
- RAG answers with citations
- FastAPI backend + React frontend
- Docker-first dev setup

## Architecture overview

- **API**: FastAPI, async SQLAlchemy
- **Vector DB**: Qdrant
- **Lexical Search**: OpenSearch (BM25)
- **Metadata DB**: PostgreSQL
- **Embeddings**: text embeddings for unstructured data
- **RAG**: Custom retrieval (dense or hybrid) + LLM generation pipeline
- **Frontend**: Vite + React

## How it works

1) Documents are uploaded and chunked.
2) Each chunk is embedded into vectors.
3) Vectors are stored in Qdrant.
4) A query is embedded and matched by similarity.
5) The top chunks are assembled into context for the LLM.
6) The LLM returns a grounded answer with sources.
7) Optional: a TOC/structure pass enables section-aware retrieval.

## Why vectorization matters

Vectorization turns unstructured text into numeric vectors that capture meaning, not just keywords. This lets the system retrieve semantically similar chunks even when the wording differs. It is especially useful for study notes, specs, or large documents where exact keyword matches miss relevant sections.

## Retrieval and citations

The system performs **semantic retrieval**: it embeds the user query, finds the closest chunk vectors, and assembles them into a context window for the LLM. You can also enable **hybrid retrieval** (BM25 + vectors), which boosts exact keyword matches while preserving semantic recall. Because the answer is grounded in retrieved chunks, we can return **citations** (source snippets) alongside the response.

For structured documents, an optional **Structure‑Aware Retrieval** step builds a TOC and section metadata. This enables section‑targeted queries (e.g., “show Question 2”), returning full, verbatim excerpts rather than a generic summary.

## Quick start (Docker)

This starts the **backend services only** (API + DB + Qdrant + OpenSearch). The frontend runs locally via Vite.

1) Create env file

```bash
cp .env.example .env
# add your OPENAI_API_KEY (or other provider keys)
```

2) Read the runbook (dev ops notes, CORS, restart rules)

[RUNBOOK.md](RUNBOOK.md)

3) Start backend services

```bash
docker compose -f docker-compose.dev.yml up -d
```

4) Open API docs

```text
http://localhost:8000/docs
```

## Quick start (local dev)

This is for running the API on the host (not Docker).

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

docker compose -f docker-compose.dev.yml up -d db qdrant opensearch
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Minimal API usage

- Create a knowledge base
- Upload a document
- Ask a question

API details are available in Swagger (`/docs`).

## Configuration

All configuration lives in `.env`. The sample file is `.env.example`.

Key settings:
- `OPENAI_API_KEY` (or alternate provider keys)
- `QDRANT_URL` and `DATABASE_URL`
- `OLLAMA_BASE_URL` (optional for local models)
- `MAX_CONTEXT_CHARS` (0 = unlimited)
- `STRUCTURE_ANALYSIS_REQUESTS_PER_MINUTE` (TOC analysis throttle; 0 = unlimited)
- `OPENSEARCH_URL` (optional; required for BM25/hybrid)

## Global settings (UI)

Global Settings define defaults for new chats and retrieval behavior:

- **Default LLM model**
- **Top K / Max context / Score threshold / Temperature**
- **Use Document Structure** default
- **TOC requests per minute** (throttles structure analysis to avoid rate limits)
- **General Knowledge Base Configuration** (chunk size/overlap, batch size, chunking strategy)

These defaults are applied unless a specific knowledge base overrides them.
They are saved in the backend and used to initialize new chats and KBs.

## Chat settings (UI)

The chat UI exposes retrieval controls to tune answer quality:

- **Top K**: number of chunks retrieved from the vector store. Typical range 10–50. Higher values add recall but can bring more noise.
- **Max context chars**: limit for assembled context (0 = unlimited). Lower values reduce cost/latency; higher values preserve more context.
- **Score threshold**: minimum similarity score (0–1) to filter low‑relevance chunks. 0 disables filtering; 0.2–0.4 is a good starting range.
- **Temperature**: response randomness. Use 0–0.3 for factual extraction, higher for exploratory/creative explanations.
- **Use Document Structure**: enables TOC‑aware, section‑targeted retrieval (e.g., “show question 2”).
- **Retrieval mode**: dense (vectors) or hybrid (BM25 + vectors).
- **BM25 controls** (hybrid only): lexical top‑K and weight blending.

### How these settings interact

- **Score threshold vs TOC**: TOC/structure queries can return chunks with lower similarity scores. If you see missing sections or “not found” responses, set **Score threshold = 0** (no filtering) before running TOC‑style queries.
- **Top K and Max context**: higher Top K increases recall, but you may need a higher Max context to avoid truncation.
- **Hybrid mode**: BM25 improves exact‑term matches. For paraphrases, keep some weight on dense vectors.

When you first enable hybrid search on an existing KB, use **Reindex for BM25** to populate the lexical index.

![Chat settings](chat_settings.png)

## KB settings (UI)

Each knowledge base can override the **TOC / Structure model** used for document structure analysis. If override is disabled, the global LLM model is used.
KB‑level configuration (chunk size/overlap, batch size, chunking strategy) is set per KB and affects only new or reprocessed documents.

## Repo layout (minimal)

```
app/           # Backend
frontend/      # UI
docker/        # Docker assets
```

## Status

This project is actively used and evolving. If you want to adapt it to a new domain or provider, the API layer and retrieval engine are designed to be modular.
