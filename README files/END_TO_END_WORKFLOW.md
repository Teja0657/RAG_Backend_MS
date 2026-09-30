# RAG Backend - Complete End-to-End Workflow

## Architecture Overview

```
┌─────────────────┐
│  RAG_Frontend   │ (React/Vite)
│  (Port 5173)    │
└────────┬────────┘
         │ HTTP + Auth0 JWT Token
         ▼
┌──────────────────────────────────────┐
│   API Gateway (Port 8000)            │
│   - Routes requests to services      │
│   - Validates JWT tokens             │
│   - Manages conversations/messages   │
└────┬──────┬──────────┬───────────────┘
     │      │          │
     ▼      ▼          ▼
  ┌──────┐ ┌───────┐ ┌──────────────┐
  │RAG   │ │Document│ │Admin Service │
  │Service│ │Service │ │(Port 8003)   │
  │(8001)│ │(8002) │ │              │
  └──────┘ └───────┘ └──────────────┘
     │
     ▼
  ┌─────────────────────┐
  │  rag_core module    │
  │ - Retrieval (hybrid)│
  │ - Reranking         │
  │ - Generation (LLM)  │
  └─────────────────────┘
     │
     ▼
  ┌─────────────────────┐
  │  Vector Store       │
  │  (Chroma DB)        │
  └─────────────────────┘
```

---

## STEP 1: LOGIN FLOW (Frontend → Auth0 → API Gateway)

### 1.1 User Visits Login Page
**File:** `RAG_Frontend/src/pages/Login/LoginPage.jsx`

```javascript
// User clicks login button
const handleLogin = () => {
  loginWithRedirect({ 
    appState: { returnTo: role === 'admin' ? '/admin' : '/chat' } 
  });
};
```

**What Happens:**
- Frontend uses **Auth0** (not self-hosted authentication)
- User is redirected to Auth0's login page
- After successful login, Auth0 issues a **JWT token**

### 1.2 Frontend Receives JWT Token from Auth0
**File:** `RAG_Frontend/src/context/AuthContext.jsx`

```javascript
const { getAccessTokenSilently } = useAuth0();

// Get JWT token from Auth0
const token = await getAccessTokenSilently();
```

**Token Structure:**
- Issued by: Auth0 (`https://{AUTH0_DOMAIN}/`)
- Contains claims:
  - `sub`: User ID (Auth0 unique identifier)
  - `https://myapp.example.com/email`: Email
  - `https://myapp.example.com/name`: User name
  - `https://myapp.example.com/roles`: Array of roles (["admin"] or ["user"])

### 1.3 Verify Role by Calling `/api/me` Endpoint
**File:** `RAG_Frontend/src/context/AuthContext.jsx`

```javascript
// Frontend sends JWT to API Gateway to fetch user info
const response = await fetch(
  `http://localhost:8000/api/me`,
  {
    headers: {
      Authorization: `Bearer ${token}`, // JWT token sent here
    },
  }
);

const data = await response.json();
const roles = data.claims?.[ROLES_CLAIM] || [];
const userRole = roles.includes('admin') ? 'admin' : 'user';
```

### 1.4 API Gateway Validates JWT
**File:** `api_gateway/main.py` → `api_gateway/auth.py`

```python
@app.get("/api/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "user_id": current_user["sub"],
        "claims": current_user,
    }
```

**JWT Validation Process:**

**File:** `api_gateway/auth.py` - `get_current_user()` function

```python
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials  # Extract token from "Bearer {token}"
    
    try:
        # Step 1: Get signing key from Auth0's JWKS endpoint
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Step 2: Decode and verify JWT using Auth0's public key
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],  # Auth0 uses RS256 (asymmetric)
            audience=AUTH0_AUDIENCE,  # Verify audience matches
            issuer=ISSUER,  # Verify issuer is Auth0
        )
        
        # Step 3: Upsert user into local database
        upsert_user(payload)
        
        return payload  # Return decoded claims
        
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

