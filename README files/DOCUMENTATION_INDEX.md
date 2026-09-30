# RAG Backend - Documentation Index

I've created **4 comprehensive guides** to help you understand the complete end-to-end workflow:

---

## 📚 Documentation Overview

### 1. **END_TO_END_WORKFLOW.md** ← START HERE
**Best for:** Understanding the complete flow from login through chat to responses

**Contains:**
- ✅ Architecture overview with visual diagrams
- ✅ Complete login flow (9 steps)
- ✅ Complete chat flow (11 steps)
- ✅ Admin operations
- ✅ Document management
- ✅ JWT vs Internal Service Secret comparison
- ✅ Data flow diagrams
- ✅ Function call chains

**Read this first if you want:** Complete step-by-step explanation

---

### 2. **QUICK_REFERENCE.md** ← USE FOR QUICK LOOKUPS
**Best for:** Quick visual reference and summaries

**Contains:**
- ✅ Who generates JWT? (Answer: Auth0)
- ✅ JWT validation flow (visual)
- ✅ Microservice communication map
- ✅ Complete request-response cycles
- ✅ Database schema overview
- ✅ Authentication & authorization matrix
- ✅ RAG pipeline stages (detailed)
- ✅ Error handling flow
- ✅ Environment variables explanation
- ✅ Flow sequence diagram

**Use this when:** You need a quick visual or table reference

---

### 3. **DETAILED_CODE_TRACE.md** ← FOR DEVELOPERS
**Best for:** Understanding exact code, files, functions, and SQL

**Contains:**
- ✅ Login flow with code snippets and line numbers
- ✅ JWT validation function (exact code)
- ✅ User upsert to database (exact SQL)
- ✅ Chat flow with code snippets
- ✅ RAG service query processing (exact code)
- ✅ Hybrid search implementation (exact code)
- ✅ Reranking logic (exact code)
- ✅ LLM generation (exact code)
- ✅ Admin operations (exact code)
- ✅ Document upload (exact code)
- ✅ Database operations with SQL queries
- ✅ Function call sequences

**Use this when:** You want to understand the actual code implementation

---

## 🗂️ Quick Navigation by Topic

### I want to understand...

**...How authentication works:**
→ Read: END_TO_END_WORKFLOW.md → STEP 1 (LOGIN FLOW)
→ Or: QUICK_REFERENCE.md → Section 2 & 6
→ Or: DETAILED_CODE_TRACE.md → Section 1-5

**...How the chat works:**
→ Read: END_TO_END_WORKFLOW.md → STEP 2 (USER CHAT FLOW)
→ Or: QUICK_REFERENCE.md → Section 4
→ Or: DETAILED_CODE_TRACE.md → Section 2

**...How RAG retrieval works:**
→ Read: END_TO_END_WORKFLOW.md → STEP 2.5-2.7
→ Or: QUICK_REFERENCE.md → Section 7
→ Or: DETAILED_CODE_TRACE.md → Section 6

**...Which service does what:**
→ Read: END_TO_END_WORKFLOW.md → Architecture Overview
→ Or: QUICK_REFERENCE.md → Section 3
→ Or: DETAILED_CODE_TRACE.md

**...How JWT validation works:**
→ Read: END_TO_END_WORKFLOW.md → STEP 1.4
→ Or: QUICK_REFERENCE.md → Section 2 & 6
→ Or: DETAILED_CODE_TRACE.md → Section 1.4

**...How microservices communicate:**
→ Read: END_TO_END_WORKFLOW.md → JWT vs INTERNAL SERVICE SECRET
→ Or: QUICK_REFERENCE.md → Section 3 & 6
→ Or: DETAILED_CODE_TRACE.md

**...How admin operations work:**
→ Read: END_TO_END_WORKFLOW.md → STEP 3-4
→ Or: DETAILED_CODE_TRACE.md → Section 3

**...Database operations:**
→ Read: END_TO_END_WORKFLOW.md → Various steps mention databases
→ Or: QUICK_REFERENCE.md → Section 5
→ Or: DETAILED_CODE_TRACE.md → Section 5

**...The exact code flow:**
→ Read: DETAILED_CODE_TRACE.md (entire document)

---

## 🔑 Key Concepts Quick Answers

