# RAG Backend - Visual Diagrams & Flows

## 1. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          EXTERNAL USERS                                    │
│                          (Web Browser)                                     │
│                               │                                           │
│                               ▼                                           │
│                    ┌──────────────────────┐                               │
│                    │   RAG_Frontend       │                               │
│                    │   React + Vite       │                               │
│                    │   Port 5173          │                               │
│                    └─────────┬────────────┘                               │
│                              │                                           │
│                        JWT Bearer Token                                   │
│                    (From Auth0 Cloud)                                    │
│                              │                                           │
│                              ▼                                           │
│                    ┌─────────────────────────────────────┐               │
│                    │  API GATEWAY                        │               │
│                    │  (Main Entry Point)                 │               │
│                    │  Port 8000                          │               │
│                    │  ✓ JWT Validation                   │               │
│                    │  ✓ Role-Based Access               │               │
│                    │  ✓ Request Routing                 │               │
│                    │  ✓ Response Aggregation            │               │
│                    └────────┬──────────┬──────────┬──────┘               │
│                             │          │          │                     │
│           ┌─────────────────┘          │          └──────────────────┐  │
│           │                            │                             │  │
│           ▼                            ▼                             ▼  │
│    ┌─────────────────┐        ┌──────────────────┐      ┌──────────────┐│
│    │  RAG Service    │        │ Document Service │      │ Admin        ││
│    │  Port 8001      │        │ Port 8002        │      │ Service      ││
│    │                 │        │                  │      │ Port 8003    ││
│    │ • Retrieval     │        │ • Upload handler │      │              ││
│    │ • Reranking     │        │ • File parsing   │      │ • Analytics  ││
│    │ • Generation    │        │ • Chunking       │      │ • Evaluation ││
│    │ • LLM Calls     │        │ • Embedding      │      │ • Testing    ││
│    │ • Tracing       │        │ • DB Storage     │      │              ││
│    └────────┬────────┘        └────────┬─────────┘      └──────┬───────┘│
│             │                          │                        │      │
│             │                          │                        │      │
│             ▼                          │                        │      │
│    ┌─────────────────┐                │                        │      │
│    │  rag_core       │                │                        │      │
│    │  Modules        │                │                        ▼      │
│    │                 │                │                ┌──────────────┐│
│    │ • retrieval/    │                │                │  MySQL DB    ││
│    │   - semantic    │                │                │  (API GW)    ││
│    │   - lexical     │                │                │              ││
│    │ • reranking/    │                │                │ • users      ││
│    │ • generation/   │                │                │ • conv.      ││
│    │ • embedding/    │                │                │ • messages   ││
│    │ • chunking/     │                │                │ • eval. data ││
│    │ • ingestion/    │                │                └──────────────┘│
│    │ • vector_store/ │                │                                │
│    └────────┬────────┘                │                                │
│             │                         │                                │
│             ▼                         ▼                                │
│    ┌─────────────────┐      ┌──────────────────────┐                  │
│    │  Chroma Vector  │      │ File Storage + LLM   │                  │
│    │  Database       │      │ • Anthropic API      │                  │
│    │                 │      │ • OpenAI API         │                  │
│    │ • Embeddings    │      │ • Document files     │                  │
│    │ • Vectors       │      │ • Logs/Traces        │                  │
│    │ • Metadata      │      └──────────────────────┘                  │
│    └─────────────────┘                                                │
│                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

External:
   ┌──────────────────┐         ┌──────────────────┐
   │  Auth0 Cloud     │         │  LLM APIs        │
   │  • JWT           │         │  • Claude        │
   │  • Auth          │         │  • GPT-4         │
   └──────────────────┘         └──────────────────┘
