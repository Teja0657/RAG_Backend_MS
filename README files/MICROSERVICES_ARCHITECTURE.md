# RAG_Backend_MS — Microservices Architecture (Verified Against Source)

This doc was produced by reading the actual source code (not just the other docs in this
folder), so it reflects what the system **really does today**, including a few places where
it disagrees with `CLAUDE.md` / other `README files/*.md` docs. Those are called out explicitly
in the "Known discrepancies" section at the bottom — read that section too, it matters for
understanding the live system.

There is **no `docker-compose.yml` or `Dockerfile`** anywhere in the repo. Every service is a
separate `uvicorn` process started manually (commands documented in `CLAUDE.md`). MySQL and
Chroma are both plain local installs/files, not containers.

## 1. The services, at a glance

| Service | Port | Framework | Role | Public? |
|---|---|---|---|---|
| `api_gateway` | 8000 | FastAPI | Only service the frontend talks to. Auth0 JWT auth, MySQL for users/chats, proxies everything else. | **Yes** |
| `rag_service` | 8001 | FastAPI | The actual RAG pipeline: retrieval → rerank → generation. Owns Chroma. | No (internal) |
| `document_service` | 8002 | FastAPI | Document lifecycle: upload/replace/delete/list, owns the MySQL `documents` table and the files on disk. | No (internal) |
| `admin_service` | 8003 | FastAPI | Dashboard aggregation (user/query stats) + triggers evaluation runs. | No (internal) |
| `rag_core` | — | plain library | Shared code: chunking, embedding, retrieval, reranking, generation, config. Imported by `rag_service`. Not a running process. | — |
| `evaluation` | — | plain scripts | LangSmith dataset + evaluation runner, invoked in-process by `admin_service`. Not a running process. | — |
| `document_storage` | — | folder | Flat folder on disk holding the raw uploaded files. | — |
| `chroma_db` | — | folder | On-disk persisted Chroma vector store. | — |

```
Browser (Frontend)
      │  HTTPS + Auth0 JWT (Bearer)
      ▼
┌─────────────┐
│ api_gateway │  :8000  (validates JWT, owns MySQL users/conversations/messages)
└──────┬──────┘
       │  X-Internal-Secret header (static shared secret, not the user's JWT)
       ├────────────────► rag_service      :8001  (retrieval + rerank + generation, owns Chroma)
       ├────────────────► document_service :8002  (file CRUD, owns MySQL documents table + disk files)
       └────────────────► admin_service     :8003  (stats/eval, ALSO reads api_gateway's MySQL tables directly in-process)
                                │
                                ├──► rag_service       (for stats / test-chat / evaluation runner queries)
                                └──► document_service  (for stats)

document_service ────► rag_service   (index/delete chunks after every upload/replace/delete)
```

## 2. Identity & auth model (important, and a bit unusual)

- **Only `api_gateway` knows who the end user is.** It validates an Auth0 RS256 JWT (JWKS
  fetched from `https://{AUTH0_DOMAIN}/.well-known/jwks.json`), checking `audience`, `issuer`,
  10s leeway. See `api_gateway/auth.py::get_current_user`.
- On **every** authenticated request, `get_current_user` also calls `upsert_user(payload)`
  (`api_gateway/user_service.py`), which writes/updates a MySQL `users` row — not just at login.
  Role comes from a custom Auth0 claim `https://myapp.example.com/roles` (yes, the local
  constant for this is actually misspelled `ROLES_CALIM` in the code).
- `require_admin` = `get_current_user` + a 403 if `"admin"` isn't in the roles claim.
- **The user's JWT never leaves `api_gateway`.** Every call from `api_gateway` to
  `rag_service`/`document_service`/`admin_service`, and every service-to-service call between
  those three, instead sends a single static shared secret in header `X-Internal-Secret`
  (env var `INTERNAL_SERVICE_SECRET`), checked by a `verify_internal_secret` dependency that is
  copy-pasted byte-for-byte into all three services.
- Net effect: **`rag_service`, `document_service`, and `admin_service` have zero concept of
  "which user" made a request.** Per-user history only exists in `api_gateway`'s MySQL tables.
- `admin_service` breaks the internal-HTTP pattern for reads: `admin_service/routes/admin.py`
  imports `api_gateway.database.SessionLocal` directly and runs raw SQL against `api_gateway`'s
  own `users`/`conversations`/`messages` tables **in-process**, bypassing HTTP and the secret
  entirely, purely because both services happen to run in the same Python environment against
  the same MySQL database.

## 3. api_gateway (port 8000)

Entry point: `api_gateway/main.py`. Creates `users`/`conversations`/`messages` MySQL tables on
import. CORS locked to `http://localhost:5173`.

### Endpoints

| Method | Path | Purpose | Auth |
|---|---|---|---|
| GET | `/internal/health` | liveness | none |
| GET | `/api/server-time` | debug clock | none |
| GET | `/api/me` | echo decoded JWT claims | JWT |
| POST | `/api/chat` | non-streaming chat turn: create/reuse conversation, save both turns, proxy to `rag_service` | JWT |
| POST | `/api/chat/stream` | SSE streaming chat turn, re-emits `rag_service`'s SSE, saves assistant turn once stream ends | JWT |
| GET | `/api/chats` | list current user's conversations | JWT |
| GET | `/api/chats/{conversation_id}` | one conversation + its messages | JWT |
| PATCH | `/api/chats/{conversation_id}/rename` | rename a conversation | JWT |
| PATCH | `/api/chats/{conversation_id}/pin` | pin/unpin (max 3 pinned at once) | JWT |
| DELETE | `/api/chats/{conversation_id}` | delete conversation (messages cascade) | JWT |
| POST | `/api/admin/documents` | upload doc → proxy to `document_service` | JWT + admin |
| GET | `/api/admin/documents` | list docs → proxy to `document_service` | JWT + admin |
| PUT | `/api/admin/documents/{document_id}` | replace doc → proxy to `document_service` | JWT + admin |
| DELETE | `/api/admin/documents/{document_id}` | delete doc → proxy to `document_service` | JWT + admin |
| POST | `/api/admin/documents/reindex-all` | bulk reindex → proxy to `document_service` | JWT + admin |
| GET | `/api/admin/overview` | dashboard overview → proxy to `admin_service` | JWT + admin |
| GET | `/api/admin/users` | per-user query counts → proxy to `admin_service` | JWT + admin |
| GET | `/api/admin/stats` | aggregated stats → proxy to `admin_service` | JWT + admin |
| POST | `/api/admin/evaluation/run` | trigger LangSmith eval run → proxy to `admin_service` | JWT + admin |
| POST | `/api/admin/test-chat` | one-off live RAG probe → proxy to `admin_service` | JWT + admin |

### Outbound calls
All via `httpx.AsyncClient` with `X-Internal-Secret` from `api_gateway/internal_client.py`:
- `routes/chat.py` → `POST {RAG_SERVICE_URL}/internal/query` and `/internal/query/stream`
- `routes/documents.py` → `{DOCUMENT_SERVICE_URL}/internal/documents...` (all CRUD + reindex-all)
- `routes/admin.py` → `{ADMIN_SERVICE_URL}/internal/...` (overview/users/stats/evaluation/test-chat)

### MySQL tables owned here (`api_gateway/models.py`)
- **`users`**: `id`, `auth0_user_id` (unique), `email`, `name`, `role` (default `"user"`), `created_at`, `last_login`
- **`conversations`**: `id`, `user_id`, `title`, `pinned` (bool), `created_at`
- **`messages`**: `id`, `conversation_id` (FK, cascade delete), `role`, `content`, `created_at`

## 4. rag_service (port 8001) — the RAG pipeline itself