### Q: Who generates JWT?
**A:** Auth0 (external SaaS). Your backend doesn't generate JWT.
- **Where:** Auth0 cloud
- **How:** User logs in → Auth0 authenticates → Issues JWT
- **Details:** END_TO_END_WORKFLOW.md → Step 1.1-1.2

### Q: How does the backend validate JWT?
**A:** Using Auth0's public key (RS256 algorithm, asymmetric).
- **Where:** API Gateway (Port 8000)
- **How:** Fetch Auth0's public key → Verify signature
- **Details:** DETAILED_CODE_TRACE.md → Section 1.4

### Q: What's the difference between JWT and internal service secret?
**A:** 
- **JWT:** Frontend authentication (Auth0)
- **Secret:** Service-to-service authentication (shared secret)
- **Details:** END_TO_END_WORKFLOW.md → "JWT vs INTERNAL SERVICE SECRET"

### Q: How does the frontend communicate with services?
**A:** Only through API Gateway (Port 8000). Never directly to other services.
- **Flow:** Frontend → API Gateway → (RAG Service, Admin Service, Document Service)
- **Details:** QUICK_REFERENCE.md → Section 3

### Q: What's the RAG pipeline?
**A:** Retrieve → Rerank → Generate
1. **Retrieve:** Hybrid search (semantic + lexical)
2. **Rerank:** Score relevance with Claude
3. **Generate:** Generate answer with Claude
- **Details:** QUICK_REFERENCE.md → Section 7

### Q: Where is data stored?
**A:**
- **MySQL:** User info, conversations, messages (API Gateway DB)
- **Chroma:** Document embeddings (vector DB)
- **Files:** Uploaded documents (disk/storage)
- **Details:** QUICK_REFERENCE.md → Section 5

### Q: Which ports run which services?
**A:**
- Port 5173: Frontend (React)
- Port 8000: API Gateway
- Port 8001: RAG Service
- Port 8002: Document Service
- Port 8003: Admin Service
- **Details:** END_TO_END_WORKFLOW.md → Port Summary

### Q: How does role-based access work?
**A:**
- JWT contains role claim: `https://myapp.example.com/roles`
- API Gateway checks role for admin endpoints
- If not admin → 403 Forbidden
- **Details:** DETAILED_CODE_TRACE.md → Section 3

### Q: What happens when a user sends a message?
**A:**
1. Frontend → API Gateway with JWT
2. API Gateway validates JWT, creates conversation
3. Saves user message to MySQL
4. Calls RAG Service
5. RAG Service: Retrieve → Rerank → Generate
6. Saves assistant response to MySQL
7. Returns answer to frontend
- **Details:** DETAILED_CODE_TRACE.md → Section 2

### Q: What happens when an admin uploads a document?
**A:**
1. Frontend → API Gateway with JWT
2. API Gateway checks if user is admin
3. Calls Document Service
4. Document Service: Parse → Chunk → Embed → Store in Chroma
5. Returns document ID
- **Details:** DETAILED_CODE_TRACE.md → Section 4

---

## 📊 High-Level Flow Summary

```
LOGIN:
  User → Auth0 → JWT → Frontend → API Gateway → MySQL

CHAT:
  User Question 
    → Frontend (JWT)
    → API Gateway (JWT validation)
    → RAG Service (Secret header)
    → Retrieve (Chroma + BM25)
    → Rerank (Claude)
    → Generate (Claude)
    → Save to MySQL
    → Return to Frontend
    → Display Answer

ADMIN:
  Admin User (JWT with "admin" role)
    → Frontend
    → API Gateway (JWT + role check)
    → Admin/Document Service (Secret header)
    → Process
    → Return to Frontend
```

---

## 🔍 File-to-Document Mapping

### Frontend Files Explained
- `RAG_Frontend/src/pages/Login/LoginPage.jsx` → END_TO_END_WORKFLOW.md Step 1.1
- `RAG_Frontend/src/context/AuthContext.jsx` → END_TO_END_WORKFLOW.md Step 1.3 & 1.6
- `RAG_Frontend/src/pages/Chat/ChatPage.jsx` → DETAILED_CODE_TRACE.md Section 2.1

