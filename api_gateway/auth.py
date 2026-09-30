import os
import ssl

import certifi
import jwt

from api_gateway.user_service import upsert_user
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
from dotenv import load_dotenv

load_dotenv()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")

ISSUER = f"https://{AUTH0_DOMAIN}/"

ROLES_CALIM= "https://myapp.example.com/roles"

security = HTTPBearer()

# python-certifi-win32 merges the corporate proxy's SSL-inspection root CA into
# certifi's bundle; ssl.load_default_certs() doesn't pick it up the same way,
# so point urllib at the certifi bundle explicitly instead.
_ssl_context = ssl.create_default_context(cafile=certifi.where())

jwks_client = PyJWKClient(
    f"https://{AUTH0_DOMAIN}/.well-known/jwks.json",
    ssl_context=_ssl_context,
)



def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=ISSUER,
            # Small tolerance for normal clock skew between Auth0's servers and
            # this one; PyJWT's default leeway is 0, which is stricter than
            # real-world network/processing latency allows for.
            leeway=10,
        )
        upsert_user(payload)
        
        return payload

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
def require_admin(
        current_user=Depends(get_current_user)
):
    roles= current_user.get(ROLES_CALIM, [])

    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
