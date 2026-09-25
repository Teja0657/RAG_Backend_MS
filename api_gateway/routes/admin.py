import os
import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from api_gateway.auth import require_admin

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
)

ADMIN_SERVICE_URL = os.getenv(
    "ADMIN_SERVICE_URL",
    "http://127.0.0.1:8003",
)


@router.get("/overview")
async def get_overview(
    current_user=Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ADMIN_SERVICE_URL}/internal/overview",
            timeout=10,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )

@router.get("/users")
async def get_users(current_user=Depends(require_admin)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ADMIN_SERVICE_URL}/internal/users",
            timeout=10,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )