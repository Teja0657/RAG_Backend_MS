# RAG Backend - Detailed Code Trace

## 1. LOGIN FLOW - Code Level Trace

### Step 1: Frontend Initiates Login

**File:** `RAG_Frontend/src/pages/Login/LoginPage.jsx` (Line 46)

```javascript
const handleLogin = () => {
  loginWithRedirect({ 
    appState: { returnTo: role === 'admin' ? '/admin' : '/chat' } 
  });
};
```

**What it does:**
- `loginWithRedirect()` is from Auth0 React SDK
- Redirects user to Auth0 hosted login page
- User enters credentials on Auth0 domain

**Function Stack:**
```
handleLogin() 
  ↓
loginWithRedirect() [Auth0 SDK]
  ↓
Auth0 issues JWT token
  ↓
Redirects back to frontend with token
```

---

### Step 2: Frontend Stores JWT and Gets User Info

**File:** `RAG_Frontend/src/context/AuthContext.jsx` (Line 21-45)

```javascript
export const AuthProvider = ({ children }) => {
  const {
    isAuthenticated,
    isLoading: auth0Loading,
    user: auth0User,
    getAccessTokenSilently,  // ← Gets JWT from Auth0
  } = useAuth0();

  useEffect(() => {
    const loadRole = async () => {
      if (!isAuthenticated) {
        setRole(null);
        setRoleLoading(false);
        return;
      }

      try {
        // Step 1: Get JWT token
        const token = await getAccessTokenSilently();

        // Step 2: Send JWT to backend
        const response = await fetch(
          `http://localhost:8000/api/me`,
          {
            headers: {
              Authorization: `Bearer ${token}`,  // ← JWT in header
            },
          }
        );

        // Step 3: Get user info including role
        const data = await response.json();
        const roles = data.claims?.[ROLES_CLAIM] || [];
        setRole(roles.includes('admin') ? 'admin' : 'user');
      } catch (error) {
        console.error('Failed to load user role:', error);
        setRole(null);
      } finally {
        setRoleLoading(false);
      }
    };

    loadRole();
  }, [isAuthenticated, getAccessTokenSilently]);
};
```

**Function Stack:**
```
loadRole() 
  ↓
getAccessTokenSilently() [Auth0 SDK]
  ↓
Returns JWT token
  ↓
fetch('/api/me', { Authorization: Bearer {JWT} })
  ↓
Wait for response
```

---

### Step 3: API Gateway Receives JWT and Validates It

**File:** `api_gateway/main.py` (Line 47)

```python
@app.get("/api/me")
def get_me(current_user=Depends(get_current_user)):
    return{
        "user_id": current_user["sub"],
        "claims": current_user,
    }
```

**Dependency:** `get_current_user` (Line 47) triggers the JWT validation

**Function Stack:**
```
GET /api/me
  ↓
FastAPI calls dependency: Depends(get_current_user)
  ↓
get_current_user() [FULL VALIDATION HERE]
```

---

### Step 4: JWT Validation Function

**File:** `api_gateway/auth.py` (Line 27-54)

```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials  # Extract token: "Bearer XXX" → "XXX"

    try:
        # STEP 1: Get Auth0's public signing key
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        # ↓ jwks_client = PyJWKClient(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
        # ↓ Fetches public keys from Auth0

        # STEP 2: Decode and verify JWT
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],  # RSA Signature (asymmetric)
            audience=AUTH0_AUDIENCE,  # Verify audience
            issuer=ISSUER,  # Verify issuer
        )
        # ↓ Returns decoded JWT payload if valid

        # STEP 3: Create/update user in database
        upsert_user(payload)  # ← Saves to MySQL

        # STEP 4: Return decoded claims
        return payload

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
```

**Validation Checks:**
```
✓ Signature verification (using Auth0's public key)
✓ Expiration check (exp claim)
✓ Audience verification (aud claim)
✓ Issuer verification (iss claim)
```

**Function Stack:**
```
get_current_user()
  ├─ Depends(security) 
  │   ↓
  │   HTTPBearer() extracts "Authorization: Bearer XXX"
  │
  ├─ jwks_client.get_signing_key_from_jwt(token)
  │   ↓
  │   PyJWKClient.get() → HTTP to Auth0 JWKS endpoint
  │   Returns: JWK signing key
  │
  ├─ jwt.decode()
  │   ↓
  │   Validates signature, exp, aud, iss
  │   Returns: payload dict
  │
  └─ upsert_user(payload)
      ↓
      Saves to MySQL [See Step 5]
```

---

### Step 5: Upsert User in Database

**File:** `api_gateway/user_service.py` (Line 5-45)

```python
def upsert_user(user_data: dict):
    # Extract from JWT payload
    auth0_user_id = user_data.get("sub")
    email = user_data.get("https://myapp.example.com/email")
    name = user_data.get("https://myapp.example.com/name")
    roles = user_data.get("https://myapp.example.com/roles", [])
    role = "admin" if "admin" in roles else "user"

    # Open database connection
    db = SessionLocal()  # ← Creates MySQL session

    try:
        # Query: Does user exist?
        user = db.scalar(
            select(User).where(
                User.auth0_user_id == auth0_user_id
            )
        )

        if user is None:
            # CREATE: Insert new user
            user = User(
                auth0_user_id=auth0_user_id,
                email=email or "",
                name=name,
                role=role,
                created_at=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc),
            )
            db.add(user)

        else:
            # UPDATE: Update existing user
            user.email = email or user.email
            user.name = name
            user.role = role
            user.last_login = datetime.now(timezone.utc)

        db.commit()  # ← Save to MySQL