```

---

## 2. Complete User Journey Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  STEP 1: AUTHENTICATION (User Login)                                   │
│                                                                         │
│  ┌──────────┐         ┌────────────┐         ┌──────────────┐          │
│  │  Browser │         │   Auth0    │         │ API Gateway  │          │
│  │  Page    │────────▶│   Cloud    │────────▶│    (JWT      │          │
│  │          │ Login   │            │ JWT     │   Validator) │          │
│  │          │ Redirect│            │  Token  │              │          │
│  └──────────┘         └────────────┘         └──────┬───────┘          │
│                                                      │                 │
│                                      ┌───────────────┤                 │
│                                      │               │                 │
│                                 Save to │             │                 │
│                                 MySQL │               │                 │
│                                      │               │                 │
│                                      ▼               ▼                 │
│                                    ┌─────────────────────┐             │
│                                    │   MySQL Database    │             │
│                                    │  (User Created)     │             │
│                                    └─────────────────────┘             │
│                                                                         │
│  STEP 2: USER SENDS MESSAGE                                            │
│                                                                         │
│  ┌──────────────┐                                                      │
│  │  Frontend UI │                                                      │
│  │ "Hi, what's  │                                                      │
│  │  AI?"        │                                                      │
│  └──────┬───────┘                                                      │
│         │ Send with JWT                                                │
│         ▼                                                              │
│  ┌──────────────────────────────────────┐                             │
│  │  API Gateway POST /api/chat          │                             │
│  │  ✓ Validate JWT                      │                             │
│  │  ✓ Create/Fetch Conversation        │                             │
│  │  ✓ Save User Message to MySQL        │                             │
│  │  ✓ Call RAG Service                  │                             │
│  └──────┬───────────────────────────────┘                             │
│         │ Send with Internal Secret                                    │
│         ▼                                                              │
│  ┌──────────────────────────────────────┐                             │
│  │  RAG Service POST /internal/query    │                             │
│  │                                      │                             │
│  │  a) RETRIEVE (Hybrid Search)         │                             │
│  │     ├─ Semantic: Vector similarity   │                             │
│  │     │   (Chroma DB)                  │                             │
│  │     └─ Lexical: Keyword matching     │                             │
│  │         (BM25 Index)                 │                             │
│  │     Result: 8 candidates             │                             │
│  │                                      │                             │
│  │  b) RERANK (Top 5)                   │                             │
│  │     └─ Score with Claude LLM         │                             │
│  │                                      │                             │
│  │  c) GENERATE Answer                  │                             │
│  │     └─ Claude LLM creates response   │                             │
│  │                                      │                             │
│  └──────┬───────────────────────────────┘                             │
│         │ Return { answer, context, timings }                         │
│         ▼                                                              │
│  ┌──────────────────────────────────────┐                             │
│  │  API Gateway                         │                             │
│  │  ✓ Save Assistant Message to MySQL   │                             │
│  │  ✓ Return answer to Frontend         │                             │
│  └──────┬───────────────────────────────┘                             │
│         │                                                             │
│         ▼                                                             │
│  ┌──────────────────────────────────────┐                             │
│  │  Frontend UI                         │                             │
│  │  "AI is Artificial Intelligence..." │                             │
│  │  (Displays answer to user)           │                             │
│  └──────────────────────────────────────┘                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. JWT Authentication Flow

```
                    ┌─────────────────────────┐
                    │   Browser/Frontend      │
                    │   User: alice@work.com  │
                    └────────────┬────────────┘
                                 │
                    Click "Login" Button
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    Auth0.com Cloud      │
                    │   (Third-party SaaS)    │
                    │                         │
                    │  1. Display login form  │
                    │  2. User enters creds   │
                    │  3. Verify credentials  │
                    │  4. Check 2FA (if any)  │
                    └────────────┬────────────┘
                                 │
                    Credentials Valid ✓
                    Issue JWT Token
                                 │
                                 ▼
