# JWT & Auth0 - Complete Beginner's Guide with Real Examples

## Part 1: What is JWT? (Simple Explanation)

### JWT Definition
**JWT = JSON Web Token**

It's basically a **secure, encoded message** that contains information about a user, signed by someone (Auth0) so that nobody can fake it.

Think of it like a **passport:**
- Your passport has your info (name, photo, ID number)
- It's signed by your government (can't be faked)
- Anyone can verify it's real by checking the signature
- It proves who you are

**JWT does the same:**
- It contains user info (user_id, email, roles)
- It's signed by Auth0 (can't be faked)
- API Gateway can verify it's real by checking the signature
- It proves the user is authenticated

---

## Part 2: JWT Structure (3 Parts)

A JWT looks like this:
```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhdXRoMHx1c2VyMTIzIiwiZW1haWwiOiJhbGljZUB3b3JrLmNvbSIsIm5hbWUiOiJBbGljZSIsImh0dHBzOi8vbXlhcHAuZXhhbXBsZS5jb20vcm9sZXMiOlsiYWRtaW4iXSwiaWF0IjoxNjk2MDAwMDAwLCJleHAiOjE2OTYwODY0MDB9.signature_here_very_long_string
```

It has **3 parts** separated by dots (`.`):

### Part 1: HEADER
```json
{
  "alg": "RS256",    ← Signing algorithm (RSA - will explain later)
  "typ": "JWT",      ← Type of token
  "kid": "..."       ← Key ID (which Auth0 key was used?)
}
```
This is **Base64 encoded** (not encrypted, just encoded).

### Part 2: PAYLOAD
```json
{
  "sub": "auth0|alice123",                              ← User ID
  "email": "alice@work.com",                            ← Email
  "name": "Alice Smith",                                ← Name
  "https://myapp.example.com/roles": ["admin"],         ← ROLES! ← This is key!
  "iat": 1696000000,                                    ← Issued at (when created)
  "exp": 1696086400,                                    ← Expiration (24 hours later)
  "aud": "https://your-api-audience",                   ← Audience (who should accept this)
  "iss": "https://your-domain.auth0.com/"               ← Issuer (who created this)
}
```
This is also **Base64 encoded** (not encrypted).

**IMPORTANT:** Anyone can decode the payload and read the contents! JWT is NOT encrypted. It's just encoded.

### Part 3: SIGNATURE
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret_key_that_only_auth0_has
)
```

Result:
```
signature_very_long_random_looking_string_here
```

**This is the magic part!** This signature proves that:
1. The payload is from Auth0 (not someone else)
2. The payload hasn't been changed (tampered with)

---

## Part 3: JWT Generation - Step by Step

### Step 1: User Logs In

You go to Auth0 login page and enter:
```
Email: alice@work.com
Password: secretpassword123
```

### Step 2: Auth0 Verifies Credentials

Auth0's server checks:
```
SELECT user FROM users WHERE email='alice@work.com' AND password=hash(secretpassword123)
```

Result: ✓ User found! User ID = `auth0|alice123`

### Step 3: Auth0 Checks Role

Auth0's database:
```
auth0|alice123 → roles: ["admin"]  ← You assigned in Auth0 dashboard
```

### Step 4: Auth0 Creates PAYLOAD

Auth0 creates an object with user info:
```python
payload = {
    "sub": "auth0|alice123",                         # User ID
    "email": "alice@work.com",                       # Email
    "name": "Alice Smith",                           # Name
    "https://myapp.example.com/roles": ["admin"],    # ROLES (custom claim)
    "iat": 1696000000,                               # Now timestamp
    "exp": 1696086400,                               # 24 hours from now
    "aud": "https://your-api-audience",              # Should accept on your app
    "iss": "https://your-domain.auth0.com/"          # Created by Auth0
}
```

**How does Auth0 know to add "admin" role?**
→ You set it in Auth0 dashboard → User management → alice@work.com → Roles → Add "admin"

### Step 5: Auth0 Encodes HEADER

```python
header = {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "auth0_key_1"  # Which key? (Auth0 has multiple keys)
}