```

**Database Table:**
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    auth0_user_id VARCHAR(255) UNIQUE,
    email VARCHAR(255),
    name VARCHAR(255),
    role ENUM('admin', 'user'),
    created_at TIMESTAMP,
    last_login TIMESTAMP
);
```

**Function Stack:**
```
upsert_user(payload)
  ├─ SessionLocal()
  │   ↓
  │   Creates connection to MySQL
  │
  ├─ db.scalar(select(User).where(...))
  │   ↓
  │   Query database: SELECT * FROM users WHERE auth0_user_id = ?
  │
  ├─ IF NOT EXISTS:
  │   User()  ← Create ORM object
  │   db.add(user)
  │   db.commit()  ← INSERT into MySQL
  │
  └─ IF EXISTS:
      Update fields
      db.commit()  ← UPDATE MySQL
```

---

### Step 6: Frontend Receives User Info and Routes

**File:** `RAG_Frontend/src/pages/Login/LoginPage.jsx` (Line 18-20)

```javascript
useEffect(() => {
  if (!isLoading && isLoggedIn) {
    // Routes based on role
    navigate(isAdmin ? '/admin' : '/chat', { replace: true });
  }
}, [isLoggedIn, isAdmin, isLoading, navigate]);
```

**Complete Login Flow Summary:**
```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Frontend: handleLogin() → Auth0 login page                   │
│ 2. Auth0: Authenticates user → Issues JWT token                │
│ 3. Frontend: AuthProvider useEffect → getAccessTokenSilently()  │
│ 4. Frontend: fetch('/api/me', { Authorization: Bearer {JWT} })  │
│ 5. Backend: get_current_user() dependency                       │
│    - Extracts token                                              │
│    - Fetches Auth0 public key                                   │
│    - Verifies signature, expiration, audience, issuer           │
│    - Returns decoded payload                                    │
│ 6. Backend: get_me() → get_current_user() returns payload       │
│    - Calls upsert_user(payload)                                 │
│    - Saves to MySQL                                             │
│    - Returns { user_id, claims }                                │
│ 7. Frontend: Receives response                                  │
│    - Extracts role from claims                                  │
│    - navigate('/chat') or navigate('/admin')                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. CHAT FLOW - Code Level Trace

### Step 1: User Types Message and Sends

**File:** `RAG_Frontend/src/pages/Chat/ChatPage.jsx` (Line 90+)

```javascript
const handleSendMessage = async () => {
  const userMessage = input;
  setInput('');
  setTyping(true);

  try {
    // Get JWT token from Auth0
    const token = await getAccessTokenSilently();

    // Send to backend
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,  // ← JWT token
      },
      body: JSON.stringify({
        question: userMessage,
        conversation_id: activeChatId,  // null for new chat
      }),
    });

    const data = await response.json();
    // Add to messages display
  } catch (error) {
    console.error('Failed to send message:', error);
  } finally {
    setTyping(false);
  }
};
```

**Function Stack:**
```
handleSendMessage()
  ├─ getAccessTokenSilently() [Auth0]
  │   ↓
  │   Returns JWT token
  │
  └─ fetch('/api/chat', {
       POST,
       Authorization: Bearer {JWT},
       body: { question, conversation_id }
     })