JWT Token Structure:
┌─────────────────────────────────────────────────────────────┐
│ Header:                                                     │
│ {                                                           │
│   "alg": "RS256",  ← RSA Signature Algorithm              │
│   "typ": "JWT",                                             │
│   "kid": "..."     ← Key ID (for multiple keys)            │
│ }                                                           │
│                                                             │
│ Payload:                                                    │
│ {                                                           │
│   "sub": "auth0|user123abc",  ← Unique User ID            │
│   "aud": "https://your-api-audience",  ← Audience        │
│   "iss": "https://your-domain.auth0.com/",  ← Issuer    │
│   "exp": 1696000000,  ← Expiration time                    │
│   "iat": 1695913600,  ← Issued at time                     │
│   "https://myapp.example.com/email": "alice@work.com",   │
│   "https://myapp.example.com/name": "Alice Smith",        │
│   "https://myapp.example.com/roles": ["user"],  ← Roles  │
│   ...other claims...                                       │
│ }                                                           │
│                                                             │
│ Signature:                                                  │
│ RSASHA256(                                                  │
│   base64UrlEncode(header) + "." +                          │
│   base64UrlEncode(payload),                                │
│   AUTH0_PRIVATE_KEY  ← Only Auth0 has this                │
│ )                                                           │
└─────────────────────────────────────────────────────────────┘
                                 │
                                 │ Redirect to:
                                 │ http://localhost:5173?code=...
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Frontend (React App)   │
                    │  Receives JWT from      │
                    │  Auth0 SDK              │
                    │                         │
                    │  getAccessTokenSilently()
                    │  Returns: JWT Token     │
                    └────────────┬────────────┘
                                 │
                    Store JWT (typically in
                    browser memory, not localStorage
                    for security)
                                 │
                                 ▼
Frontend API Request:

  fetch('http://localhost:8000/api/me', {
    headers: {
      'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIs...'
    }
  })
                                 │
                                 ▼
        ┌─────────────────────────────────────────┐
        │  API Gateway (Port 8000)                │
        │                                         │
        │  get_current_user() dependency:         │
        │  1. Extract token from Authorization    │
        │  2. Validate signature using            │
        │     Auth0's public key                  │
        │     (JWKS endpoint)                     │
        │  3. Check expiration                    │
        │  4. Verify audience                     │
        │  5. Verify issuer                       │
        │  6. Return decoded payload              │
        │                                         │
        │  If all checks pass:                    │
        │  ✓ Call upsert_user()                  │
        │  ✓ Save to MySQL                        │
        │  ✓ Return user info                     │
        │                                         │
        │  If checks fail:                        │
        │  ✗ Raise 401 Unauthorized               │
        └─────────────────────────────────────────┘
                                 │
                      ✓ 200 OK or ✗ 401
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Frontend               │
                    │  Set user state         │
                    │  Navigate to /chat      │
                    │  or /admin              │
                    └─────────────────────────┘