**JWT Validation Details:**
- **Where:** API Gateway (Port 8000)
- **How:** 
  - Fetches Auth0's public signing key from `.well-known/jwks.json`
  - Uses RS256 algorithm (RSA public/private key cryptography)
  - Verifies signature, expiration, audience, issuer
  - Is NOT self-signed; uses Auth0's certificate
- **Result:** Returns decoded JWT claims or 401 Unauthorized

### 1.5 Create/Update User in Database
**File:** `api_gateway/user_service.py` - `upsert_user()` function

```python
def upsert_user(user_data: dict):
    auth0_user_id = user_data.get("sub")
    email = user_data.get("https://myapp.example.com/email")
    name = user_data.get("https://myapp.example.com/name")
    roles = user_data.get("https://myapp.example.com/roles", [])
    role = "admin" if "admin" in roles else "user"
    
    db = SessionLocal()  # MySQL connection (API Gateway database)
    
    # Check if user exists
    user = db.scalar(select(User).where(User.auth0_user_id == auth0_user_id))
    
    if user is None:
        # Create new user
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
        # Update existing user
        user.email = email or user.email
        user.name = name
        user.role = role
        user.last_login = datetime.now(timezone.utc)
    
    db.commit()
```

**Database:** API Gateway MySQL database

### 1.6 Frontend Routes Based on Role
**File:** `RAG_Frontend/src/pages/Login/LoginPage.jsx`

```javascript
useEffect(() => {
  if (!isLoading && isLoggedIn) {
    // Redirect based on role
    navigate(isAdmin ? '/admin' : '/chat', { replace: true });
  }
}, [isLoggedIn, isAdmin, isLoading, navigate]);
```

**Result:** 
- Admin → `/admin` (Admin Dashboard)
- User → `/chat` (Chat Page)

---

## STEP 2: USER CHAT FLOW (Frontend → API Gateway → RAG Service)

### 2.1 User Submits Question on Chat Page
**File:** `RAG_Frontend/src/pages/Chat/ChatPage.jsx`

```javascript
const handleSendMessage = async () => {
  const userMessage = input;
  setInput('');
  setTyping(true);
  
  try {
    // Get JWT token
    const token = await getAccessTokenSilently();
    
    // Send message to backend
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        question: userMessage,
        conversation_id: activeChatId,  // null for new conversation
      }),
    });
    
    const data = await response.json();
    // Display answer to user
  } catch (error) {
    console.error('Failed to send message:', error);
  } finally {
    setTyping(false);
  }
};
```

**What Happens:**
1. User types message and clicks send
2. Frontend sends JWT token in Authorization header
3. Sends question + conversation_id to `/api/chat`

### 2.2 API Gateway Receives Chat Request
**File:** `api_gateway/routes/chat.py` - `chat()` endpoint

```python
@router.post("/api/chat")
async def chat(
    request: ChatRequest,  # { question, conversation_id }
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),  # JWT validation here
):
    user_id = current_user["sub"]  # Extract user ID from JWT
    
    # Step 1: Create or fetch conversation
    if request.conversation_id is None:
        # Create NEW conversation
        conversation = create_conversation(
            db=db,
            user_id=user_id,
            title=request.question[:50],  # First 50 chars as title
        )
        conversation_id = conversation.id
    else:
        # Fetch EXISTING conversation
        conversation = get_conversation(
            db=db,
            conversation_id=request.conversation_id,
            user_id=user_id
        )
        
        if conversation is None:
            return {"error": "Conversation not found"}
        
        conversation_id = conversation.id
    
    # Step 2: Save user's message to database
    add_message(
        db=db,
        conversation_id=conversation_id,
        role="user",
        content=request.question,
    )
    
    # Step 3: Send question to RAG Service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{RAG_SERVICE_URL}/internal/query",  # http://127.0.0.1:8001/internal/query
            json={"question": request.question},
            headers=INTERNAL_AUTH_HEADERS,  # Internal service secret (NOT JWT)
            timeout=None,
        )
        
        response.raise_for_status()
        rag_result = response.json()
    
    answer = rag_result["answer"]
    
    # Step 4: Save assistant's response to database
    add_message(
        db=db,
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
    )
    
    # Step 5: Return response to frontend
    return {
        "answer": answer,
        "conversation_id": conversation_id,
    }
```

