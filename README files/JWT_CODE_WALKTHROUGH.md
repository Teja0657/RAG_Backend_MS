# JWT & Auth0 - Complete Code Walkthrough with Comments

## File 1: Auth0 Configuration (What Happens in Auth0 Dashboard)

```
Auth0 Dashboard → Applications → Your App → Settings

AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=client_id_here
AUTH0_CLIENT_SECRET=secret_here
AUTH0_AUDIENCE=https://your-api-audience

Custom Claims (Configure in Auth0):
└─ Rules → Add Rule → Add Custom Claim
   └─ namespace: https://myapp.example.com/roles
      └─ value: user.roles  (from user's roles in Auth0)

Role: admin is assigned in:
└─ Users → alice@work.com → Roles → Add "admin"
```

---

## File 2: Frontend - Login Page (React)

### File: `RAG_Frontend/src/pages/Login/LoginPage.jsx`

```javascript
import { useAuth0 } from '@auth0/auth0-react';  // Auth0 React SDK

const LoginPage = () => {
  // Get Auth0 functions
  const { loginWithRedirect } = useAuth0();

  // Step 1: User clicks login button
  const handleLogin = () => {
    // This sends user to Auth0's login page
    // Auth0 URL: https://your-domain.auth0.com/authorize?...
    loginWithRedirect({ 
      appState: { returnTo: '/chat' }  // Where to go after login
    });
  };

  return (
    <button onClick={handleLogin}>
      Login
    </button>
  );
};
```

**What happens:**
1. User clicks button
2. Redirects to: `https://your-domain.auth0.com/authorize?...`
3. Auth0 shows login form
4. User enters email: `alice@work.com`
5. User enters password: `secretpassword123`
6. Auth0 verifies in database
7. Auth0 checks: Does alice have admin role?
   - YES → Will add to JWT
8. Auth0 creates JWT with: `roles: ["admin"]`
9. Auth0 redirects back to frontend with JWT

---

## File 3: Frontend - Auth Context (Getting and Storing JWT)

### File: `RAG_Frontend/src/context/AuthContext.jsx`

```javascript
import { useAuth0 } from '@auth0/auth0-react';

export const AuthProvider = ({ children }) => {
  // Get Auth0 utilities
  const { 
    isAuthenticated,           // Is user logged in?
    user: auth0User,           // User info from Auth0
    getAccessTokenSilently,    // Function to get JWT token
  } = useAuth0();

  const [role, setRole] = useState(null);

  // Step 2: Frontend gets JWT from Auth0
  useEffect(() => {
    if (!isAuthenticated) return;  // User not logged in

    const loadRole = async () => {
      try {
        // GET JWT TOKEN FROM AUTH0
        const token = await getAccessTokenSilently();
        // token = "eyJhbGciOiJSUzI1NiI...hVk-xk_YWc"
        // This JWT was created by Auth0 and contains:
        // {
        //   "sub": "auth0|alice123",
        //   "email": "alice@work.com",
        //   "https://myapp.example.com/roles": ["admin"],
        //   "iat": 1696000000,
        //   "exp": 1696086400
        // }

        // Step 3: Send JWT to API Gateway to verify it
        const response = await fetch(
          'http://localhost:8000/api/me',  // API Gateway endpoint
          {
            headers: {
              // ADD JWT TO REQUEST HEADER
              // Format: "Bearer {token}"
              'Authorization': `Bearer ${token}`,
            },
          }
        );

        // Step 4: Get response from API Gateway
        const data = await response.json();
        // Response: {
        //   "user_id": "auth0|alice123",
        //   "claims": {
        //     "sub": "auth0|alice123",
        //     "email": "alice@work.com",
        //     "https://myapp.example.com/roles": ["admin"]
        //   }
        // }

        // Step 5: Extract role from response
        const roles = data.claims?.[ROLES_CLAIM] || [];
        // roles = ["admin"]

        setRole(roles.includes('admin') ? 'admin' : 'user');
        // If "admin" in roles → setRole('admin')
        // Otherwise → setRole('user')

      } catch (error) {
        console.error('Failed to get user role:', error);
        setRole(null);
      }
    };

    loadRole();
  }, [isAuthenticated, getAccessTokenSilently]);

  // Step 6: Return to component using this context
  return (
    <AuthContext.Provider
      value={{
        role,                      // 'admin' or 'user'
        isAdmin: role === 'admin', // true/false
        getAccessTokenSilently,    // Function to get JWT (used for all API calls)
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
```

**Key points:**
- `getAccessTokenSilently()` gets JWT from Auth0 (stored in browser)
- JWT is sent to API Gateway in `Authorization: Bearer` header
- API Gateway verifies JWT and returns user info
- Frontend extracts role and uses for routing

---

## File 4: Frontend - Chat Page (Using JWT for Every Request)

### File: `RAG_Frontend/src/pages/Chat/ChatPage.jsx`

```javascript
const ChatPage = () => {
  // Get Auth0 functions (including JWT getter)
  const { getAccessTokenSilently } = useAuth();

  // User sends a message
  const handleSendMessage = async () => {
    const userMessage = input;  // e.g., "What is AI?"

    try {
      // STEP 1: GET JWT TOKEN
      const token = await getAccessTokenSilently();
      // token = "eyJhbGciOiJSUzI1NiI...hVk-xk_YWc"

      // STEP 2: SEND MESSAGE TO API GATEWAY WITH JWT
      const response = await fetch(
        'http://localhost:8000/api/chat',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            // INCLUDE JWT IN AUTHORIZATION HEADER
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            question: userMessage,           // "What is AI?"
            conversation_id: activeChatId,   // null for new chat
          }),
        }
      );

      const data = await response.json();
      // Response: {
      //   "answer": "AI is Artificial Intelligence...",
      //   "conversation_id": 42
      // }

      // STEP 3: DISPLAY ANSWER
      setMessages([
        ...messages,
        { role: 'user', text: userMessage },
        { role: 'bot', text: data.answer }
      ]);

    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  return (
    <div>
      <input value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={handleSendMessage}>Send</button>
      {/* Display messages */}
    </div>
  );
};
```

**Every API call:**
1. Gets JWT from Auth0
2. Includes in Authorization header
3. Sends to API Gateway
4. API Gateway verifies and processes

---

## File 5: Backend - Auth Module (JWT Verification)

### File: `api_gateway/auth.py` - COMPLETE DETAILED VERSION