KEY POINTS:
───────────
✓ JWT is generated by Auth0, NOT your backend
✓ JWT signature uses RS256 (RSA Asymmetric)
✓ Auth0 has private key (signing)
✓ Your backend has public key (verification)
✓ JWT contains roles in custom claim
✓ JWT expires (typically 24 hours)
✓ Every API call needs JWT in Authorization header
```

---

## 4. RAG Pipeline Detail Flow

```
INPUT QUESTION: "What is machine learning?"
                          │
                          ▼
        ┌──────────────────────────────────┐
        │  STEP 1: RETRIEVAL (Hybrid)      │
        │  Goal: Find relevant documents   │
        └──────────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                 │
         ▼                                 ▼
    ┌─────────────┐               ┌──────────────┐
    │  SEMANTIC   │               │  LEXICAL     │
    │  SEARCH     │               │  SEARCH      │
    │  (Vector)   │               │  (BM25)      │
    └──────┬──────┘               └────────┬─────┘
           │                               │
    "What is machine       "machine" "learning"
    learning?" →           "keyword matching"
    Embedding Vector       "term frequency"
    (1536-dim)             "inverse doc freq"
           │                               │
           ├─ Query Chroma DB    ├─ Query BM25 Index
           │  (Vector DB)         │  (In-memory)
           │                      │
           └─ Find top 8          └─ Find top 8
             semantically           keyword matches
             similar docs           from documents
           │                               │
           ▼                               ▼
    ┌─────────────────┐          ┌──────────────────┐
    │ Semantic Results│          │ Lexical Results  │
    │                 │          │                  │
    │ 1. Doc A        │          │ 1. Doc C         │
    │    similarity:0.92         │    score: 8.5    │
    │ 2. Doc B        │          │ 2. Doc A         │
    │    similarity:0.87         │    score: 7.2    │
    │ 3. Doc C        │          │ 3. Doc D         │
    │    similarity:0.85         │    score: 6.1    │
    │ ... (8 total)   │          │ ... (8 total)    │
    └────────┬────────┘          └────────┬─────────┘
             │                             │
             └─────────────┬───────────────┘
                           │
                ┌──────────────────────────┐
                │  MERGE using RRF         │
                │ (Reciprocal Rank Fusion) │
                │                          │
                │ RRF Score =              │
                │ 1/(semantic_rank+60) +   │
                │ 1/(lexical_rank+60)      │
                │                          │
                │ Result: Top 8 combined   │
                │ deduplicated documents   │
                └──────────────┬───────────┘
                               │
                               ▼
                    ┌────────────────────┐
                    │ 8 Candidates       │
                    │ (Most relevant)    │
                    └─────────┬──────────┘
                              │
                              ▼
        ┌───────────────────────────────────┐
        │  STEP 2: RERANKING                │
        │  Goal: Keep only top 5            │
        │  Method: LLM-based scoring        │
        └───────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
    For each of 8 candidates:          Use Claude LLM
       Score relevance to question      to assign
       based on semantic match          relevance score
                                        (0.0 to 1.0)
                                        │
        ┌───────────────────────────────┴───────────────────────────────┐
        │                                                               │
        ▼                                                               ▼
    Results with scores:                                   Sort by score:
    ┌─────────────────────────────┐     ┌──────────────────────────────┐
    │ Doc A: score 0.95           │     │ 1. Doc A (0.95) ✓            │
    │ Doc B: score 0.82           │     │ 2. Doc F (0.88) ✓            │
    │ Doc C: score 0.78           │────▶│ 3. Doc B (0.82) ✓            │
    │ Doc F: score 0.88           │     │ 4. Doc C (0.78) ✓            │
    │ Doc D: score 0.65           │     │ 5. Doc E (0.72) ✓            │
    │ Doc E: score 0.72           │     │ 6. Doc D (0.65) ✗ (dropped) │
    │ Doc G: score 0.58           │     │ 7. Doc G (0.58) ✗ (dropped) │
    │ Doc H: score 0.52           │     │ 8. Doc H (0.52) ✗ (dropped) │
    └─────────────────────────────┘     └──────────────────────────────┘
                                               │
                                               │ Keep top k=5
                                               ▼
                                        ┌──────────────┐
                                        │ 5 Documents │
                                        │ (Best ones)  │
                                        └──────┬───────┘
                                               │
                                               ▼
        ┌──────────────────────────────────────────────┐
        │  STEP 3: GENERATION                          │
        │  Goal: Generate answer using LLM             │
        │  Method: Prompt + Context + Claude API       │
        └──────────────────────────────────────────────┘
                                               │
        ┌──────────────────────────────────────┴──────────────────────────────┐
        │                                                                     │
        ▼                                                                     ▼
    Build Prompt:                                          Call Claude LLM:
    ┌────────────────────────────────────┐    ┌─────────────────────────────┐
    │ Based on the following documents,  │    │ POST https://api.anthropic  │
    │ answer the question:               │    │ model: claude-3-sonnet      │
    │                                    │    │ max_tokens: 1024            │
    │ Document 1:                        │────▶ prompt: [see left]          │
    │ [Doc A content]                    │    │                             │
    │                                    │    │ Response:                   │
    │ Document 2:                        │    │ "Machine learning is a      │
    │ [Doc F content]                    │    │  subset of artificial       │
    │                                    │    │  intelligence that enables  │
    │ Document 3:                        │    │  systems to learn from      │
    │ [Doc B content]                    │    │  data..."                   │
    │                                    │    └──────────┬──────────────────┘
    │ Document 4:                        │               │
    │ [Doc C content]                    │               ▼
    │                                    │    ┌──────────────────┐
    │ Document 5:                        │    │ Generated Answer │
    │ [Doc E content]                    │    │ (Ready to return)│
    │                                    │    └──────────────────┘
    │ Question: What is machine          │
    │ learning?                          │
    │                                    │
    │ Answer:                            │
    └────────────────────────────────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │  RETURN TO GATEWAY   │
                                    │  {                   │
                                    │    "answer": "...",  │
                                    │    "context": [...], │
                                    │    "timings": {...}  │
                                    │  }                   │
                                    └──────────┬───────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │  DISPLAY TO USER     │
                                    │  "Machine learning   │
                                    │   is a subset of..." │
                                    └──────────────────────┘