# Base64 encode
encoded_header = base64url_encode(json_stringify(header))
# Result: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9
```

### Step 6: Auth0 Encodes PAYLOAD

```python
encoded_payload = base64url_encode(json_stringify(payload))
# Result: eyJzdWIiOiJhdXRoMHx1c2VyMTIzIiwi...
```

### Step 7: Auth0 Creates SIGNATURE

```python
# Only Auth0 has this private key
auth0_private_key = "-----BEGIN RSA PRIVATE KEY-----\n..."

# Create signature
signature = RSASHA256(
    encoded_header + "." + encoded_payload,
    auth0_private_key
)

# Result: signature_very_long_string
```

**Why "RS256"?**
- **R** = RSA (asymmetric encryption algorithm)
- **S** = SHA (hashing algorithm)
- **256** = 256-bit strength

### Step 8: Auth0 Combines All Three

```python
jwt_token = encoded_header + "." + encoded_payload + "." + signature

# Result:
# eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWI...igibmFt....abcd1234
```

### Step 9: Auth0 Sends to Frontend

```javascript
// Auth0 returns to frontend
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWI...",
  "token_type": "Bearer",
  "expires_in": 86400  // 24 hours in seconds
}
```

---

## Part 4: Frontend Receives JWT

### Frontend Code
```javascript
// RAG_Frontend/src/context/AuthContext.jsx

const { getAccessTokenSilently } = useAuth0();

const token = await getAccessTokenSilently();
// Returns: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWI..."

// Store in memory (NOT localStorage for security)
// Send to backend
```

---

## Part 5: Frontend Sends JWT to API Gateway

### Frontend Request

```javascript
fetch('http://localhost:8000/api/me', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWI...'
    // Format: "Bearer {token}"
  }
})
```

**What is sent:**
```
GET /api/me HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWI...
```

---

## Part 6: API Gateway Receives JWT (THIS IS THE CRUCIAL PART)

### API Gateway File
```python
# api_gateway/auth.py

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
import jwt

# Setup
AUTH0_DOMAIN = "your-domain.auth0.com"
AUTH0_AUDIENCE = "https://your-api-audience"
ISSUER = f"https://{AUTH0_DOMAIN}/"

# Step 1: Create a security object that extracts the token from header
security = HTTPBearer()
# This automatically extracts the token from "Authorization: Bearer XXX"

# Step 2: Create a JWKS client
# JWKS = JSON Web Key Set (Auth0's public keys)
jwks_client = PyJWKClient(
    f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
)
# This URL is PUBLIC and anyone can access it
# It contains Auth0's PUBLIC KEYS for verifying signatures
```

### Decoding JWT - Full Function

```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    # Step 1: Extract token from "Bearer XXX"
    token = credentials.credentials
    # Extracts: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWI..."

    try:
        # Step 2: Get the SIGNING KEY from Auth0
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        # What this does:
        # 1. Looks at JWT header: kid = "auth0_key_1"
        # 2. Goes to Auth0's JWKS endpoint (public URL)
        # 3. Finds the public key with matching kid
        # 4. Downloads the public key
        
        # Example public key (simplified):
        # signing_key.key = "-----BEGIN PUBLIC KEY-----\n..."

        # Step 3: DECODE AND VERIFY JWT
        payload = jwt.decode(
            token,                          # The token
            signing_key.key,                # Auth0's PUBLIC key
            algorithms=["RS256"],           # Expect RS256 signature
            audience=AUTH0_AUDIENCE,        # Verify aud claim
            issuer=ISSUER,                  # Verify iss claim
        )
        # jwt.decode() does this:
        # 1. Split token into 3 parts
        # 2. Base64 decode header and payload
        # 3. Recreate the signature using the public key
        # 4. Compare: Does new signature == token's signature?
        #    YES → Token is valid ✓
        #    NO → Token is tampered ✗
        # 5. Check: Is expiration time passed?
        #    NO → Token is not expired ✓
        #    YES → Token is expired ✗
        # 6. Check: Is audience correct?
        #    Match → ✓
        #    No match → ✗
        # 7. Check: Is issuer Auth0?
        #    YES → ✓
        #    NO → ✗

        # Step 4: Save user to database
        upsert_user(payload)
        # This stores the user info in MySQL:
        # INSERT INTO users (auth0_user_id, email, name, role, ...)
        # VALUES ('auth0|alice123', 'alice@work.com', 'Alice', 'admin', ...)

        # Step 5: Return the decoded payload
        return payload
        # Returns:
        # {
        #   "sub": "auth0|alice123",
        #   "email": "alice@work.com",
        #   "name": "Alice Smith",
        #   "https://myapp.example.com/roles": ["admin"],
        #   "iat": 1696000000,
        #   "exp": 1696086400,
        #   "aud": "https://your-api-audience",
        #   "iss": "https://your-domain.auth0.com/"
        # }

    except jwt.PyJWTError as e:
        # If ANY validation fails:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
        # Frontend receives 401 Unauthorized → User not authenticated