```

---

### Step 2: API Gateway Receives Chat Request

**File:** `api_gateway/routes/chat.py` (Line 40-71)

```python
@router.post("/api/chat")
async def chat(
    request: ChatRequest,  # { question, conversation_id }
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),  # ← JWT VALIDATION HERE
):
    user_id = current_user["sub"]  # Extract user_id from JWT

    # STEP 1: Create or fetch conversation
    if request.conversation_id is None:
        # CREATE NEW CONVERSATION
        conversation = create_conversation(
            db=db,
            user_id=user_id,
            title=request.question[:50],  # First 50 chars as title
        )
        conversation_id = conversation.id

    else:
        # FETCH EXISTING CONVERSATION
        conversation = get_conversation(
            db=db,
            conversation_id=request.conversation_id,
            user_id=user_id
        )

        if conversation is None:
            return {"error": "Conversation not found"}

        conversation_id = conversation.id

    # STEP 2: Save user's message
    add_message(
        db=db,
        conversation_id=conversation_id,
        role="user",
        content=request.question,
    )

    # STEP 3: Call RAG Service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{RAG_SERVICE_URL}/internal/query",
            json={"question": request.question},
            headers=INTERNAL_AUTH_HEADERS,  # X-Internal-Secret
            timeout=None,
        )

        response.raise_for_status()
        rag_result = response.json()

    answer = rag_result["answer"]

    # STEP 4: Save assistant's response
    add_message(
        db=db,
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
    )

    # STEP 5: Return to frontend
    return {
        "answer": answer,
        "conversation_id": conversation_id,
    }
```

**Function Stack:**
```
POST /api/chat
  │
  ├─ Depends(get_current_user)
  │   ↓
  │   Validates JWT (same as /api/me)
  │   Returns: payload with user_id
  │
  ├─ create_conversation()
  │   ↓
  │   SQL: INSERT INTO conversations (user_id, title)
  │   Returns: conversation.id
  │
  ├─ add_message(role="user", ...)
  │   ↓
  │   SQL: INSERT INTO messages (conversation_id, role, content)
  │
  ├─ httpx.post('/internal/query')
  │   ↓
  │   [See Step 3 below]
  │
  ├─ add_message(role="assistant", ...)
  │   ↓
  │   SQL: INSERT INTO messages (conversation_id, role, content)
  │
  └─ return { answer, conversation_id }
```

---

### Step 3: API Gateway Calls RAG Service

**File:** `api_gateway/internal_client.py` (Line 3-4)

```python
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET")
INTERNAL_AUTH_HEADERS = {"X-Internal-Secret": INTERNAL_SERVICE_SECRET}
```

**Important:** This is NOT JWT. It's a shared secret for service-to-service communication.

---

### Step 4: RAG Service Processes Query

**File:** `rag_service/main.py` (Line 9)

```python
app = FastAPI(
    title="Hybrid RAG Service",
    version="1.0.0",
)

@app.get("/internal/health")
def health_check():
    return {"status": "ok", "service": "rag-service"}
```

**Includes router:** `rag_service/routes/query.py`

---

### Step 5: RAG Query Route

**File:** `rag_service/routes/query.py` (Line 18-60)

```python
@router.post("/internal/query")
@traceable(name="RAG Query", tags=["rag", "query"])
def query_rag(request: QueryRequest):  # { question }
    # STEP 1: RETRIEVAL (Hybrid Search)
    retrieval_start = time.perf_counter()

    candidates = hybrid_search(
        request.question,
        k=8  # Get top 8 candidates
    )

    retrieval_ms = round((time.perf_counter() - retrieval_start) * 1000)

    # STEP 2: RERANKING
    rerank_start = time.perf_counter()

    reranked_documents = rerank_documents(
        request.question,
        candidates,
        top_k=5,  # Keep top 5 after reranking
        model="claude"
    )

    reranking_ms = round((time.perf_counter() - rerank_start) * 1000)

    # STEP 3: GENERATION (LLM)
    generation_start = time.perf_counter()

    answer = generate_answer(
        request.question,
        reranked_documents,
        model="claude"
    )

    generation_ms = round((time.perf_counter() - generation_start) * 1000)

    run_tree = get_current_run_tree()
    trace_url = run_tree.get_url() if run_tree is not None else None

    return {
        "answer": answer,
        "context": [document.page_content for document in reranked_documents],
        "timings": {
            "retrieval_ms": retrieval_ms,
            "reranking_ms": reranking_ms,
            "generation_ms": generation_ms,
        },
        "trace_url": trace_url,
    }