```

---

## 5. Database Schema Diagram

```
API GATEWAY DATABASE (MySQL)

┌────────────────────────────────────────┐
│            USERS Table                 │
├────────────────────────────────────────┤
│ PK │ id                    INT          │
│ UQ │ auth0_user_id         VARCHAR(255) │
│    │ email                 VARCHAR(255) │
│    │ name                  VARCHAR(255) │
│    │ role                  ENUM          │
│    │                       ('admin',    │
│    │                        'user')     │
│    │ created_at            TIMESTAMP    │
│    │ last_login            TIMESTAMP    │
│    │                                    │
│    │ Example:                           │
│    │ ─────────────────────────────────  │
│    │ id=1                               │
│    │ auth0_user_id='auth0|user123'    │
│    │ email='alice@work.com'             │
│    │ name='Alice Smith'                 │
│    │ role='admin'                       │
│    │ created_at=2024-01-01 10:00:00    │
│    │ last_login=2024-01-15 14:30:00    │
└────────────────────────────────────────┘
         │
         │ 1:Many
         │
         ▼
┌────────────────────────────────────────┐
│        CONVERSATIONS Table             │
├────────────────────────────────────────┤
│ PK │ id                    INT          │
│ FK │ user_id               INT          │ ──────┐ References USERS
│    │ title                 VARCHAR(255) │       │
│    │ created_at            TIMESTAMP    │       │
│    │ updated_at            TIMESTAMP    │       │
│    │ pinned                BOOLEAN      │       │
│    │                                    │       │
│    │ Example:                           │       │
│    │ ─────────────────────────────────  │       │
│    │ id=42                              │       │
│    │ user_id=1                          │ ─────▶ References user alice
│    │ title='What is AI?'                │
│    │ created_at=2024-01-15 10:00:00    │
│    │ pinned=TRUE                        │
└────────────────────────────────────────┘
         │
         │ 1:Many
         │
         ▼
┌────────────────────────────────────────┐
│          MESSAGES Table                │
├────────────────────────────────────────┤
│ PK │ id                    INT          │
│ FK │ conversation_id       INT          │ ──────┐ References CONVERSATIONS
│    │ role                  ENUM          │       │
│    │                       ('user',     │       │
│    │                        'assistant')│       │
│    │ content               LONGTEXT     │       │
│    │ created_at            TIMESTAMP    │       │
│    │                                    │       │
│    │ Example:                           │       │
│    │ ─────────────────────────────────  │       │
│    │ id=101                             │       │
│    │ conversation_id=42                 │ ─────▶ References conversation
│    │ role='user'                        │
│    │ content='What is ML?'              │
│    │ created_at=2024-01-15 10:01:00    │
│    │                                    │
│    │ id=102                             │
│    │ conversation_id=42                 │
│    │ role='assistant'                   │
│    │ content='ML is a subset of AI...'  │
│    │ created_at=2024-01-15 10:02:00    │
└────────────────────────────────────────┘


VECTOR DATABASE (Chroma)

