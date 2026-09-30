# JWT & Auth0 - Quick Summary (5-Minute Read)

## What is JWT?

**JWT = A secure identity card**

Like your driver's license - it proves who you are and nobody can fake it.

Example:
```
eyJhbGciOiJSUzI1NiI...  .  eyJzdWIiOiJhbGljZSI...  .  signature_here
    ↑ Header              ↑ Payload (user info)     ↑ Proof it's real
```

---

## 3 Parts of JWT

### 1. HEADER (Who am I from?)
```json
{
  "alg": "RS256",     // RS256 = RSA + SHA256 (signing method)
  "typ": "JWT"        // It's a JWT
}
```
**Base64 encoded** (readable, not encrypted)

### 2. PAYLOAD (My info)
```json
{
  "sub": "auth0|alice123",                      // User ID
  "email": "alice@work.com",                    // Email
  "https://myapp.example.com/roles": ["admin"]  // ROLE (THIS IS KEY!)
}
```
**Base64 encoded** (readable, not encrypted)

### 3. SIGNATURE (Proof it's real)
```
RSASHA256(header.payload, AUTH0_PRIVATE_KEY_ONLY_AUTH0_HAS)
= abcd1234efgh5678ijkl9012mnop3456...
```
**Not encoded, actual cryptographic signature**

This proves:
- ✓ It came from Auth0 (only they have the private key)
- ✓ Nobody changed the data (signature would break if changed)

---

## How JWT is Generated (Simple Steps)

1. **User logs in** → Auth0 verifies credentials
2. **Auth0 checks role** → Database: alice → role: "admin"
3. **Auth0 creates payload** with user info + role
4. **Auth0 signs it** with their private key (RSA algorithm)
5. **Auth0 sends JWT to frontend**
6. **Frontend stores JWT** in memory

---

## How Auth0 Signs JWT (Using Private/Public Key Pair)

### Auth0's Two Keys

1. **Private Key** (Secret, only Auth0 has)
   ```
   -----BEGIN RSA PRIVATE KEY-----
   MIIEpAIBAAKCAQEA7e...
   [very long key]
   -----END RSA PRIVATE KEY-----
   ```
   Used to: **SIGN** the JWT (create signature)

2. **Public Key** (Available to everyone)
   ```
   -----BEGIN PUBLIC KEY-----
   MIIBIjANBgkqhkiG9w0B...
   [very long key]
   -----END PUBLIC KEY-----
   ```
   Used to: **VERIFY** the JWT signature

### Signing Process (What Auth0 Does)

```python
# Auth0 has the payload
payload = {"sub": "alice123", "roles": ["admin"]}

# Auth0 uses their PRIVATE key to create a signature
signature = RSASHA256(
    base64(header) + "." + base64(payload),
    auth0_private_key  # Only Auth0 has this!
)

# Auth0 combines all 3 parts
jwt_token = header + "." + payload + "." + signature

# Send to frontend
return jwt_token
```

**Why use RSA (Asymmetric)?**
- Auth0 can sign with private key
- Your backend can verify with public key
- Your backend never needs the private key
- Public key can be shared openly

---

## Frontend Gets and Uses JWT

```javascript
// Step 1: Get JWT from Auth0
const token = await getAccessTokenSilently();
// token = "eyJhbGciOiJSUzI1NiI...hVk-xk_YWc"

// Step 2: Send JWT to backend with every request
fetch('http://localhost:8000/api/admin/documents', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`  // JWT here!
  }
})
```

---

## API Gateway Receives and Verifies JWT

### Step-by-Step Verification

```python
# api_gateway/auth.py

from fastapi.security import HTTPBearer
from jwt import PyJWKClient
import jwt

# Setup
security = HTTPBearer()  # Extracts token from "Authorization: Bearer XXX"
jwks_client = PyJWKClient(
    "https://your-domain.auth0.com/.well-known/jwks.json"  # Auth0's public keys
)

def get_current_user(credentials = Depends(security)):
    # Step 1: Extract token
    token = credentials.credentials
    # = "eyJhbGciOiJSUzI1NiI...hVk-xk_YWc"
    
    # Step 2: Get Auth0's PUBLIC key
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    # Fetches from: https://your-domain.auth0.com/.well-known/jwks.json
    # Returns: Auth0's public key
    
    # Step 3: Verify JWT
    payload = jwt.decode(
        token,
        signing_key.key,           # Auth0's PUBLIC key
        algorithms=["RS256"],
        audience="your-api",       # Verify it's for YOUR API
        issuer="https://auth0.com" # Verify it's from Auth0
    )
    # This function:
    # ├─ Splits token into 3 parts
    # ├─ Base64 decodes header and payload
    # ├─ Recreates signature using public key
    # ├─ Compares: new_sig == token_sig?
    # │  ├─ YES → Token is valid ✓
    # │  └─ NO → Token was tampered ✗
    # ├─ Checks: Is token expired?
    # │  └─ If expired → Reject
    # ├─ Checks: Is audience correct?
    # │  └─ If wrong → Reject
    # └─ Checks: Is issuer Auth0?
    #    └─ If wrong → Reject
    
    # Step 4: If all checks pass, return decoded payload
    return payload
    # = {
    #     "sub": "auth0|alice123",
    #     "email": "alice@work.com",
    #     "https://myapp.example.com/roles": ["admin"]
    #   }
```

**Key Point:** Your backend VERIFIES but doesn't CREATE JWT
- Verification uses Auth0's PUBLIC key (available to everyone)
- Creation uses Auth0's PRIVATE key (only Auth0 has)

---

## What is `Depends()`? (FastAPI Feature)

`Depends()` means: **"Run this function first, then pass its result to me"**

```python
# FastAPI sees this:
@app.get("/api/admin")
def admin_endpoint(
    current_user=Depends(require_admin)
):
    ...

# FastAPI does this:
# 1. Call require_admin()
# 2. require_admin has Depends(get_current_user)
# 3. Call get_current_user()
# 4. Pass result to admin_endpoint()
# 5. Execute admin_endpoint()
```

### Dependency Chain

```
admin_endpoint()
  └─ Depends(require_admin)
      └─ Depends(get_current_user)
          └─ Depends(security)
              └─ Extracts token from Authorization header
```

Execution order:
1. security() → Extract token
2. get_current_user() → Verify JWT
3. require_admin() → Check role
4. admin_endpoint() → Do work

---

## What is HTTPBearer()? (FastAPI Feature)

```python
security = HTTPBearer()
```

This function:
1. Looks at HTTP headers
2. Finds: `Authorization: Bearer {token}`
3. Extracts: `{token}`
4. Returns: Object with the token

**Example:**

```
HTTP Request:
  Authorization: Bearer eyJhbGciOiJSUzI1NiI...

HTTPBearer does:
  Extracts: "eyJhbGciOiJSUzI1NiI..."
  Returns: HTTPAuthorizationCredentials(credentials="eyJhbGc...")
```

---

## How Does It Know User vs Admin?

### The Role Claim

In Auth0 Dashboard, you set:
```
User: alice@work.com
Role: admin
```

This goes into JWT as custom claim:
```json
{
  "sub": "auth0|alice123",
  "https://myapp.example.com/roles": ["admin"]  ← The role!
}
```

### Checking Role

```python
def require_admin(current_user=Depends(get_current_user)):
    # Extract roles from payload
    roles = current_user.get("https://myapp.example.com/roles", [])
    # roles = ["admin"]
    
    # Check if admin
    if "admin" not in roles:
        raise HTTPException(403, "Admin access required")
    
    return current_user
```

### Usage

```python
# This endpoint needs JWT + admin role
@app.post("/api/admin/documents")
async def upload_document(
    current_user=Depends(require_admin)  # ← Requires admin!
):
    return {"status": "uploaded"}

# This endpoint needs only JWT
@app.post("/api/chat")
async def chat(
    current_user=Depends(get_current_user)  # ← Any logged-in user
):
    return {"status": "ok"}
```

---

## Real-World Example: Alice Uploads Document

### Step 1: Alice's Role (Auth0 Dashboard)
```
Users → alice@work.com → Roles → Add "admin"
```

### Step 2: Alice Logs In
```
1. Alice enters email/password
2. Auth0 verifies credentials ✓
3. Auth0 checks: alice has admin role? YES
4. Auth0 creates JWT with: roles: ["admin"]
5. Auth0 signs with private key
6. Sends to frontend
```

### Step 3: JWT Created by Auth0
```json
Header:
{
  "alg": "RS256",
  "kid": "auth0_key_1"
}

Payload:
{
  "sub": "auth0|alice123",
  "email": "alice@work.com",
  "name": "Alice Smith",
  "https://myapp.example.com/roles": ["admin"],
  "iat": 1696000000,
  "exp": 1696086400  // 24 hours later
}