### Backend Files Explained
- `api_gateway/auth.py` → DETAILED_CODE_TRACE.md Section 1.4
- `api_gateway/user_service.py` → DETAILED_CODE_TRACE.md Section 1.5
- `api_gateway/routes/chat.py` → DETAILED_CODE_TRACE.md Section 2.2
- `api_gateway/routes/admin.py` → DETAILED_CODE_TRACE.md Section 3
- `api_gateway/routes/documents.py` → DETAILED_CODE_TRACE.md Section 4
- `rag_service/routes/query.py` → DETAILED_CODE_TRACE.md Section 2.4-2.8
- `rag_core/retrieval/hybrid_retrieval.py` → DETAILED_CODE_TRACE.md Section 2.6

---

## 💡 Key Files to Know

### Authentication & Authorization
- `api_gateway/auth.py` - JWT validation, role checking

### Chat & Conversation
- `api_gateway/routes/chat.py` - Chat endpoints
- `api_gateway/crud.py` - Conversation/message CRUD
- `api_gateway/user_service.py` - User management

### RAG Pipeline
- `rag_service/routes/query.py` - Main RAG query endpoint
- `rag_core/retrieval/hybrid_retrieval.py` - Hybrid search
- `rag_core/retrieval/semantic_retrieval.py` - Vector search
- `rag_core/retrieval/lexical_retrieval.py` - BM25 search
- `rag_core/reranking/reranking.py` - Document reranking
- `rag_core/generation/generation.py` - LLM answer generation

### Admin & Documents
- `admin_service/routes/admin.py` - Admin operations
- `document_service/routes/documents.py` - Document handling

---

## 🎯 Reading Recommendations

### For Project Managers
1. END_TO_END_WORKFLOW.md (Architecture Overview + High-level steps)
2. QUICK_REFERENCE.md (Section 1, 3, 10)

### For Backend Developers
1. DETAILED_CODE_TRACE.md (entire document)
2. END_TO_END_WORKFLOW.md (for context)
3. Code files directly

### For Frontend Developers
1. END_TO_END_WORKFLOW.md (Login flow, Chat flow)
2. QUICK_REFERENCE.md (Authentication matrix)
3. DETAILED_CODE_TRACE.md (Sections 2.1, 2.11)

### For DevOps/Infrastructure
1. END_TO_END_WORKFLOW.md (Port Summary, Environment Configuration)
2. QUICK_REFERENCE.md (Section 8)

### For New Team Members
1. END_TO_END_WORKFLOW.md (read all)
2. QUICK_REFERENCE.md (read all)
3. DETAILED_CODE_TRACE.md (as reference)

---

## ✅ Quick Verification Checklist

### Verify Your Understanding:

- [ ] Can you explain how JWT is generated? → Auth0
- [ ] Can you explain how JWT is validated? → Using Auth0's public key (RS256)
- [ ] Can you trace a user login from start to finish?
- [ ] Can you trace a chat message from user to answer?
- [ ] Can you explain the difference between JWT and internal secret?
- [ ] Can you name all 4 microservices and what each does?
- [ ] Can you explain the RAG pipeline (Retrieve, Rerank, Generate)?
- [ ] Can you explain how roles are checked for admin access?
- [ ] Can you name all 5 ports and what runs on each?
- [ ] Can you explain where data is stored (MySQL, Chroma, etc.)?

If you can answer all of these, you understand the system! 🎉

---

## 📞 When to Reference Each Document

| Scenario | Document |
|----------|----------|
| "Explain the system to me" | END_TO_END_WORKFLOW.md |
| "How does this endpoint work?" | DETAILED_CODE_TRACE.md |
| "Which service handles this?" | QUICK_REFERENCE.md Section 3 |
| "Show me the flow visually" | QUICK_REFERENCE.md |
| "What's the exact code?" | DETAILED_CODE_TRACE.md |
| "How many steps in login?" | END_TO_END_WORKFLOW.md Step 1 |
| "What database tables exist?" | QUICK_REFERENCE.md Section 5 |
| "Which files do I need to change?" | DETAILED_CODE_TRACE.md |
| "How is data validated?" | DETAILED_CODE_TRACE.md |
| "What are all the auth mechanisms?" | QUICK_REFERENCE.md Section 6 |

---

## 🚀 Next Steps

1. **Read:** START with END_TO_END_WORKFLOW.md
2. **Skim:** Review QUICK_REFERENCE.md for visual understanding
3. **Deep Dive:** Use DETAILED_CODE_TRACE.md when you need to modify code
4. **Reference:** Keep this index handy for quick lookups

---

**You now have everything you need to understand the RAG Backend system! 🎯**