Entry point: `rag_service/main.py`. On startup it loads the Gemini embedding model once into
`app.state.embedding_model`. Every route requires the `X-Internal-Secret` header.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/internal/health` | liveness (no secret required) |
| POST | `/internal/query` | full pipeline: `hybrid_search(k=8)` → `rerank_documents(top_k=5)` → `generate_answer`. Returns answer, source chunks, per-stage timings, LangSmith trace URL |
| POST | `/internal/query/stream` | same pipeline, but the generation step streams tokens as SSE (`token`/`done`/`error` events) |
| POST | `/internal/documents/index` | load a file → chunk it → diff-sync chunks into Chroma |
| DELETE | `/internal/documents/{document_id}` | delete all Chroma chunks belonging to that document |
| GET | `/internal/stats` | `{"indexed_chunks": <chroma collection.count()>}` |

This service has no outbound calls to other internal services — it's a leaf. It only calls the
Google/Anthropic LLM APIs and reads/writes the local Chroma store.

### The RAG pipeline in detail (`rag_core/`, shared library)

1. **Ingestion** (`rag_core/ingestion/ingestion.py`) — parses `.pdf` (pdfplumber; tables become
   Markdown; pages are 0-indexed in metadata), `.docx`, `.html`, `.txt`/`.md`, `.csv`
   (→ Markdown table). All text is NFKC-normalized and whitespace-collapsed.
2. **Chunking** (`rag_core/chunking/chunking.py`) — fixed-size chunks (`CHUNK_SIZE=1000`,
   `CHUNK_OVERLAP=150`). Each chunk gets a deterministic `chunk_id = sha256(document_id +
   content_hash)`, plus `document_id`, `document_version`, `chunk_index`, `source`, `file_type`.
3. **Embedding** — Google `gemini-embedding-001` (`GoogleGenerativeAIEmbeddings`). **Note:**
   this is instantiated independently in three different places (`embedding.py`,
   `vector_store.py`, and `semantic_retrieval.py`) instead of being shared — see discrepancy #4
   below.
4. **Storage/sync** (`rag_core/vector_store/vector_store.py::sync_document_chunks`) — diffs new
   chunk IDs against existing ones scoped to that `document_id` (`collection.get(where=
   {"document_id": ...})`), adds new ones in batches of 90 with a 60s sleep between batches
   (Gemini rate-limit protection), then deletes stale ones only after adds succeed.
5. **Retrieval, hybrid** (`rag_core/retrieval/`):
   - Semantic: Chroma `similarity_search_with_relevance_scores`, k=8.
   - Lexical: BM25 (`rank_bm25`), index rebuilt from the **entire collection** on every call, k=8.
   - Fusion: Reciprocal Rank Fusion (`RRF_K=60`), top 8 candidates kept.
6. **Reranking** (`rag_core/reranking/reranking.py`) — **LLM-based**, not a cross-encoder: asks
   the LLM to return a JSON array of ranked indices over the candidates; falls back to
   `documents[:top_k]` if the JSON is malformed; keeps top 5.
7. **Generation** (`rag_core/generation/generation.py`) — strict system prompt that forbids
   answering outside the retrieved context, with a fixed abstention phrase: *"I could not find
   the answer in the provided document, please ask a relevant question."*

Config for all of the above lives in one place: `rag_core/config.py`.

### Storage: Chroma vector store
- Path `./chroma_db` (relative to process CWD), single collection `knowledge_base`.
- Nothing else touches this store except `rag_service` — no other service reads/writes Chroma
  directly.

## 5. document_service (port 8002) — file lifecycle

Entry point: `document_service/main.py`. Creates the MySQL `documents` table on import. Every
route requires `X-Internal-Secret`.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/internal/health` | liveness |
| POST | `/internal/documents` | upload: `document_id = sha256(filename)`; rejects duplicates; saves file to `document_storage/<filename>`; inserts MySQL row (`status=PROCESSING`); calls `rag_service` to index; flips `status` to `READY`/`FAILED` |
| GET | `/internal/documents` | list all documents (id, filename, version, status, timestamps) |
| GET | `/internal/documents/stats` | `{total, ready, processing, failed}` |
| PUT | `/internal/documents/{document_id}` | versioned replace: writes new file to a temp path, re-indexes from the temp path, and **only on success** swaps it over the old file and bumps `version` (rolls back the temp file + marks `FAILED` on any failure) |
| DELETE | `/internal/documents/{document_id}` | deletes Chroma chunks via `rag_service` **first**, then the physical file, then the MySQL row — so a failed RAG delete leaves the file and DB row untouched |
| POST | `/internal/documents/reindex-all` | re-POSTs every existing document (oldest first) to `rag_service`'s index endpoint |