```python
import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
from dotenv import load_dotenv

load_dotenv()

# ===== CONFIGURATION (From environment variables) =====
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")      # "your-domain.auth0.com"
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")  # "https://your-api-audience"
ISSUER = f"https://{AUTH0_DOMAIN}/"           # "https://your-domain.auth0.com/"
ROLES_CLAIM = "https://myapp.example.com/roles"

# ===== SECURITY SETUP =====

# Step 1: Create HTTPBearer security object
# This object extracts token from "Authorization: Bearer {token}" header
security = HTTPBearer()

# Step 2: Create JWKS client
# JWKS = JSON Web Key Set (Auth0's public keys)
# This client fetches Auth0's public keys from the JWKS endpoint
jwks_client = PyJWKClient(
    f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    # Example: https://your-domain.auth0.com/.well-known/jwks.json
    # This URL is PUBLIC and contains Auth0's public keys
)

# ===== JWT VERIFICATION FUNCTION =====

def get_current_user(
    # Depends(security) tells FastAPI to:
    # 1. Call security() with the HTTP request
    # 2. security() extracts token from Authorization header
    # 3. Return HTTPAuthorizationCredentials object with token
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    This function validates JWT and returns decoded user info.
    
    Flow:
    1. Extract JWT from Authorization header
    2. Get Auth0's public key
    3. Verify JWT signature
    4. Check expiration, audience, issuer
    5. Return decoded payload (user info)
    """
    
    # STEP 1: EXTRACT TOKEN
    token = credentials.credentials
    # credentials = HTTPAuthorizationCredentials(
    #     scheme='Bearer',
    #     credentials='eyJhbGciOiJSUzI1NiI...hVk-xk_YWc'
    # )
    # token = 'eyJhbGciOiJSUzI1NiI...hVk-xk_YWc'

    try:
        # STEP 2: GET AUTH0'S PUBLIC SIGNING KEY
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        # This function:
        # 1. Looks at JWT header: kid = "auth0_key_1"
        # 2. Fetches from JWKS endpoint:
        #    https://your-domain.auth0.com/.well-known/jwks.json
        # 3. Finds public key with matching kid
        # 4. Returns public key object
        
        # signing_key.key = RSA public key
        # Example:
        # -----BEGIN PUBLIC KEY-----
        # MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA7e...
        # -----END PUBLIC KEY-----

        # STEP 3: DECODE AND VERIFY JWT
        payload = jwt.decode(
            # PARAMETER 1: The JWT token
            token,
            # Example: 'eyJhbGciOiJSUzI1NiI...hVk-xk_YWc'

            # PARAMETER 2: Auth0's PUBLIC key
            signing_key.key,
            # This is used to verify the signature
            # JWT.decode():
            # 1. Splits token into 3 parts: header.payload.signature
            # 2. Base64 decodes header and payload
            # 3. Recreates signature using public key:
            #    new_sig = RSASHA256(header.payload, public_key)
            # 4. Compares: new_sig == token.signature?
            #    YES → Token is valid (not tampered)
            #    NO → Token was changed (reject)

            # PARAMETER 3: Expected algorithms
            algorithms=["RS256"],
            # JWT header must have: "alg": "RS256"
            # RS256 = RSA + SHA256
            # We only accept this algorithm (secure against algorithm confusion attacks)

            # PARAMETER 4: Expected audience
            audience=AUTH0_AUDIENCE,
            # JWT payload must have: "aud": "https://your-api-audience"
            # This verifies the JWT is for OUR API, not someone else's
            # Example:
            # JWT has: "aud": "https://your-api-audience" → Match ✓
            # JWT has: "aud": "https://other-api" → No match ✗ (reject)

            # PARAMETER 5: Expected issuer
            issuer=ISSUER,
            # JWT payload must have: "iss": "https://your-domain.auth0.com/"
            # This verifies the JWT is from Auth0, not a fake
            # Example:
            # JWT has: "iss": "https://your-domain.auth0.com/" → Match ✓
            # JWT has: "iss": "https://fake-auth.com/" → No match ✗ (reject)
        )
        # If jwt.decode() doesn't raise exception, JWT is valid!
        # Returns decoded payload:
        # payload = {
        #     "sub": "auth0|alice123",
        #     "email": "alice@work.com",
        #     "name": "Alice Smith",
        #     "https://myapp.example.com/roles": ["admin"],
        #     "iat": 1696000000,     # issued at
        #     "exp": 1696086400,     # expiration time
        #     "aud": "https://your-api-audience",
        #     "iss": "https://your-domain.auth0.com/"
        # }

        # STEP 4: SAVE USER TO DATABASE (will cover in separate file)
        upsert_user(payload)
        # Creates or updates user in MySQL:
        # INSERT INTO users (auth0_user_id, email, name, role, ...)
        # VALUES ('auth0|alice123', 'alice@work.com', 'Alice', 'admin', ...)

        # STEP 5: RETURN DECODED PAYLOAD
        return payload
        # This payload will be available in endpoint via Depends()
        # Example:
        # @app.get("/api/me")
        # def get_me(current_user=Depends(get_current_user)):
        #     # current_user = payload (the decoded JWT)
        #     return current_user

    except jwt.ExpiredSignatureError:
        # JWT has expired (exp time passed)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidAudienceError:
        # JWT audience doesn't match
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience"
        )
    except jwt.InvalidIssuerError:
        # JWT issuer is not Auth0
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer"
        )
    except jwt.PyJWTError as e:
        # Any other JWT error (tampered token, invalid signature, etc.)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# ===== ROLE CHECKING FUNCTION =====

def require_admin(
    # First run get_current_user() to get payload
    current_user=Depends(get_current_user)
):
    """
    This function checks if user is admin.
    
    Flow:
    1. Get current_user (from get_current_user)
    2. Extract roles from JWT payload
    3. Check if "admin" is in roles
    4. If yes → Allow
    5. If no → Deny with 403
    """
    
    # STEP 1: EXTRACT ROLES FROM JWT PAYLOAD
    roles = current_user.get(ROLES_CLAIM, [])
    # current_user is the payload from get_current_user
    # Example payload:
    # {
    #   "sub": "auth0|alice123",
    #   "email": "alice@work.com",
    #   "https://myapp.example.com/roles": ["admin"]  ← This line
    # }
    
    # roles = ["admin"]  (for admin user)
    # roles = []         (for regular user)

    # STEP 2: CHECK IF ADMIN
    if "admin" not in roles:
        # User doesn't have admin role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    # If we reach here, user is admin ✓

    # STEP 3: RETURN PAYLOAD (allow endpoint to use it)
    return current_user
```

---

## File 6: Backend - API Gateway Endpoints

### File: `api_gateway/main.py`

```python
from fastapi import FastAPI, Depends
from api_gateway.auth import get_current_user, require_admin

app = FastAPI()

# ===== PUBLIC ENDPOINTS =====

@app.get("/api/me")
def get_me(
    # Depends(get_current_user) means:
    # 1. Extract JWT from Authorization header
    # 2. Verify JWT with Auth0's public key
    # 3. Return decoded payload
    # 4. If invalid → Return 401 Unauthorized
    current_user=Depends(get_current_user)
):
    """
    Returns current user's info from JWT payload.
    
    Flow:
    1. Client sends: GET /api/me Authorization: Bearer {JWT}
    2. FastAPI calls: get_current_user(credentials=...)
       - Extracts token from Authorization header
       - Fetches Auth0's public key
       - Verifies JWT
       - Returns decoded payload
    3. execute get_me(current_user=payload)
    4. Return payload to client
    """
    return {
        "user_id": current_user["sub"],  # "auth0|alice123"
        "claims": current_user,
    }


# ===== PROTECTED ENDPOINTS (Any logged-in user) =====

@app.post("/api/chat")
async def chat(
    request: ChatRequest,  # {question, conversation_id}
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),  # Any logged-in user
):
    """
    Sends message to RAG service.
    
    Requirements: User must be logged in (have valid JWT)
    """
    user_id = current_user["sub"]  # Get user_id from JWT
    
    # ... rest of function


# ===== ADMIN ENDPOINTS (Only admin users) =====

@app.get("/api/admin/overview")
async def get_overview(
    current_user=Depends(require_admin)  # ADMIN ONLY!
    # Depends(require_admin) means:
    # 1. Call get_current_user() to get payload
    # 2. Check if "admin" in roles
    # 3. If YES → Continue
    # 4. If NO → Return 403 Forbidden
):
    """
    Returns admin dashboard overview.
    
    Requirements: User must be admin
    
    Flow:
    1. Client sends: GET /api/admin/overview Authorization: Bearer {JWT}
    2. FastAPI sees: Depends(require_admin)
    3. FastAPI calls: require_admin()
    4. require_admin calls: get_current_user()
       - Verifies JWT
       - Returns payload
    5. require_admin checks: "admin" in roles?
       - YES → Return payload
       - NO → Raise 403 Forbidden
    6. Execute get_overview(current_user=payload)
    7. Return response
    """
    return {"overview": "data"}


@app.post("/api/admin/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(require_admin)  # ADMIN ONLY!
):
    """
    Uploads document (admin only).
    
    Requirements: User must be admin
    """
    user_id = current_user["sub"]
    # ... rest of function
```

---

## File 7: Backend - User Service (Saving to Database)

### File: `api_gateway/user_service.py`

```python
from datetime import datetime, timezone
from api_gateway.database import SessionLocal
from api_gateway.models import User

def upsert_user(user_data: dict):
    """
    Create or update user in MySQL database.
    
    Called by get_current_user() after JWT is verified.
    """
    
    # STEP 1: EXTRACT INFO FROM JWT PAYLOAD
    auth0_user_id = user_data.get("sub")
    # Example: "auth0|alice123"
    
    email = user_data.get("https://myapp.example.com/email")
    # Example: "alice@work.com"
    
    name = user_data.get("https://myapp.example.com/name")
    # Example: "Alice Smith"
    
    roles = user_data.get("https://myapp.example.com/roles", [])
    # Example: ["admin"]
    
    # Convert to simple "admin" or "user" role
    role = "admin" if "admin" in roles else "user"
    # role = "admin"

    # STEP 2: CONNECT TO DATABASE
    db = SessionLocal()  # MySQL connection
    # SessionLocal() creates SQLAlchemy session

    try:
        # STEP 3: CHECK IF USER EXISTS
        user = db.scalar(
            select(User).where(
                User.auth0_user_id == auth0_user_id
            )
        )
        # This SQL:
        # SELECT * FROM users WHERE auth0_user_id = 'auth0|alice123'
        
        # user = User object if found, None if not found

        if user is None:
            # STEP 4A: CREATE NEW USER
            user = User(
                auth0_user_id=auth0_user_id,
                email=email or "",
                name=name,
                role=role,
                created_at=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc),
            )
            db.add(user)  # Mark for insertion
            # This generates SQL:
            # INSERT INTO users (auth0_user_id, email, name, role, created_at, last_login)
            # VALUES ('auth0|alice123', 'alice@work.com', 'Alice Smith', 'admin', NOW(), NOW())

        else:
            # STEP 4B: UPDATE EXISTING USER
            user.email = email or user.email
            user.name = name
            user.role = role
            user.last_login = datetime.now(timezone.utc)
            # This generates SQL:
            # UPDATE users SET email=?, name=?, role=?, last_login=NOW()
            # WHERE auth0_user_id=?

        # STEP 5: COMMIT TO DATABASE
        db.commit()
        # Saves the changes to MySQL

    finally:
        db.close()  # Close database connection
```

---

## File 8: Complete Request Flow Diagram (Code Level)

