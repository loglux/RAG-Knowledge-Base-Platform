# Knowledge Base Platform

![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-FF6B6B?logo=qdrant&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![OpenSearch](https://img.shields.io/badge/OpenSearch-005EB8?logo=opensearch&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-111111?logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-191919?logo=anthropic&logoColor=white)
![Voyage](https://img.shields.io/badge/Voyage-1B1F23?logo=voyage&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-000000?logo=ollama&logoColor=white)
![LangChain](https://img.shields.io/badge/🦜_LangChain-1C3C3C?logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=111111)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

Knowledge Base Platform is a production-ready RAG backend with a clean API and a modern web UI. It ingests documents, builds a semantic index in Qdrant, and answers questions with grounded citations. It also generates document structure (TOC metadata) to enable section-aware retrieval and precise "show me question X" queries, and provides a **retrieve-only** API for automation and MCP-style tools.

It can be used as a standalone service or integrated into other products via its API (plugin-style: you bring the data, it provides retrieval, citations, and answers).

## Why it is useful

- **High-signal retrieval**: Vector search with Qdrant and configurable chunking.
- **Structured navigation**: LLM-based TOC extraction enables section-aware search.
- **API-first**: Use the backend independently from the UI.
- **Provider-flexible**: OpenAI by default, with optional Anthropic, Voyage, or Ollama.
- **Grounded answers**: Responses are built from your documents, not guesses.
- **Retrieve-only access**: Get chunks + context without creating chat history.

## Key features

- **Document ingestion with intelligent chunking** (txt, md, fb2, docx):
  - **Simple**: Fast fixed-size chunking with overlap
  - **Smart**: Recursive chunking respecting sentence/paragraph boundaries (recommended for most cases)
  - **Semantic**: Advanced embedding-based boundary detection using cosine similarity to find natural topic changes
- Embedding-based semantic search over unstructured documents
- Qdrant-backed vector index for fast similarity search
- **MMR (Maximal Marginal Relevance)** for diversity-aware search
- Optional BM25 lexical index (OpenSearch) for hybrid retrieval
- **Self-Check Validation** (optional): Two-stage answer generation with validation for improved accuracy
- **Retrieve-only API** for MCP/search tools (no chat side-effects)
- **Chat history controls**: delete individual Q/A pairs from a conversation
- **BM25 phrase matching**: adds an exact `match_phrase` clause for strict wording
- **Windowed retrieval (context expansion)** for neighboring chunk context
- Structured document analysis and TOC metadata
- RAG answers with citations
- FastAPI backend + React frontend
- Docker-first dev setup
- **KB-level retrieval defaults** stored per knowledge base
- JWT-based admin auth for protected endpoints

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

For structured documents, an optional **Structure‑Aware Retrieval** step builds a TOC and section metadata. This enables section‑targeted queries (e.g., "show Question 2"), returning full, verbatim excerpts rather than a generic summary.

### Retrieve-only (MCP-friendly)

If you need **retrieval without LLM generation** (for tools like MCP `search`/`retrieve`), use:

- `POST /api/v1/retrieve/`

This returns chunks + assembled context **without** creating chat conversations or messages.

You can also set **KB-level retrieval defaults** (e.g., `top_k`, `retrieval_mode`, BM25 settings):

- `GET /api/v1/knowledge-bases/{kb_id}/retrieval-settings`
- `PUT /api/v1/knowledge-bases/{kb_id}/retrieval-settings`
- `DELETE /api/v1/knowledge-bases/{kb_id}/retrieval-settings`

## Chunking strategies

The platform supports three chunking strategies with different trade-offs:

### Simple (Fixed-Size)
- **How it works**: Splits text at fixed character positions with configurable overlap
- **Pros**: Fastest, predictable chunk sizes
- **Cons**: May split mid-sentence or mid-word
- **Use when**: Speed is critical, document structure doesn't matter
- **Overlap**: Required (15-20% recommended)

### Smart (Recursive) - Recommended
- **How it works**: Uses LangChain's RecursiveCharacterTextSplitter to split at natural boundaries (paragraphs → sentences → words)
- **Pros**: Respects document structure, maintains coherent chunks
- **Cons**: Slightly slower than simple
- **Use when**: General-purpose chunking for most documents
- **Overlap**: Required (15-20% recommended)

### Semantic (Embeddings-Based)
- **How it works**:
  1. Splits text into sentences (NLTK)
  2. Generates embeddings for each sentence
  3. Calculates cosine similarity between consecutive sentences
  4. Detects boundaries where similarity drops (topic changes)
  5. Groups semantically related sentences into chunks
- **Pros**: Chunks align with natural topic boundaries, better retrieval quality
- **Cons**: Slowest (requires embedding each sentence), GPU recommended
- **Use when**: Documents have clear topic changes, retrieval quality is critical
- **Overlap**: Not used (boundaries are semantic, not positional)
- **Parameters**:
  - `chunk_size`: Maximum chunk size (acts as soft limit, default 800)
  - `min_chunk_size`: Minimum size before merging (default 100)
  - `boundary_method`: "adaptive" (mean - k*std) or "fixed" (constant threshold)

**Dependencies**:
- Simple: None
- Smart: LangChain
- Semantic: NLTK, NumPy, scikit-learn

## Quick start (Docker)

This starts the full stack (API + DB + Qdrant + OpenSearch + frontend).

1) Create env file

```bash
cp .env.example .env
# add your OPENAI_API_KEY (or other provider keys)
```

2) Read the runbook (dev ops notes, CORS, restart rules)

[RUNBOOK.md](RUNBOOK.md)

3) Start the stack

```bash
docker compose up -d --build
```

4) Open API docs

```text
http://localhost:8004/docs
```

URLs:
- UI: `http://localhost:5174`
- API: `http://localhost:8004/api/v1`

## 📚 Documentation

Comprehensive API documentation is available in multiple formats:

### 📖 GitHub Wiki (Recommended)
Complete documentation with navigation, examples, and visual diagrams:

- **[📚 Documentation Home](https://github.com/loglux/RAG-Knowledge-Base-Platform/wiki)** - Start here
- **[📖 API Documentation](https://github.com/loglux/RAG-Knowledge-Base-Platform/wiki/API-Documentation)** - Complete API reference with request/response examples, data models, and error handling
- **[⚡ Quick Reference](https://github.com/loglux/RAG-Knowledge-Base-Platform/wiki/Quick-Reference)** - Endpoint tables, common patterns, and bash snippets for rapid development
- **[🗺️ API Map](https://github.com/loglux/RAG-Knowledge-Base-Platform/wiki/API-Map)** - Visual API structure, data flow diagrams, and integration examples

### 🔧 Interactive API Docs (When Running)
Explore and test endpoints directly in your browser:

- **[Swagger UI](http://localhost:8004/docs)** - Interactive API documentation with "Try it out" functionality
- **[ReDoc](http://localhost:8004/redoc)** - Clean, responsive API documentation
- **[OpenAPI JSON](http://localhost:8004/api/v1/openapi.json)** - Machine-readable API specification

### 📁 Local Documentation
Documentation source files are available in the [`docs/`](docs/) directory:
- `API_DOCUMENTATION.md` - Full API reference
- `ENDPOINTS_QUICK_REFERENCE.md` - Quick lookup tables
- `API_MAP.md` - Architecture and diagrams

## Minimal API usage

- Create a knowledge base
- Upload a document
- Ask a question
- (Optional) Retrieve-only without creating chats

API details are available in Swagger (`/docs`).

### Retrieve-only example

```bash
curl -X POST http://localhost:8004/api/v1/retrieve/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is this document about?",
    "knowledge_base_id": "your-kb-id",
    "top_k": 5
  }'
```

Pagination note: list endpoints accept `page` and `page_size` (default 10, max 100).

## Windowed Retrieval (Context Expansion)

You can expand retrieval context by including neighboring chunks from the same document.
This helps recover surrounding text that was split during chunking.

API fields:
- `context_expansion: ["window"]`
- `context_window: N` (number of chunks on each side, 0–5)

## Configuration

All configuration lives in `.env`. The sample file is `.env.example`.

Key settings:
- `OPENAI_API_KEY` (or alternate provider keys)
- `QDRANT_URL`
- `OLLAMA_BASE_URL` (optional for local models)
- `MAX_CONTEXT_CHARS` (0 = unlimited)
- `STRUCTURE_ANALYSIS_REQUESTS_PER_MINUTE` (TOC analysis throttle; 0 = unlimited)
- `OPENSEARCH_URL` (optional; required for BM25/hybrid)

### Authentication (JWT)

After the Setup Wizard creates the admin account, all API routes (except `/health`, `/setup`, and `/auth`) require authentication.

- UI login: `http://<host>:5174/login`
- API login: `POST /api/v1/auth/login` (username + password)
- Access token: sent as `Authorization: Bearer <token>`
- Refresh token: stored as an httpOnly cookie; rotate via `POST /api/v1/auth/refresh`
- Logout: `POST /api/v1/auth/logout`

### Reset admin password (Docker)

Use the interactive script to reset an admin password without manual hash copying:

```bash
./scripts/reset_admin_password.sh
```

### CORS (frontend on another host)

If the frontend and API are on different origins (different host or port), CORS is required.

Common cases:
- **Vite frontend on 5174 + API on 8004** → CORS required
- **Nginx proxy** (frontend serves `/api` on same host) → CORS not required

To allow a browser origin, set `CORS_ORIGINS` in `.env` (comma-separated). For example:

```
http://localhost:5174
```

### Database password (Docker secrets)

We now use a Docker‑Compose secret for the database password. This avoids storing the password in `.env` or the database.

1) Create the secret file:
```
./scripts/setup_secrets.sh
```
2) Rebuild and restart:
```
docker compose down
docker compose up -d --build
```

If you don't know the current DB password, reset it first:
```
docker exec -u postgres -it kb-platform-db psql -U postgres -d postgres \
  -c "ALTER USER kb_user WITH PASSWORD 'NEW_PASSWORD';"
```
Then rerun `./scripts/setup_secrets.sh` with the new password.

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
- **Use Document Structure**: enables TOC‑aware, section‑targeted retrieval (e.g., "show question 2").
- **Use MMR (Maximal Marginal Relevance)**: enables diversity-aware search to avoid retrieving too many similar chunks from the same section. Balances relevance and diversity.
- **MMR Diversity** (when MMR enabled): controls the relevance-diversity tradeoff (0.0–1.0). See detailed guidance below.
- **Windowed retrieval**: expands context by adding neighboring chunks (prevents truncated citations; useful for multi-part questions).
- **Retrieval mode**: dense (vectors) or hybrid (BM25 + vectors).
- **BM25 controls** (hybrid only): lexical top‑K and weight blending.

### MMR Diversity Parameter Guide

MMR (Maximal Marginal Relevance) balances relevance and diversity in search results. Higher diversity values sacrifice some relevance to retrieve chunks from more varied sources.

**Diversity parameter (0.0 - 1.0):**

| Value | Documents | Behavior | Use Case |
|-------|-----------|----------|----------|
| **0.0** | ~4 docs | Pure relevance (standard vector search) | Highest precision needed |
| **0.3** | ~5 docs | Slight diversity, high relevance | Legal docs, technical specs |
| **0.5** | ~6 docs | **Balanced (recommended default)** ⭐ | General use, Q&A |
| **0.7** | ~8 docs | High diversity, varied sources | Research, exploration |
| **1.0** | ~8 docs | Maximum diversity (lower relevance) | Broad topic overview |

**Trade-off:**
- **Higher diversity** → More different documents, but average relevance score drops (0.67 → 0.59)
- **Lower diversity** → Higher relevance, but chunks may come from same sections

**When to use:**
- `0.3-0.4` — Precision-critical tasks (legal, medical, technical specifications)
- `0.5-0.6` — Default balanced mode for most queries
- `0.7-0.8` — Exploratory research, brainstorming, broad topic surveys

**Example impact** (Top K = 8):
- Without MMR: 4 chunks from Unit 1, 2 from Unit 14, 1 from Unit 2, 1 from Unit 8
- With MMR (0.6): 3 chunks from Unit 1, 2 from Unit 5, 1 each from Units 4, 8, 12 → more diverse sources

### When NOT to use MMR (important!)

MMR is **not always better**. It can hurt answer quality when sequential information is needed:

**❌ Don't use MMR for:**

| Query Type | Why MMR Hurts | Example |
|------------|---------------|---------|
| **Sequential explanations** | Breaks logical flow by skipping intermediate steps | "Explain the rounding rules" → With MMR: gets intro + conclusion but misses rules 1-3. Without MMR: gets complete sequential explanation |
| **Step-by-step instructions** | Scatters steps across different sections | "How to install the software" → With MMR: step 1, step 5, troubleshooting. Without: steps 1-6 in order |
| **Mathematical proofs** | Misses critical intermediate steps | "Prove theorem X" → With MMR: theorem statement + conclusion, missing proof steps |
| **Technical procedures** | Jumps between prerequisites and advanced steps | "Configure authentication" → With MMR: overview + edge cases, missing basic setup |
| **Definition lookups** | Gets related concepts instead of the definition | "What is an API?" → With MMR: mentions of APIs in different contexts vs. focused definition |

**✅ Use MMR for:**

| Query Type | Why MMR Helps | Example |
|------------|---------------|---------|
| **Comparative questions** | Brings perspectives from different sections | "Compare Python vs JavaScript" → gets examples from multiple contexts |
| **Topic overviews** | Samples diverse aspects of a subject | "What is machine learning?" → gets theory, applications, examples from different chapters |
| **Exploratory research** | Discovers unexpected connections | "Applications of blockchain" → finds use cases across finance, healthcare, supply chain |
| **Multi-faceted questions** | Needs information from multiple independent sources | "Pros and cons of microservices" → gets architectural, operational, cost perspectives |
| **Brainstorming** | Maximum idea diversity from varied sources | "Innovation strategies" → collects diverse approaches from different case studies |

**Real example from production:**

Query: *"Tell me about rounding methods"*

- **With MMR (0.6)**: Retrieved chunks from 5 different sections → mentioned "preliminary rounding" but **missed the 3 main rounding rules** (most important part). Answer was incomplete.
- **Without MMR**: Retrieved chunks from 1 section sequentially → got **all 3 rules + examples + edge cases**. Complete answer.

**Rule of thumb:** If your query expects information from **one logical section** of a document (rules, procedures, definitions), **disable MMR**. If you're exploring a topic across **multiple independent sources**, **enable MMR**.

### How these settings interact

- **Score threshold vs TOC**: TOC/structure queries can return chunks with lower similarity scores. If you see missing sections or "not found" responses, set **Score threshold = 0** (no filtering) before running TOC‑style queries.
- **Top K and Max context**: higher Top K increases recall, but you may need a higher Max context to avoid truncation.
- **Hybrid mode**: BM25 improves exact‑term matches. For paraphrases, keep some weight on dense vectors.
- **MMR vs Top K**: MMR is most effective with larger Top K (20+). With small Top K (5-10), diversity impact is limited.

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