```

**Function Stack:**
```
query_rag(request: { question })
  │
  ├─ hybrid_search(question, k=8)
  │   [See Step 6 below]
  │
  ├─ rerank_documents(question, candidates, top_k=5)
  │   ↓
  │   For each candidate:
  │     score = claude_lm.score(question, doc)
  │   Sort by score
  │   Keep top 5
  │
  ├─ generate_answer(question, reranked_documents)
  │   ↓
  │   Prompt = f"Context: {docs}\n\nQuestion: {question}"
  │   answer = claude_api.call(prompt)
  │
  └─ return {
       "answer": answer,
       "context": [...],
       "timings": {...},
       "trace_url": trace_url
     }
```

---

### Step 6: Hybrid Search - Retrieval

**File:** `rag_core/retrieval/hybrid_retrieval.py` (Line 17-45)

```python
def hybrid_search(question, k=8, verbose=False, metadata_filter=None):
    start_time = time.perf_counter()

    # SEMANTIC SEARCH (Vector similarity)
    semantic_results = retrieve_documents(
        question,
        k=8,  # Get 8 semantically similar
        metadata_filter=metadata_filter
    )
    # ↓ Uses Chroma vector database
    # ↓ Embedding model: sentence-transformers/all-MiniLM-L6-v2

    # LEXICAL SEARCH (BM25 keyword matching)
    bm25_results = lexical_search(
        question,
        k=8,  # Get 8 keyword matches
        metadata_filter=metadata_filter
    )
    # ↓ Uses BM25 algorithm
    # ↓ In-memory index

    # MERGE using RRF (Reciprocal Rank Fusion)
    # Combine rankings: RRF score = sum(1 / (rank + k))
    # Return: Top k=8 merged results
```

**Detailed Sub-functions:**

### Semantic Retrieval (Vector Search)

**File:** `rag_core/retrieval/semantic_retrieval.py`

```python
def retrieve_documents(question, k=8, metadata_filter=None):
    # Step 1: Convert question to embedding vector
    query_embedding = embedding_model.embed_query(question)
    # ↓ 1536-dim vector using all-MiniLM-L6-v2

    # Step 2: Search Chroma vector database
    results = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=k,  # Get top k (8)
        where=metadata_filter,
    )
    # Returns: Top 8 documents by cosine similarity

    # Step 3: Convert to Document objects
    documents = [Document(...) for result in results]
    return documents
```

### Lexical Retrieval (BM25)

**File:** `rag_core/retrieval/lexical_retrieval.py`

```python
def lexical_search(question, k=8, metadata_filter=None):
    # Step 1: BM25 ranking
    scores = bm25_index.get_scores(tokenize(question))
    # ↓ Scores documents based on term frequency

    # Step 2: Get top k documents
    top_docs = sorted(scores, key=lambda x: x[1], reverse=True)[:k]

    # Step 3: Convert to Document objects
    documents = [Document(...) for doc, score in top_docs]
    return documents
```

### Merge Results

```python
# RRF combines rankings:
# semantic_rank = [doc1, doc2, doc3, ...]  (by cosine similarity)
# lexical_rank = [doc4, doc2, doc1, ...]   (by BM25)

# RRF score:
# doc1_score = 1/(semantic_rank[0] + 60) + 1/(lexical_rank[2] + 60)
# doc2_score = 1/(semantic_rank[1] + 60) + 1/(lexical_rank[1] + 60)
# ...

# Final: Sort by RRF score, keep top k=8
```

---

### Step 7: Reranking - Relevance Scoring

**File:** `rag_core/reranking/reranking.py`

```python
def rerank_documents(question, candidates, top_k=5, model="claude"):
    scored_docs = []

    for candidate in candidates:
        # Score each candidate using Claude
        score = score_relevance(
            question,
            candidate,
            model="claude"
        )
        # ↓ Calls Claude API with relevance prompt
        # ↓ Claude returns 0-1 score

        scored_docs.append((candidate, score))

    # Sort by score (highest first)
    scored_docs.sort(key=lambda x: x[1], reverse=True)

    # Keep top k=5
    return [doc for doc, score in scored_docs[:top_k]]
```

---

### Step 8: Generation - LLM Answer

**File:** `rag_core/generation/generation.py`

```python
def generate_answer(question, documents, model="claude"):
    # Step 1: Build context from documents
    context = "\n".join([
        f"Document {i+1}: {doc.page_content}"
        for i, doc in enumerate(documents)
    ])

    # Step 2: Build prompt
    prompt = f"""Based on the following documents, answer the question.

Documents:
{context}

Question: {question}

Answer:"""

    # Step 3: Call Claude LLM
    response = anthropic_client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    # Step 4: Extract answer
    answer = response.content[0].text
    return answer
```

---

### Step 9: Return Answer to API Gateway

**File:** `rag_service/routes/query.py` (Line 59-70)

```python
return {
    "answer": answer,
    "context": [document.page_content for document in reranked_documents],
    "timings": {
        "retrieval_ms": retrieval_ms,
        "reranking_ms": reranking_ms,
        "generation_ms": generation_ms,
    },
    "trace_url": trace_url,
}
```

**API Gateway receives this response**

---

### Step 10: API Gateway Saves Message and Returns

**File:** `api_gateway/routes/chat.py` (Line 67-79)

```python
answer = rag_result["answer"]

# Save assistant's response to MySQL
add_message(
    db=db,
    conversation_id=conversation_id,
    role="assistant",
    content=answer,
)

# Return to frontend
return {
    "answer": answer,
    "conversation_id": conversation_id,
}
```

**Function Stack:**
```
add_message(conversation_id, role="assistant", content=answer)
  └─ SQL: INSERT INTO messages (conversation_id, role, content, created_at)
     VALUES (?, 'assistant', ?, NOW())
```

---

### Step 11: Frontend Displays Answer

**File:** `RAG_Frontend/src/pages/Chat/ChatPage.jsx` (continuation)

```javascript
const data = await response.json();
setMessages([
  ...messages,
  { id: msg_id++, role: 'user', text: userMessage, time: new Date() },
  { id: msg_id++, role: 'bot', text: data.answer, time: new Date() }
]);
setActiveChatId(data.conversation_id);
```

**Complete Chat Flow:**
```
┌──────────────────────────────────────────────────────────────────┐
│ 1. Frontend: handleSendMessage()                                 │
│    - Gets JWT token from Auth0                                   │
│    - POST /api/chat { question, conversation_id }                │
│                                                                  │
│ 2. API Gateway: POST /api/chat                                   │
│    - Validates JWT                                               │
│    - Creates/fetches conversation (MySQL)                        │
│    - Saves user message (INSERT INTO messages)                   │
│    - Calls RAG Service POST /internal/query                      │
│                                                                  │
│ 3. RAG Service: POST /internal/query                             │
│    a) hybrid_search(k=8)                                         │
│       - semantic_search(): Chroma vector DB                      │
│       - lexical_search(): BM25 index                             │
│       - merge with RRF                                           │
│    b) rerank_documents(top_k=5)                                  │
│       - score with Claude                                        │
│    c) generate_answer()                                          │
│       - build prompt                                             │
│       - call Claude API                                          │
│    - Returns { answer, context, timings }                        │
│                                                                  │
│ 4. API Gateway: Receives answer                                  │
│    - Saves assistant message (INSERT INTO messages)              │
│    - Returns { answer, conversation_id }                         │
│                                                                  │
│ 5. Frontend: Receives response                                   │
│    - Displays answer to user                                     │
│    - Saves conversation_id for future messages                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. ADMIN OPERATIONS - Code Level Trace

### Admin Dashboard Access

**File:** `api_gateway/routes/admin.py` (Line 20-35)

```python
@router.get("/api/admin/overview")
async def get_overview(
    current_user=Depends(require_admin),  # ← ROLE CHECK HERE
):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ADMIN_SERVICE_URL}/internal/overview",
            headers=INTERNAL_AUTH_HEADERS,
            timeout=10,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )
```

**Role Check Function:**

**File:** `api_gateway/auth.py` (Line 56-66)

```python
def require_admin(
    current_user=Depends(get_current_user)
):
    ROLES_CLAIM = "https://myapp.example.com/roles"
    roles = current_user.get(ROLES_CLAIM, [])

    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user
```

**Function Stack:**
```
GET /api/admin/overview
  │
  ├─ Depends(require_admin)
  │   ├─ Depends(get_current_user)
  │   │   ├─ Validates JWT
  │   │   ├─ Calls upsert_user()
  │   │   └─ Returns payload
  │   │
  │   └─ Checks if "admin" in roles claim
  │       ├─ YES: Continue
  │       └─ NO: raise HTTPException(403)
  │
  └─ httpx.get('/internal/overview', headers=INTERNAL_AUTH_HEADERS)
```

---

## 4. DOCUMENT UPLOAD - Code Level Trace

**File:** `api_gateway/routes/documents.py` (Line 25-45)

```python
@router.post("/api/admin/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(require_admin),  # ← Admin check
):
    file_content = await file.read()

    # Forward to Document Service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DOCUMENT_SERVICE_URL}/internal/documents",
            files={
                "file": (
                    file.filename,
                    file_content,
                    file.content_type,
                )
            },
            headers=INTERNAL_AUTH_HEADERS,
            timeout=None,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )
```

**Function Stack:**
```
POST /api/admin/documents
  │
  ├─ Depends(require_admin)
  │   └─ [Same as above - validate JWT + check admin role]
  │
  ├─ await file.read()
  │   └─ Reads uploaded file into memory
  │
  └─ httpx.post('/internal/documents')
      └─ Sends to Document Service (Port 8002)
         [Document Service processes: parse → chunk → embed → store]
```

---

## 5. DATABASE OPERATIONS - SQL Queries

### Create Conversation

**File:** `api_gateway/crud.py` (hypothetical)

```python
def create_conversation(db, user_id, title):
    conversation = Conversation(
        user_id=user_id,
        title=title,
        created_at=datetime.now(timezone.utc)
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)  # ← Fetch ID from DB
    return conversation
    
    # SQL Generated:
    # INSERT INTO conversations (user_id, title, created_at)
    # VALUES (?, ?, ?)
    # COMMIT;
    # SELECT * FROM conversations WHERE id = LAST_INSERT_ID()
```

### Save Message

```python
def add_message(db, conversation_id, role, content):
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc)
    )
    db.add(message)
    db.commit()
    
    # SQL Generated:
    # INSERT INTO messages (conversation_id, role, content, created_at)
    # VALUES (?, ?, ?, ?)
    # COMMIT;
```

### Fetch Conversation

```python
def get_conversation(db, conversation_id, user_id):
    return db.scalar(
        select(Conversation).where(
            (Conversation.id == conversation_id) &
            (Conversation.user_id == user_id)
        )
    )
    
    # SQL Generated:
    # SELECT * FROM conversations 
    # WHERE id = ? AND user_id = ?
```

### Fetch Conversations List

```python
def get_user_conversations(db, user_id):
    return db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    ).all()
    
    # SQL Generated:
    # SELECT * FROM conversations 
    # WHERE user_id = ? 
    # ORDER BY created_at DESC
```

---

## Summary: Key Function Call Sequences

### **LOGIN:**
```
LoginPage.handleLogin()
  → Auth0.loginWithRedirect()
  → Auth0 login page
  → Auth0 issues JWT
  → AuthContext.useEffect()
  → AuthContext.getAccessTokenSilently()
  → fetch('/api/me', Authorization: Bearer JWT)
  → get_me()
  → get_current_user()
  → jwks_client.get_signing_key_from_jwt()
  → jwt.decode()
  → upsert_user()
  → User saved to MySQL
  → Returns { user_id, claims, roles }
  → Frontend routes to /chat or /admin
```

### **CHAT:**
```
ChatPage.handleSendMessage()
  → fetch('/api/chat', Authorization: Bearer JWT)
  → chat()
  → get_current_user()
  → [JWT validation]
  → create_conversation() or get_conversation()
  → add_message(role="user")
  → httpx.post('/internal/query', X-Internal-Secret)
  → query_rag()
  → hybrid_search()
    ├─ retrieve_documents() [Chroma vector DB]
    └─ lexical_search() [BM25]
  → rerank_documents() [Claude LLM scoring]
  → generate_answer() [Claude LLM generation]
  → add_message(role="assistant")
  → return { answer, conversation_id }
  → ChatPage displays answer
```

### **ADMIN:**
```
Frontend GET /api/admin/overview
  → get_overview()
  → require_admin()
    ├─ get_current_user()
    └─ Check if "admin" in roles
  → httpx.get('/internal/overview', X-Internal-Secret)
  → Admin Service retrieves stats
  → return data
```