```

---

## Part 7: What is `Depends(security)`?

### Understanding Depends()

`Depends()` is from FastAPI. It's a way to say:
**"Before running this function, first run this dependency and pass the result to me"**

### Understanding HTTPBearer()

```python
security = HTTPBearer()
```

This creates a function that:
1. Looks for `Authorization` header
2. Expects format: `Bearer {token}`
3. Extracts the token
4. Returns `HTTPAuthorizationCredentials` object containing the token

### Example

```python
# When FastAPI sees this:
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    ...

# FastAPI does this:
# 1. Call security() with the HTTP request
# 2. security() extracts the token from Authorization header
# 3. Returns HTTPAuthorizationCredentials(credentials='token_here')
# 4. Pass this to get_current_user() as the "credentials" parameter
```

**Real Request:**
```
GET /api/me
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**FastAPI processes it:**
```python
# Step 1: Depends(security) is called
credentials = security(request)
# credentials.credentials = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

# Step 2: Call the function with the result
current_user = get_current_user(credentials=credentials)
```

---

## Part 8: What is `Depends(current_user)`?

### Role Checking Function

```python
def require_admin(
    current_user=Depends(get_current_user)  # ← First run get_current_user()
):
    ROLES_CLAIM = "https://myapp.example.com/roles"
    
    # Extract roles from the payload
    roles = current_user.get(ROLES_CLAIM, [])
    # Example: ["admin"]
    
    # Check if "admin" is in roles
    if "admin" not in roles:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    return current_user
```

### How It's Used

```python
@router.get("/api/admin/overview")
async def get_overview(
    current_user=Depends(require_admin)  # ← Requires JWT + admin role
):
    return {"overview": "data"}
```

### Execution Flow

```
User sends request with JWT token
        │
        ▼
FastAPI sees: Depends(require_admin)
        │
        ▼
FastAPI calls: require_admin()
        │
        ▼
require_admin has: Depends(get_current_user)
        │
        ▼
FastAPI calls: get_current_user(credentials=...)
        │
        ├─ security() extracts token from Authorization header
        ├─ Fetches Auth0 public key
        ├─ Verifies JWT signature
        ├─ Checks expiration, audience, issuer
        ├─ Calls upsert_user(payload)
        │
        ▼ Returns payload
current_user = {
    "sub": "auth0|alice123",
    "email": "alice@work.com",
    "https://myapp.example.com/roles": ["admin"]
}
        │
        ▼
Back to require_admin():
        │
        ├─ Extract roles from current_user
        ├─ Check if "admin" in roles
        ├─ YES → Continue
        ├─ NO → Raise 403 Forbidden
        │
        ▼ Return current_user
        │
        ▼
Execute: get_overview(current_user=payload)
        │
        ▼
Return response
```

---

## Part 9: How API Gateway Knows if User or Admin

### Key 1: The Role Claim in JWT

When you set a user as admin in Auth0 dashboard:

**Auth0 Dashboard:**
```
Users → alice@work.com → Roles → Add Role → Select "admin"
```

This sets in Auth0's database:
```
auth0|alice123 → roles: ["admin"]
```

### Key 2: Custom Claim in JWT Payload

When JWT is created, Auth0 adds a custom claim (this is configured in your Auth0 app settings):

```json
{
  "sub": "auth0|alice123",
  "https://myapp.example.com/roles": ["admin"]  ← Custom claim with roles
}
```

### Key 3: Extracting Role

```python
# In require_admin()
ROLES_CLAIM = "https://myapp.example.com/roles"  # ← Custom claim key
roles = current_user.get(ROLES_CLAIM, [])        # ← Extract from JWT payload
# roles = ["admin"]

if "admin" not in roles:
    raise HTTPException(403, "Admin access required")
```

### Complete Example Flow

**Scenario 1: Alice (Admin)**
```
1. Alice logs in with alice@work.com
2. Auth0 checks: Does alice have "admin" role?
   YES → Auth0 adds to JWT: "https://myapp.example.com/roles": ["admin"]
3. Alice sends request with JWT to /api/admin/overview
4. API Gateway:
   - Decodes JWT
   - Extracts roles from payload: ["admin"]
   - Checks: "admin" in ["admin"]?
   - YES → Allow access ✓
5. Alice sees admin dashboard
```

**Scenario 2: Bob (Regular User)**
```
1. Bob logs in with bob@work.com
2. Auth0 checks: Does bob have "admin" role?
   NO → Auth0 adds to JWT: "https://myapp.example.com/roles": []  (or just user)
3. Bob sends request with JWT to /api/admin/overview
4. API Gateway:
   - Decodes JWT
   - Extracts roles from payload: []
   - Checks: "admin" in []?
   - NO → Raise 403 Forbidden ✗
5. Bob gets error: "Admin access required"
```

---

## Part 10: Complete Real-World Example

### Scenario: Admin Alice Wants to Upload Document

### Step 1: Auth0 Configuration
```
Auth0 Dashboard:
├─ Applications → Your App → Settings
│  ├─ Name: RAG Backend
│  └─ Custom Claim Name: https://myapp.example.com/roles
│
├─ Users → alice@work.com
│  └─ Roles → Add "admin" role
│
└─ Auth0 JWKS Endpoint: 
   https://your-domain.auth0.com/.well-known/jwks.json
```

### Step 2: Alice Logs In

**Frontend:**
```javascript
// RAG_Frontend/src/pages/Login/LoginPage.jsx
const handleLogin = () => {
  loginWithRedirect({ 
    appState: { returnTo: '/admin' }  // Try to go to admin
  });
};
```

**Auth0:**
- Alice enters credentials
- Auth0 verifies
- Auth0 checks: Does alice have admin role? YES
- Auth0 creates JWT with:
  ```json
  {
    "sub": "auth0|alice123",
    "email": "alice@work.com",
    "name": "Alice Smith",
    "https://myapp.example.com/roles": ["admin"],
    "exp": 1696086400
  }
  ```
- Auth0 signs with private key
- Auth0 sends to frontend

### Step 3: Frontend Stores JWT

```javascript
// RAG_Frontend/src/context/AuthContext.jsx
const token = await getAccessTokenSilently();
// token = "eyJhbGciOiJSUzI1NiI..."

// Frontend stores in memory
// Every API request includes it
```

### Step 4: Alice Uploads Document

**Frontend Code:**
```javascript
const uploadFile = async (file) => {
  const token = await getAccessTokenSilently();
  
  const response = await fetch('http://localhost:8000/api/admin/documents', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`  // JWT in header
    },
    body: formData  // File data
  });
};
```

**Request Sent:**
```
POST /api/admin/documents
Authorization: Bearer eyJhbGciOiJSUzI1NiI...
Content-Type: multipart/form-data

[file data]
```

### Step 5: API Gateway Receives Request

**Backend Code:**
```python
# api_gateway/routes/documents.py

@router.post("/api/admin/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(require_admin)  # ← TWO things happen:
):
    # ...
```

**What Depends(require_admin) does:**

```python
# Step 1: FastAPI calls require_admin()

# Step 2: require_admin has Depends(get_current_user)
# FastAPI calls get_current_user(credentials=...)

# Step 3: get_current_user() executes:
#   a) Depends(security) extracts token from header
#      token = "eyJhbGciOiJSUzI1NiI..."
#
#   b) jwks_client.get_signing_key_from_jwt(token)
#      → Fetches from: https://your-domain.auth0.com/.well-known/jwks.json
#      → Gets Auth0's public key
#      public_key = "-----BEGIN PUBLIC KEY-----\n..."
#
#   c) jwt.decode(token, public_key, ...)
#      → Verifies signature is valid
#      → Checks expiration: 1696086400 > now? YES ✓
#      → Checks audience: matches? YES ✓
#      → Checks issuer: is Auth0? YES ✓
#      → All checks pass ✓
#      → Returns decoded payload:
payload = {
    "sub": "auth0|alice123",
    "email": "alice@work.com",
    "name": "Alice Smith",
    "https://myapp.example.com/roles": ["admin"],
    "exp": 1696086400
}
#
#   d) upsert_user(payload)
#      → Saves/updates Alice in MySQL:
#      INSERT/UPDATE users SET
#        auth0_user_id='auth0|alice123',
#        email='alice@work.com',
#        name='Alice Smith',
#        role='admin',
#        last_login=NOW()
#
#   e) Returns payload

# Step 4: Back in require_admin()
current_user = payload  # {sub: ..., roles: ["admin"], ...}

# Step 5: require_admin checks role
ROLES_CLAIM = "https://myapp.example.com/roles"
roles = current_user.get(ROLES_CLAIM, [])
# roles = ["admin"]

if "admin" not in roles:
    raise HTTPException(403, "Admin access required")
    
# "admin" is in roles → Continue! ✓

# Step 6: require_admin returns payload
return current_user

# Step 7: upload_document() is called with:
# current_user = {sub: "auth0|alice123", ..., roles: ["admin"]}
```

### Step 6: Execute Endpoint

```python
@router.post("/api/admin/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(require_admin)  # ← Now we're here, all checks passed!
):
    # current_user is available:
    user_id = current_user["sub"]  # "auth0|alice123"
    user_role = current_user.get("https://myapp.example.com/roles")[0]  # "admin"
    
    # Process file upload...
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://127.0.0.1:8002/internal/documents",  # Document Service
            files={"file": file_content},
            headers={"X-Internal-Secret": INTERNAL_SERVICE_SECRET}
        )
    
    return {"document_id": response.json()["id"]}
```

### Step 7: Frontend Receives Response

```javascript
// Upload successful!
const data = await response.json();
console.log("Document uploaded:", data.document_id);
```

---

## Part 11: Visual Comparison - Admin vs Regular User

### Alice (Admin)

```
LOGIN:
Alice@auth0 → Auth0 checks → Has admin role? YES
                              └─ Add to JWT: roles: ["admin"]
                              
JWT PAYLOAD:
{
  "sub": "auth0|alice123",
  "email": "alice@work.com",
  "roles": ["admin"]  ← HERE
}

SIGNED BY: Auth0 private key

