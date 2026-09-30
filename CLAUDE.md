# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Setup (Windows/PowerShell):
```
python -m venv .venv
.venv\Scripts\activate.ps1
python -m pip install -r requirements.txt
```

Running the system — each service is a separate `uvicorn` process and all four must be running for the app to work end-to-end:
```
uvicorn api_gateway.main:app --reload --reload-dir api_gateway --reload-dir rag_core --port 8000
uvicorn rag_service.main:app --reload --reload-dir rag_service --reload-dir rag_core --port 8001
uvicorn document_service.main:app --reload --reload-dir document_service --port 8002
uvicorn admin_service.main:app --reload --reload-dir admin_service --reload-dir evaluation --port 8003
```
Port map: `api_gateway`=8000 (public), `rag_service`=8001, `document_service`=8002, `admin_service`=8003.

Running the RAG evaluation suite (seeds/uses the LangSmith dataset `Hybrid-RAG-Evaluation`, requires `rag_service` running on :8001 and `LANGSMITH_API_KEY`/`ANTHROPIC_API_KEY` set):
```
python -m evaluation.seed_dataset   # one-time: create the 50-example eval dataset in LangSmith
python -m evaluation.runner         # run the eval, judged by 5 Claude-based evaluators
```
The same evaluation is also triggerable at runtime via `admin_service`'s `/internal/evaluation/run` (exposed through the Admin dashboard's Statistics tab in the frontend).

There is no configured test suite, linter, or formatter in this repo — do not invent `pytest`/`ruff`/`black` invocations.

## Architecture

This is 4 independent FastAPI microservices plus a shared library (`rag_core`), all reading from **one shared MySQL database** and **one shared Chroma vector store** (`./chroma_db`, collection `knowledge_base`) on local disk.

```
Frontend (Vite/React :5173)
   │ Bearer JWT (Auth0, RS256)
   ▼
api_gateway :8000   — only externally-facing service; validates Auth0 JWT, owns User/Conversation/Message tables
   │ X-Internal-Secret header on every call below
   ├──► rag_service :8001        (hybrid retrieval → LLM rerank → LLM generation)
   ├──► document_service :8002  (file storage + Document registry)
   │        └──► rag_service :8001  (index/delete chunks on upload/update/delete)
   └──► admin_service :8003     (dashboard aggregation + evaluation trigger)
            ├──► rag_service :8001       (/internal/stats, /internal/query)
            ├──► document_service :8002  (/internal/documents/stats)
            ├──► api_gateway's MySQL DB directly (in-process import of api_gateway.database.SessionLocal)
            └──► evaluation/runner.py → LangSmith evaluate() → rag_service /internal/query, judged by Claude
```