```
REQUEST COMES IN:
┌─ GET /api/admin/overview
├─ Authorization: Bearer eyJhbGciOiJSUzI1NiI...hVk-xk_YWc
└─ Host: localhost:8000

│
▼ FastAPI receives request
│
├─ Looks at endpoint:
│  @app.get("/api/admin/overview")
│  def get_overview(current_user=Depends(require_admin)):
│
│  Sees: Depends(require_admin)
│
├─ FastAPI calls: require_admin()
│
│  In require_admin():
│  ├─ Has: Depends(get_current_user)
│  │  FastAPI calls: get_current_user(credentials=?)
│  │
│  │  In get_current_user():
│  │  ├─ Has: Depends(security)
│  │  │  FastAPI calls: security(request)
│  │  │  
│  │  │  HTTPBearer.security():
│  │  │  ├─ Looks at request headers
│  │  │  ├─ Finds: Authorization: Bearer ...
│  │  │  ├─ Extracts: eyJhbGciOiJSUzI1NiI...hVk-xk_YWc
│  │  │  └─ Returns: HTTPAuthorizationCredentials(credentials='eyJh...')
│  │  │
│  │  │  ← Returns to get_current_user
│  │  │
│  │  ├─ credentials.credentials = 'eyJhbGciOiJSUzI1NiI...hVk-xk_YWc'
│  │  │
│  │  ├─ token = 'eyJhbGciOiJSUzI1NiI...hVk-xk_YWc'
│  │  │
│  │  ├─ signing_key = jwks_client.get_signing_key_from_jwt(token)
│  │  │  ├─ HTTP GET https://your-domain.auth0.com/.well-known/jwks.json
│  │  │  ├─ Parse response (JSON array of keys)
│  │  │  ├─ Find key with kid matching JWT header
│  │  │  └─ Return public key
│  │  │
│  │  ├─ payload = jwt.decode(token, signing_key.key, ...)
│  │  │  ├─ Split: header.payload.signature
│  │  │  ├─ Base64 decode header and payload
│  │  │  ├─ Recreate signature:
│  │  │  │  new_sig = RSASHA256(header.payload, public_key)
│  │  │  ├─ Compare: new_sig == signature?
│  │  │  │  ├─ YES → Token valid ✓
│  │  │  │  └─ NO → Raise PyJWTError ✗
│  │  │  ├─ Check: exp > now?
│  │  │  │  ├─ YES → Not expired ✓
│  │  │  │  └─ NO → Raise ExpiredSignatureError ✗
│  │  │  ├─ Check: aud == expected?
│  │  │  │  ├─ YES → Audience match ✓
│  │  │  │  └─ NO → Raise InvalidAudienceError ✗
│  │  │  ├─ Check: iss == expected?
│  │  │  │  ├─ YES → Issuer match ✓
│  │  │  │  └─ NO → Raise InvalidIssuerError ✗
│  │  │  └─ Return: {sub: "...", email: "...", roles: ["admin"]}
│  │  │
│  │  ├─ upsert_user(payload)
│  │  │  ├─ Extract: auth0_user_id, email, name, roles
│  │  │  ├─ Query DB: SELECT * FROM users WHERE auth0_user_id = ?
│  │  │  ├─ If not found: INSERT new user
│  │  │  ├─ If found: UPDATE user
│  │  │  └─ COMMIT to database
│  │  │
│  │  └─ return payload
│  │  └─ Returns: {sub: "auth0|alice123", email: "alice@work.com", roles: ["admin"]}
│  │
│  │  ← Returns to require_admin
│  │
│  ├─ current_user = {sub: "...", email: "...", roles: ["admin"]}
│  │
│  ├─ roles = current_user.get("https://myapp.example.com/roles", [])
│  │  └─ roles = ["admin"]
│  │
│  ├─ if "admin" not in roles:
│  │  └─ "admin" is in ["admin"] → Condition is FALSE
│  │  └─ Don't raise HTTPException
│  │
│  └─ return current_user
│  └─ Returns: {sub: "auth0|alice123", email: "...", roles: ["admin"]}
│
│  ← Returns to get_overview
│
├─ current_user = {sub: "auth0|alice123", email: "...", roles: ["admin"]}
│
├─ Execute endpoint body:
│  return {"overview": "data"}
│
└─ Send response:
   HTTP 200 OK
   Content-Type: application/json
   {"overview": "data"}
```

---

## Summary of Code Execution Order

1. **Browser sends request** with JWT in Authorization header
2. **FastAPI receives request** and sees `Depends(require_admin)`
3. **FastAPI calls security()** → Extracts token from header
4. **FastAPI calls get_current_user()** → Validates JWT
   - Fetches Auth0's public key
   - Verifies signature
   - Checks expiration, audience, issuer
   - Returns decoded payload
5. **FastAPI calls require_admin()** → Checks role
   - Extracts roles from payload
   - Checks if "admin" in roles
   - Returns payload or raises 403
6. **Endpoint executes** with verified current_user
7. **Response sent** to browser

All of this happens in milliseconds! 🚀