┌────────────────────────────────────────────┐
│         CHROMA COLLECTIONS               │
├────────────────────────────────────────────┤
│ document_id     │ "doc_123"              │
│ chunk_id        │ "chunk_456"            │
│ embedding       │ [0.12, 0.45, ..., 0.78] │ 1536 dimensions
│ page_content    │ "Machine learning is   │
│                 │  a type of AI..."      │
│ metadata        │ {                      │
│                 │   "filename":          │
│                 │   "ai_intro.pdf",      │
│                 │   "page_num": 1,       │
│                 │   "chunk_index": 0     │
│                 │ }                      │
│ created_at      │ 2024-01-01 09:00:00   │
│                 │                        │
│ [... more      │
│  documents]    │
└────────────────────────────────────────────┘
```

---

## 6. Authentication & Authorization Matrix

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    API ENDPOINT SECURITY MATRIX                         │
├──────────────────────────┬─────────────────┬──────────────┬─────────────┤
│ ENDPOINT                 │ JWT Required    │ Role Check   │ Access Level│
├──────────────────────────┼─────────────────┼──────────────┼─────────────┤
│ GET /api/me              │ ✓ Yes           │ None         │ Logged-in   │
│                          │                 │              │ users       │
├──────────────────────────┼─────────────────┼──────────────┼─────────────┤
│ POST /api/chat           │ ✓ Yes           │ None         │ Logged-in   │
│ POST /api/chat/stream    │ ✓ Yes           │ None         │ users       │
│ GET /api/chats           │ ✓ Yes           │ None         │             │
│ GET /api/chats/{id}      │ ✓ Yes           │ None         │ Same user   │
│ PATCH /api/chats/{id}    │ ✓ Yes           │ None         │ only        │
│ DELETE /api/chats/{id}   │ ✓ Yes           │ None         │             │
├──────────────────────────┼─────────────────┼──────────────┼─────────────┤
│ GET /api/admin/overview  │ ✓ Yes           │ ✓ admin      │ Admin only  │
│ GET /api/admin/users     │ ✓ Yes           │ ✓ admin      │             │
│ GET /api/admin/stats     │ ✓ Yes           │ ✓ admin      │ Admin only  │
│ POST /api/admin/eval/run │ ✓ Yes           │ ✓ admin      │             │
│ POST /api/admin/documents│ ✓ Yes           │ ✓ admin      │ Admin only  │
│ GET /api/admin/documents │ ✓ Yes           │ ✓ admin      │             │
│ PUT /api/admin/documents │ ✓ Yes           │ ✓ admin      │ Admin only  │
├──────────────────────────┼─────────────────┼──────────────┼─────────────┤
│ GET /internal/health     │ ✗ No (internal) │ None         │ Services    │
│ POST /internal/query     │ ✗ No (internal) │ None         │ only        │
│ /internal/*              │ Secret header   │ None         │             │
│                          │ X-Internal-     │              │             │
│                          │ Secret          │              │             │
└──────────────────────────┴─────────────────┴──────────────┴─────────────┘

AUTHENTICATION METHODS:

1. JWT (External/Frontend)
   ├─ Header: Authorization: Bearer {JWT_TOKEN}
   ├─ Validated by: get_current_user()
   ├─ Validated against: Auth0 public key
   ├─ Algorithm: RS256 (RSA Asymmetric)
   └─ Extracted info: user_id, email, roles

2. Internal Service Secret (Service-to-Service)
   ├─ Header: X-Internal-Secret: {SECRET}
   ├─ Validated by: verify_internal_secret()
   ├─ Shared via: Environment variable
   └─ Used for: API Gateway ↔ RAG/Admin/Document Services

ROLE HIERARCHY:

   ┌──────────────┐
   │   "admin"    │  ← Can access /api/admin/*
   │   (Full)     │  ← Can access all user endpoints
   └──────┬───────┘
          │
          │ vs.
          │
          ▼
   ┌──────────────┐
   │   "user"     │  ← Can only access /api/chat
   │  (Limited)   │     and /api/chats
   └──────────────┘
```

---

## 7. Error Handling Flow

```
                    Frontend Makes Request
                            │
                            ▼
                    ┌─────────────────┐
                    │ GET /api/chat   │
                    │ + JWT token     │
                    └────────┬────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         ▼
   JWT Valid?                              JWT Missing/Invalid?
        │                                         │
        ▼                                         ▼
    YES: Continue                             ❌ 401 UNAUTHORIZED
        │                                    "Invalid or expired token"
        ▼                                         │
   Is Admin Endpoint?                            ▼
   (/api/admin/*)                         Return Error Response
        │                                         │
   ┌────┴────┐                                   ▼
   │          │                           ┌──────────────────┐
   ▼          ▼                           │  Frontend Error  │
  YES        NO                           │  Handler         │
   │          │                           │  Redirect to     │
   ▼          ▼                           │  login or show   │
Is admin? Process                         │  error message   │
 │       Normally                         └──────────────────┘
 │          │
 ▼          └────┬──────────────────┐
NO              │                   │
 │              ▼                   ▼
 │          DB Error         Internal Error
 │            │                  │
 ▼            ▼                  ▼
❌            ❌                 ❌
403        500/502             500/503
FORBIDDEN  Internal Error      Service Unavailable
"Admin     "Failed to query    "RAG service
access     database"           unreachable"
required"
 │            │                  │
 └────┬───────┴────────┬─────────┘
      │                │
      ▼                ▼
   Frontend receives error response
   Displays error to user
   Suggests action (retry, login, etc.)
```