**Inter-service auth**: every downstream service protects its `/internal/*` routes with `verify_internal_secret` (duplicated in each service's `internal_auth.py`), which checks header `X-Internal-Secret` against env var `INTERNAL_SERVICE_SECRET`. This is a separate, simpler auth layer from the user-facing Auth0 JWT auth used only by `api_gateway`.

**`admin_service` is not fully isolated**: it imports `api_gateway.database.SessionLocal` directly and queries `api_gateway`'s tables in-process rather than calling `api_gateway` over HTTP. Keep this in mind when tracing data flow for admin overview/user stats — it bypasses the internal-secret HTTP boundary that every other cross-service call uses.

### Service responsibilities

- **`api_gateway`** — public API. `auth.py` validates Auth0 JWTs via JWKS and upserts a `User` row per request (`user_service.py`); role (`user`/`admin`) comes from the Auth0 custom claim `https://myapp.example.com/roles`, not a server-side source of truth. Owns `Conversation`/`Message` tables (`models.py`, `crud.py` — pins capped at 3 per user). `routes/chat.py` streams answers by proxying `rag_service`'s SSE endpoint and persists both turns to MySQL. `routes/documents.py` and `routes/admin.py` are thin admin-only (`require_admin`) proxies to `document_service` and `admin_service`.
- **`rag_service`** — the RAG pipeline itself. Loads the Gemini embedding model once at startup into `app.state`. `routes/query.py` orchestrates `hybrid_search (k=8) → rerank_documents (top_k=5) → generate_answer`, both non-streaming and SSE variants; every stage is `@traceable` for LangSmith. `routes/documents.py` handles chunk-level index/delete and reports indexed chunk counts.
- **`document_service`** — file lifecycle. Saves uploads to `document_storage/`, dedupes by sha256 of filename, tracks `status` (PROCESSING/READY/FAILED) in its own `Document` table, and calls `rag_service` to index/delete chunks. Update is a versioned replace-then-reindex with rollback on failure. `reindex-all` is the bootstrap/recovery path.
- **`admin_service`** — read-side aggregation for the admin dashboard and the evaluation trigger; has its own `EvaluationMetric` table for persisting LangSmith run summaries.

### `rag_core/` — the RAG techniques (shared by `rag_service` and reload-tracked by `api_gateway`)

- **Ingestion** (`ingestion/`): format-specific loaders for PDF (pdfplumber, tables→Markdown), DOCX (python-docx), HTML (BeautifulSoup), TXT/MD, CSV (→Markdown table); all text NFKC-normalized and whitespace-collapsed.
- **Chunking** (`chunking/`): `RecursiveCharacterTextSplitter`, size 1000 / overlap 150. Chunk IDs are `sha256(document_id + sha256(content))` — deterministic, so re-indexing unchanged content is a no-op.
- **Embedding** (`embedding/`): Google `gemini-embedding-001` (hardcoded in three places: `embedding.py`, `vector_store.py`, `semantic_retrieval.py` — keep them in sync if this ever changes).
- **Vector store** (`vector_store/`): Chroma, persisted at `./chroma_db`. `sync_document_chunks` diffs new-vs-stale chunk IDs per document, adds new chunks first in batches of 90 with a 60s delay between batches (Gemini rate-limit protection), then deletes stale ones only after adds succeed.
- **Retrieval** (`retrieval/`): hybrid — Chroma semantic search (`semantic_retrieval.py`, k=8) + BM25 built fresh from the whole collection each call (`lexical_retrieval.py`, k=8) — fused via Reciprocal Rank Fusion (`hybrid_retrieval.py`, RRF_K=60). All stages `@traceable`.
- **Reranking** (`reranking/`): LLM-based (not a cross-encoder) — asks the LLM (`get_llm("claude")` by default) to return a JSON-ranked index array over the candidates; falls back gracefully on malformed JSON and appends any indices the model omitted.
- **Generation** (`generation/`): `get_llm(model)` returns either Claude (`claude-sonnet-4-6`, temp 0) or Gemini (`gemini-3.1-flash-lite-preview`). System prompt strictly forbids answering outside retrieved context and mandates a fixed abstention phrase; both sync and streaming (`generate_answer_stream`) variants are `@traceable`.

### Evaluation (`evaluation/`)

`seed_dataset.py` seeds a LangSmith dataset (`Hybrid-RAG-Evaluation`) with 50 adversarial Q&A pairs sourced from the docs in `document_storage/`, deliberately covering numeric near-misses, similar-sounding definitions, conditional logic, negative facts, and out-of-context questions meant to trigger abstention. `runner.py` runs every example through `rag_service`'s `/internal/query` and scores results with 5 Claude-judge evaluators: `answer_correctness`, `faithfulness`, `answer_relevance`, `retrieval_quality` (skipped for out-of-context questions), `abstention` (only for out-of-context questions).

### Known inconsistencies to be aware of

- `PINECONE_API_KEY` and `GROQ_API_KEY` exist in `.env` but are unused anywhere in the code — the real vector store is Chroma and the real LLMs are Claude/Gemini. Don't assume Pinecone or Groq are wired up.
- All 4 services and `evaluation` share a single MySQL database; each service creates its own tables via `Base.metadata.create_all` in its own `database.py`/`models.py` rather than there being one shared schema module.