**Database Operations:**
- **Database:** API Gateway MySQL
- **Tables:**
  - `conversations` (stores conversation metadata)
  - `messages` (stores all messages in conversations)

### 2.3 Internal Service Communication (Security)
**File:** `api_gateway/internal_client.py`

```python
import os

INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET")
INTERNAL_AUTH_HEADERS = {"X-Internal-Secret": INTERNAL_SERVICE_SECRET}
```

**Important:**
- API Gateway → RAG Service uses **internal service secret** (NOT JWT)
- JWT is for external requests (frontend)
- Internal services authenticate each other with a shared secret
- This secret is passed in `X-Internal-Secret` header

### 2.4 RAG Service Processes Question
**File:** `rag_service/main.py` → `rag_service/routes/query.py`

```python
@router.post("/internal/query")
@traceable(name="RAG Query", tags=["rag", "query"])
def query_rag(request: QueryRequest):
    # request.question = the user's question
    
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
    
    # STEP 3: GENERATION (LLM Answer)
    generation_start = time.perf_counter()
    
    answer = generate_answer(
        request.question,
        reranked_documents,
        model="claude"
    )
    
    generation_ms = round((time.perf_counter() - generation_start) * 1000)
    
    # Return to API Gateway
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

### 2.5 RAG Service - Step 1: Hybrid Retrieval
**File:** `rag_core/retrieval/hybrid_retrieval.py`

```python
def hybrid_search(question, k=8):
    # Combines semantic and lexical search
    
    # SEMANTIC SEARCH (vector similarity)
    semantic_results = retrieve_documents(
        question,
        k=8,  # Get 8 most similar vectors
    )
    # Uses Chroma DB (vector database)
    
    # BM25 LEXICAL SEARCH (keyword matching)
    bm25_results = lexical_search(
        question,
        k=8,  # Get 8 best keyword matches
    )
    # Uses in-memory BM25 index
    
    # Combine and rank using RRF (Reciprocal Rank Fusion)
    # Returns merged and deduplicated results (top k=8)
    return merged_results
```

**Retrieval Components:**
1. **Semantic Search** (`rag_core/retrieval/semantic_retrieval.py`)
   - Uses embedding model
   - Searches Chroma vector database
   - Finds semantically similar documents

2. **Lexical Search** (`rag_core/retrieval/lexical_retrieval.py`)
   - Uses BM25 algorithm
   - Keyword-based matching
   - Finds exact or partial keyword matches

### 2.6 RAG Service - Step 2: Reranking
**File:** `rag_core/reranking/reranking.py`

```python
def rerank_documents(question, candidates, top_k=5, model="claude"):
    # Rerank retrieved documents by relevance
    # Uses Claude LLM to score relevance
    # Returns top_k most relevant documents
    
    reranked = []
    for doc in candidates:
        score = score_relevance(question, doc)  # LLM scoring
        reranked.append((doc, score))
    
    # Sort by score and return top k
    return sorted(reranked, key=lambda x: x[1], reverse=True)[:top_k]
```

### 2.7 RAG Service - Step 3: Generation (LLM Answer)
**File:** `rag_core/generation/generation.py`

```python
def generate_answer(question, documents, model="claude"):
    # Build prompt with context from retrieved documents
    context = "\n".join([doc.page_content for doc in documents])
    
    prompt = f"""
    Context:
    {context}
    
    Question: {question}
    
    Answer based on the context above.
    """
    
    # Call Claude LLM API
    response = anthropic_client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text