### Outbound calls
All `httpx.AsyncClient` calls to `{RAG_SERVICE_URL}/internal/documents/index` (upload, replace,
reindex-all) and `{RAG_SERVICE_URL}/internal/documents/{document_id}` (delete).

### Storage
- **MySQL `documents`** (`document_service/models.py`): `id` (sha256 of filename, PK),
  `filename`, `file_path`, `version` (int), `status` (`PROCESSING`/`READY`/`FAILED`),
  `created_at`, `updated_at`.
- **Raw files**: flat folder `document_storage/` at the repo root — `STORAGE_DIR =
  Path("document_storage")` is a *relative* path, so it resolves against wherever `uvicorn` was
  launched from, not against the service's own package directory. No subfolders, no versioning
  on disk (replace overwrites in place), no S3/cloud storage anywhere in the codebase.

## 6. admin_service (port 8003) — dashboard + evaluation trigger

Entry point: `admin_service/main.py`. Creates MySQL `evaluation_metrics` table on import. Every
route requires `X-Internal-Secret`.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/internal/health` | liveness |
| GET | `/internal/overview` | registered users, total queries, recent activity (raw SQL on `api_gateway`'s DB, in-process) + `rag_service /internal/stats` |
| GET | `/internal/users` | per-user query counts (raw SQL join on `api_gateway`'s tables, excludes admins) |
| POST | `/internal/evaluation/run` | runs `evaluation.runner.run_evaluation()` synchronously, persists per-metric rows |
| GET | `/internal/stats` | total queries (MySQL) + `rag_service` stats + `document_service` stats + latest cached evaluation summary |
| POST | `/internal/test-chat` | one-shot probe: calls `rag_service /internal/query` directly, returns answer/timings/trace_url |

### Outbound calls
- `GET {RAG_SERVICE_URL}/internal/stats` (overview, stats)
- `GET {DOCUMENT_SERVICE_URL}/internal/documents/stats` (stats)
- `POST {RAG_SERVICE_URL}/internal/query` (test-chat)
- In-process (not HTTP) `evaluation.runner.run_evaluation()`, which itself calls
  `rag_service /internal/query` via plain `requests` for each dataset example.
- In-process raw SQL reads against `api_gateway.database.SessionLocal` (see §2 above).

### Storage
- **MySQL `evaluation_metrics`** (`admin_service/models.py`): `id`, `run_id`, `run_url`,
  `metric_name`, `score`, `total_examples`, `passed_examples`, `failed_examples`,
  `evaluated_at` — one row per metric per evaluation run.
- Also **reads** (never writes) `api_gateway`'s `users`/`conversations`/`messages` tables.

## 7. evaluation/ — not a service, a script library

- `evaluation/seed_dataset.py` — seeds a LangSmith dataset (`Hybrid-RAG-Evaluation`) with 50
  hardcoded Q&A pairs across question types (`numeric`, `cross_reference`, `negation`,
  `reasoning`, `out_of_context`, etc).
- `evaluation/runner.py` — `run_evaluation()` queries `rag_service` for every example, then runs
  LangSmith's `evaluate()` with 5 Claude-judge evaluators (`ChatAnthropic`,
  `claude-sonnet-4-6`): `answer_correctness`, `faithfulness`, `answer_relevance`,
  `retrieval_quality` (skipped for `out_of_context`), `abstention` (only for `out_of_context`).
- Invoked only from `admin_service`'s `/internal/evaluation/run`, in-process — never runs as its
  own HTTP server.

## 8. End-to-end walkthroughs

### A) User asks a question in the chat UI
1. Frontend → `POST /api/chat` (or `/api/chat/stream`) on `api_gateway`, with Auth0 JWT.
2. `api_gateway` validates JWT, upserts the `users` row, creates/reuses a `conversations` row,
   saves the user's message to `messages`.
3. `api_gateway` → `POST {RAG_SERVICE_URL}/internal/query[/stream]` with `X-Internal-Secret`
   (no user identity is sent downstream).
4. `rag_service`: hybrid retrieval (semantic + BM25 via RRF) over Chroma → LLM rerank → LLM
   generation, grounded strictly in the retrieved chunks.
5. `rag_service` returns the answer (+ sources, timings, trace URL) to `api_gateway`.
6. `api_gateway` saves the assistant's message to `messages`, returns/streams it to the frontend.

### B) Admin uploads a document
1. Frontend → `POST /api/admin/documents` on `api_gateway` (JWT + admin role required).
2. `api_gateway` → `POST {DOCUMENT_SERVICE_URL}/internal/documents` with the file.
3. `document_service` computes `document_id = sha256(filename)`, saves the raw file to
   `document_storage/`, inserts a MySQL row with `status=PROCESSING`.
4. `document_service` → `POST {RAG_SERVICE_URL}/internal/documents/index`.
5. `rag_service` ingests → chunks → embeds → diff-syncs chunks into Chroma (`knowledge_base`
   collection, tagged with that `document_id`).
6. On success, `document_service` flips the MySQL row to `READY` (or `FAILED` on error) and
   responds back up the chain to the frontend.

### C) Admin opens the dashboard
1. Frontend → `GET /api/admin/overview` / `/stats` / `/users` on `api_gateway`.
2. `api_gateway` proxies to the matching `admin_service` `/internal/...` endpoint.
3. `admin_service` combines: raw SQL against `api_gateway`'s MySQL tables (in-process, no HTTP),
   plus `GET /internal/stats` calls out to `rag_service` and `document_service`.
4. Result is a single combined JSON payload returned up to the frontend.

## 9. Known discrepancies vs. other docs / comments in this repo

These were found by comparing the live code against `CLAUDE.md` and the other files in this
`README files/` folder — worth knowing so you don't trust a stale description of the system:

1. **Active LLM is Gemini, not Claude.** `rag_core/config.py` currently sets both
   `GENERATION_MODEL` and `RERANK_MODEL` to `"google_genai:gemini-3.5-flash-lite"`, with
   `"anthropic:claude-sonnet-4-6"` commented out on the same lines. Other docs describe Claude
   as the default for generation/reranking — that's not what's currently configured. Only the
   evaluation judge (`ChatAnthropic`) still uses Claude.
2. **The LangGraph pipeline (`rag_core/agent/graph.py`, `nodes.py`, `state.py`) is dead code.**
   `rag_service/routes/query.py` has that implementation fully commented out, labeled as a
   pre-demo rollback. The live `/internal/query` route is a plain step-by-step function, not the
   graph. If you read about "the graph" elsewhere, know it's not what actually runs right now.
3. **Evaluation dataset size comment is stale.** A comment in `api_gateway/routes/admin.py` says
   "35-question" dataset; the actual seeded dataset (`evaluation/seed_dataset.py`) has 50
   examples.
4. **Embedding model/client duplication.** `gemini-embedding-001` and the Chroma client are
   instantiated independently in three places (`embedding.py`, `vector_store.py`,
   `semantic_retrieval.py`) instead of sharing one instance — `rag_service` actually holds two
   separate embedding-model objects and two separate Chroma client objects in memory at once
   (one from the startup `lifespan`, one lazily built inside retrieval).
5. **No docker-compose/Dockerfile exists** — everything runs as manually-started `uvicorn`
   processes per the commands in `CLAUDE.md`.
6. Minor code typos (not doc issues, but easy to trip over while reading): `ROLES_CALIM` in
   `api_gateway/auth.py` (should read `ROLES_CLAIM`), and `converstion_id` as a parameter name in
   `api_gateway/crud.py::get_conversation_messages`.