API GATEWAY VALIDATION:
1. Verify signature with Auth0 public key ✓
2. Check expiration ✓
3. Extract roles: ["admin"]
4. Check if "admin" in roles ✓
5. ALLOW ACCESS to /api/admin/*

RESULT: Alice can upload documents, see admin dashboard
```

### Bob (Regular User)

```
LOGIN:
bob@auth0 → Auth0 checks → Has admin role? NO
                           └─ Add to JWT: roles: [] (or just ["user"])

JWT PAYLOAD:
{
  "sub": "auth0|bob456",
  "email": "bob@work.com",
  "roles": []  ← NO ADMIN
}

SIGNED BY: Auth0 private key

API GATEWAY VALIDATION:
1. Verify signature with Auth0 public key ✓
2. Check expiration ✓
3. Extract roles: []
4. Check if "admin" in roles ✗ NOT FOUND
5. DENY ACCESS to /api/admin/*
   └─ Raise HTTPException(403, "Admin access required")

RESULT: Bob gets 403 Forbidden when trying to access /api/admin/*
        Bob CAN access /api/chat (regular user endpoints)
```

---

## Part 12: Summary Table

| Concept | What It Is | Who Creates It | How Verified |
|---------|-----------|-----------------|-------------|
| **JWT** | Signed token with user info | Auth0 | Signature checked with Auth0's public key |
| **Payload** | User data (name, email, roles) | Auth0 (from DB) | Decoded from JWT |
| **Signature** | Proof token is from Auth0 | Auth0 (using private key) | Verified using Auth0's public key |
| **RS256** | Signing algorithm (RSA + SHA256) | Standard algorithm | RSA asymmetric encryption |
| **Public Key** | Used to verify signatures | Auth0 (published publicly) | Fetched from JWKS endpoint |
| **Private Key** | Used to create signatures | Auth0 only | Secret, never shared |
| **Role Claim** | Custom field in JWT with roles | Auth0 (from user's roles) | Extracted and checked in require_admin() |
| **Depends()** | FastAPI dependency injection | FastAPI framework | Runs dependency before endpoint |
| **HTTPBearer()** | Extracts token from Authorization header | FastAPI security | Looks for "Bearer {token}" format |
| **get_current_user()** | Validates JWT, returns payload | Your backend | Calls jwt.decode() with public key |
| **require_admin()** | Checks if user has admin role | Your backend | Checks if "admin" in roles array |

---

## Part 13: Quick Reference - Code Flow

### User Login to Admin Access

```
┌─ Alice logs in (alice@work.com)
│  └─ Auth0 checks: admin role? YES
│     └─ Creates JWT with: roles: ["admin"]
│        └─ Signs with Auth0 private key
│
├─ Frontend receives JWT
│  └─ Stores in memory
│     └─ Sends with every request
│
├─ Alice clicks "Upload Document"
│  └─ Frontend sends: POST /api/admin/documents
│     └─ Headers: Authorization: Bearer {JWT}
│
├─ API Gateway receives request
│  └─ Depends(require_admin) is triggered
│     ├─ Depends(get_current_user)
│     │  ├─ Depends(security)
│     │  │  └─ Extracts token from Authorization header
│     │  │
│     │  ├─ jwks_client.get_signing_key_from_jwt()
│     │  │  └─ Fetches public key from Auth0
│     │  │
│     │  ├─ jwt.decode(token, public_key, ...)
│     │  │  ├─ Verifies signature
│     │  │  ├─ Checks expiration
│     │  │  ├─ Checks audience, issuer
│     │  │  └─ Returns: {sub: "...", roles: ["admin"]}
│     │  │
│     │  └─ upsert_user(payload)
│     │     └─ Saves Alice to MySQL
│     │
│     └─ Check: "admin" in roles?
│        ├─ YES → Continue ✓
│        └─ NO → Raise 403 Forbidden ✗
│
├─ upload_document(current_user=payload) executes
│  └─ Process file upload
│     └─ Call Document Service
│
└─ Return success response to Alice
   └─ File uploaded!
```

---

## Part 14: Key Takeaways

1. **JWT is not encrypted** - Anyone can read the payload. It's just encoded (Base64).
   - But the signature proves it's from Auth0 (can't be faked)

2. **Role is in the JWT payload** - Auth0 puts the role when creating the JWT
   - If you set alice as admin in Auth0, the JWT will contain: roles: ["admin"]

3. **API Gateway verifies, doesn't create** - Your backend doesn't create JWT
   - It only verifies it's real by checking the signature
   - Uses Auth0's public key (available at: https://your-domain.auth0.com/.well-known/jwks.json)

4. **Depends() is FastAPI dependency injection** - Tells FastAPI to run a function first
   - `Depends(security)` → Extract token from Authorization header
   - `Depends(get_current_user)` → Validate JWT and return payload
   - `Depends(require_admin)` → Also check if user is admin

5. **Role checking is simple** - Just check if "admin" is in the roles array
   - If yes → Allow access to admin endpoints
   - If no → Return 403 Forbidden

6. **Flow:** Login (Auth0) → Get JWT → Send to backend → Backend verifies → Extract role → Allow/Deny

This is the complete flow! Now you understand JWT, Auth0, roles, and how everything works together! 🎉

