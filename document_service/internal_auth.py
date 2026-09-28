import os

from fastapi import Header, HTTPException

INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET")


def verify_internal_secret(x_internal_secret: str = Header(default="")):
    if not INTERNAL_SERVICE_SECRET or x_internal_secret != INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=401, detail="Invalid internal service credentials")