```

---

## STEP 3: ADMIN OPERATIONS

### 3.1 Admin Dashboard Workflow
**File:** `api_gateway/routes/admin.py`

```python
@router.get("/api/admin/overview")
async def get_overview(
    current_user=Depends(require_admin),  # Checks if user is admin
):
    # require_admin verifies role from JWT
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ADMIN_SERVICE_URL}/internal/overview",  # http://127.0.0.1:8003/internal/overview
            headers=INTERNAL_AUTH_HEADERS,  # Internal service secret
            timeout=10,
        )
    
    return response.json()
```

### 3.2 Admin Authorization
**File:** `api_gateway/auth.py` - `require_admin()` function

```python
def require_admin(current_user=Depends(get_current_user)):
    ROLES_CLAIM = "https://myapp.example.com/roles"
    roles = current_user.get(ROLES_CLAIM, [])
    
    if "admin" not in roles:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    
    return current_user
```

**How Admin Role is Determined:**
1. JWT token contains `https://myapp.example.com/roles` claim
2. This is set in Auth0 configuration (custom claims)
3. API Gateway checks this claim during JWT decode
4. If "admin" is in roles array → user is admin

### 3.3 Admin Service Operations
**File:** `admin_service/routes/admin.py`

Examples:
- `/internal/overview` - Get dashboard stats
- `/internal/users` - List all users
- `/internal/stats` - Get RAG statistics
- `/internal/evaluation/run` - Run evaluation tests
- `/internal/test-chat` - Test chat functionality

**All admin endpoints:**
1. Require JWT validation at API Gateway (via `require_admin`)
2. Use internal service secret when calling Admin Service
3. Return data to frontend through API Gateway

---

## STEP 4: DOCUMENT MANAGEMENT (Admin Only)

### 4.1 Upload Document
**File:** `api_gateway/routes/documents.py`

```python
@router.post("/api/admin/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(require_admin),  # Admin check
):
    file_content = await file.read()
    
    # Forward to Document Service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DOCUMENT_SERVICE_URL}/internal/documents",  # http://127.0.0.1:8002/internal/documents
            files={
                "file": (file.filename, file_content, file.content_type)
            },
            headers=INTERNAL_AUTH_HEADERS,  # Internal service secret
            timeout=None,
        )
    
    return response.json()
```

### 4.2 Document Service Processing
**File:** `document_service/main.py` → `document_service/routes/documents.py`

When a document is uploaded:
1. Parse document (PDF, DOCX, TXT)
2. Split into chunks (from `rag_core/chunking/`)
3. Create embeddings (from `rag_core/embedding/`)
4. Store in Chroma vector database
5. Index for BM25 search

---

## JWT vs INTERNAL SERVICE SECRET

### JWT (User Authentication)
```
Frontend ──(JWT Bearer Token)──> API Gateway
                                  - Validates with Auth0
                                  - Checks user role
                                  - Extracts user_id
```

### Internal Service Secret (Service-to-Service)
```
API Gateway ──(X-Internal-Secret Header)──> RAG Service
                                            ├─> Admin Service
                                            └─> Document Service
                                            
Used for: Service-to-service communication
Not exposed to frontend
Shared via environment variable
```

---

## DATA FLOW DIAGRAM

```
USER TYPES QUESTION
        │
        ▼
┌─────────────────────────────────────┐
│ Frontend (ChatPage.jsx)             │
│ - Get JWT from Auth0                │
│ - Send: {question, conversation_id}│
└─────────────────────────────────────┘
        │
        │ POST /api/chat
        │ Header: Authorization: Bearer {JWT}
        ▼
┌─────────────────────────────────────┐
│ API Gateway (auth.py)               │
│ - Validate JWT signature            │
│ - Verify audience & issuer          │
│ - Extract user_id from sub claim    │
│ - Upsert user in database           │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ API Gateway (routes/chat.py)        │
│ - Create/fetch conversation         │
│ - Save user message to DB           │
└─────────────────────────────────────┘
        │
        │ POST /internal/query
        │ Header: X-Internal-Secret
        ▼
┌─────────────────────────────────────┐
│ RAG Service (routes/query.py)       │
│ 1. Hybrid Search (k=8)              │
│ 2. Rerank (top k=5)                 │
│ 3. Generate Answer (LLM)            │
└─────────────────────────────────────┘
        │
        │ Returns: answer + context
        ▼
┌─────────────────────────────────────┐
│ API Gateway (routes/chat.py)        │
│ - Save assistant message to DB      │
│ - Return {answer, conversation_id}  │
└─────────────────────────────────────┘
        │
        │ HTTP Response
        ▼
┌─────────────────────────────────────┐
│ Frontend (ChatPage.jsx)             │
│ - Display answer to user            │
│ - Display conversation_id for       │
│   future message continuity         │
└─────────────────────────────────────┘
```

---

## SUMMARY: FUNCTION CALL CHAIN

```
Login Flow:
─────────
1. User clicks "Login" → LoginPage.jsx handleLogin()
2. Redirects to Auth0 login page
3. User authenticates with Auth0
4. Auth0 returns JWT token to frontend
5. Frontend calls GET /api/me with JWT
6. API Gateway validates JWT in get_current_user()
7. API Gateway calls upsert_user() → Creates/updates user in MySQL
8. Frontend gets user info and role
9. Frontend navigates to /chat (user) or /admin (admin)

Chat Flow:
──────────
1. User types question → ChatPage.jsx handleSendMessage()
2. Frontend calls POST /api/chat with JWT token
3. API Gateway validates JWT in get_current_user()
4. API Gateway creates/fetches conversation with create_conversation()
5. API Gateway saves user message with add_message()
6. API Gateway calls RAG Service POST /internal/query
7. RAG Service calls hybrid_search() → semantic_retrieval() + lexical_search()
8. RAG Service calls rerank_documents() with Claude LLM
9. RAG Service calls generate_answer() with Claude LLM
10. RAG Service returns {answer, context, timings}
11. API Gateway saves assistant message with add_message()
12. API Gateway returns {answer, conversation_id} to frontend
13. Frontend displays answer to user

Admin Flow:
──────────
1. Admin user (role="admin" in JWT)
2. Frontend sends JWT to POST /api/admin/overview
3. API Gateway validates JWT in get_current_user()
4. API Gateway checks role with require_admin()
5. If not admin → raises HTTPException 403 Forbidden
6. If admin → API Gateway calls Admin Service /internal/overview
7. Admin Service returns statistics
8. API Gateway returns data to frontend

Key Points:
───────────
- JWT for external authentication (frontend)
- Internal Service Secret for internal communication
- Auth0 generates JWT, doesn't our backend
- All microservices validate through API Gateway (no direct frontend-to-service calls)
- MySQL stores conversations, messages, users
- Chroma DB stores document vectors
- RAG Pipeline: Retrieve → Rerank → Generate
```

---

## ENVIRONMENT CONFIGURATION

```bash
# Auth0
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_AUDIENCE=https://your-api-audience

# Service URLs
RAG_SERVICE_URL=http://127.0.0.1:8001
ADMIN_SERVICE_URL=http://127.0.0.1:8003
DOCUMENT_SERVICE_URL=http://127.0.0.1:8002

# Internal Communication
INTERNAL_SERVICE_SECRET=your-shared-secret

# Database (API Gateway)
DATABASE_URL=mysql+pymysql://user:password@localhost/rag_db

# LLM
ANTHROPIC_API_KEY=your-claude-api-key
OPENAI_API_KEY=your-openai-api-key (if using)

# Tracing
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=your-project-name
LANGSMITH_TRACING=true
```

---

## Port Summary

```
Port 5173  → RAG Frontend (Vite React app)
Port 8000  → API Gateway (Main backend entry point)
Port 8001  → RAG Service (Query processing)
Port 8002  → Document Service (Document management)
Port 8003  → Admin Service (Admin operations)
```

All frontend requests go through **Port 8000 (API Gateway)** - never directly to other services.