---

## 8. Request/Response Cycle

```
┌───────────────────────────────────────────────────────────────────────┐
│                      USER CHAT REQUEST CYCLE                          │
└───────────────────────────────────────────────────────────────────────┘

TIME FLOW (Left to Right, Top to Bottom):

T=0ms   ┌─ User types: "What is AI?"
        │  Clicks Send Button
        │
        └──────────────────┐
T=10ms              Frontend │ Creates Request
                    {       │
                      method: "POST",
                      url: "/api/chat",
                      headers: {
                        Authorization: "Bearer eyJh..."
                      },
                      body: {
                        question: "What is AI?",
                        conversation_id: null
                      }
                    }
                            │
                            ▼
T=50ms              ┌─────────────────────┐
                    │  API Gateway Port 8000
                    │  (Receiving Request) │
                    └────────┬────────────┘
                             │
                    Step 1: Validate JWT
                    - Extract token
                    - Verify signature
                    - Check expiration
                    ✓ Valid
                             │
T=100ms                      ▼
                    Step 2: Extract user_id from JWT
                    user_id = "auth0|alice123"
                             │
T=150ms                      ▼
                    Step 3: Create Conversation
                    SQL: INSERT INTO conversations...
                    conversation_id = 42
                             │
T=200ms                      ▼
                    Step 4: Save User Message
                    SQL: INSERT INTO messages...
                    role = "user"
                    content = "What is AI?"
                             │
T=250ms                      ▼
                    Step 5: Call RAG Service
                    POST http://127.0.0.1:8001/internal/query
                    Headers: X-Internal-Secret: secret123
                    Body: { question: "What is AI?" }
                             │
T=300ms              ┌───────────────────────────┐
                    │  RAG Service Port 8001      │
T=350ms             │  Step 1: Hybrid Retrieval │
                    │  - Semantic search        │
                    │  - Lexical search         │
                    │  Time: ~200ms             │
                    │  Result: 8 candidates     │
                    │                           │
T=550ms             │  Step 2: Reranking        │
                    │  - Score with Claude      │
                    │  Time: ~500ms             │
                    │  Result: 5 best docs      │
                    │                           │
T=1050ms            │  Step 3: Generation       │
                    │  - Create prompt          │
                    │  - Call Claude API        │
                    │  Time: ~1000ms            │
                    │  Result: Answer           │
                    │                           │
T=2050ms            │  Response:                │
                    │  {                        │
                    │    "answer": "AI is...",  │
                    │    "context": [...],      │
                    │    "timings": {...}       │
                    │  }                        │
                    │                           │
                    └────────┬──────────────────┘
                             │
T=2100ms            ┌────────────────────────┐
                    │  API Gateway (Response)│
                    │  Step 6: Save Answer   │
                    │  SQL: INSERT INTO      │
                    │  messages...           │
                    │  role = "assistant"    │
                    │                        │
T=2150ms            │  Response to Frontend: │
                    │  {                     │
                    │    "answer": "AI is...",│
                    │    "conversation_id": 42
                    │  }                     │
                    └────────┬───────────────┘
                             │
T=2200ms            ┌─────────────────────────┐
                    │  Frontend (Display)     │
                    │  Update messages array  │
                    │  Show answer to user    │
                    │                         │
                    │  "AI is Artificial      │
                    │   Intelligence..."      │
                    └─────────────────────────┘


TOTAL TIME: ~2200ms (2.2 seconds)
├─ API Gateway processing: 150ms
├─ Retrieval: 200ms
├─ Reranking: 500ms
├─ Generation: 1000ms
└─ Response + Display: 350ms
```

---

## Summary

These diagrams show:
1. **System Architecture** - Physical layout of services
2. **User Journey** - Complete flow from login to answer
3. **JWT Authentication** - Security flow with Auth0
4. **RAG Pipeline** - Retrieval, Reranking, Generation details
5. **Database Schema** - Table structure and relationships
6. **Security Matrix** - Endpoints and access control
7. **Error Handling** - What happens when things go wrong
8. **Request/Response** - Timing and flow of a complete cycle

Use these diagrams as reference when understanding or explaining the system!