Signature:
abcd1234efgh5678ijkl9012mnop3456...
(Created using Auth0's private key)

Complete JWT:
eyJhbGciOiJSUzI1NiIsImtpZCI6ImF1dGgwX2tleV8xIn0.
eyJzdWIiOiJhdXRoMHxhbGljZTEyMyIsImVtYWlsIjoiYWxpY2VAd29yay5jb20iLCJodHRwczovL215YXBwLmV4YW1wbGUuY29tL3JvbGVzIjpbImFkbWluIl0sImlhdCI6MTY5NjAwMDAwMCwiZXhwIjoxNjk2MDg2NDAwfQ.
abcd1234efgh5678ijkl9012mnop3456...
```

### Step 4: Frontend Gets JWT
```javascript
const token = await getAccessTokenSilently();
// token = "eyJhbGciOi..."
```

### Step 5: Alice Clicks "Upload Document"
```javascript
fetch('http://localhost:8000/api/admin/documents', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${token}`  // JWT sent here!
  }
})
```

### Step 6: API Gateway Receives
```python
@app.post("/api/admin/documents")
async def upload(current_user=Depends(require_admin)):
    # Depends(require_admin) triggers:
    # 1. Extract token from Authorization header
    # 2. Fetch Auth0's public key from .well-known/jwks.json
    # 3. Verify signature with public key
    # 4. Check expiration: exp=1696086400 > now? YES ✓
    # 5. Check audience: matches? YES ✓
    # 6. Check issuer: is Auth0? YES ✓
    # 7. Decode payload:
    #    {
    #      "sub": "auth0|alice123",
    #      "roles": ["admin"]
    #    }
    # 8. Check if "admin" in roles: YES ✓
    # 9. Save Alice to MySQL
    # 10. Pass current_user to endpoint
    
    # current_user is available here!
    user_id = current_user["sub"]  # "auth0|alice123"
    role = current_user["https://myapp.example.com/roles"][0]  # "admin"
    
    # Upload document...
    return {"document_id": 123}
```

### Step 7: Frontend Receives Response
```javascript
{
  "document_id": 123
}
// Upload successful!
```

---

## If Bob (Regular User) Tries

```
1. Bob logs in
2. Auth0: Does bob have admin role? NO
3. JWT created: roles: [] (empty or ["user"])
4. Bob sends request to /api/admin/documents
5. API Gateway:
   - Validates JWT ✓
   - Extracts roles: []
   - Checks: "admin" in []? NO ✗
   - Raises HTTPException(403, "Admin access required")
6. Frontend receives: 403 Forbidden
```

---

## Complete Comparison Table

| Item | What It Is | Who Has It | For What |
|------|-----------|-----------|----------|
| **JWT** | Signed token | Auth0 creates, user receives | Proves identity |
| **Private Key** | Secret key | Auth0 only | SIGN JWT (create signature) |
| **Public Key** | Open key | Everyone | VERIFY JWT (check signature) |
| **Payload** | User info | In JWT (readable) | Contains user data + role |
| **RS256** | Algorithm | Standard | RSA + SHA256 signature method |
| **Role Claim** | Custom field | In JWT | Specifies user role (admin/user) |
| **Depends()** | FastAPI feature | Framework | Run function before endpoint |
| **HTTPBearer()** | FastAPI feature | Framework | Extract token from header |
| **get_current_user()** | Your function | Your code | Validate JWT + extract payload |
| **require_admin()** | Your function | Your code | Check if user is admin |

---

## Key Rules to Remember

1. **JWT has 3 parts:** header.payload.signature
   - Header = algorithm info
   - Payload = user data (READABLE!)
   - Signature = proof of authenticity

2. **JWT is NOT encrypted** - anyone can read payload
   - But signature proves it's from Auth0
   - And signature can't be faked (need private key)

3. **Auth0 creates JWT** - your backend only verifies it
   - Creation: Auth0 private key (signing)
   - Verification: Auth0 public key (checking)

4. **Role is in the JWT** - Auth0 puts it when creating
   - If user has admin role in Auth0 → JWT has roles: ["admin"]
   - If user has no special role → JWT has roles: []

5. **API Gateway checks role** - just looks at the array
   - if "admin" in roles → Allow
   - else → Deny with 403

6. **Depends() is a chain** - runs dependencies first
   - First: Extract token
   - Second: Validate JWT
   - Third: Check role
   - Finally: Execute endpoint

---

## Final Answer Summary

| Question | Answer |
|----------|--------|
| **What is JWT?** | A signed token proving user identity |
| **Who creates JWT?** | Auth0 (not your backend) |
| **What does Auth0 use?** | RSA private key to SIGN, public key to VERIFY |
| **What is JWT made of?** | Header.Payload.Signature |
| **Is JWT encrypted?** | NO - it's readable but signed |
| **How does it verify?** | Compare signature using Auth0's public key |
| **Where is role stored?** | In JWT payload under custom claim |
| **How does API check role?** | Extracts claim, checks if "admin" in array |
| **What is Depends()?** | FastAPI runs dependency before endpoint |
| **What is HTTPBearer()?** | Extracts token from Authorization header |
| **User vs Admin?** | Checked by comparing roles array in payload |
| **Can JWT be faked?** | NO - would need Auth0's private key |

---

Now you understand the complete JWT flow! 🎉

