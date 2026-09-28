import os
import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from api_gateway.auth import require_admin
from api_gateway.internal_client import INTERNAL_AUTH_HEADERS

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
)


class TestChatRequest(BaseModel):
    question: str

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
            headers=INTERNAL_AUTH_HEADERS,
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
            headers=INTERNAL_AUTH_HEADERS,
            timeout=10,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )


@router.get("/stats")
async def get_stats(current_user=Depends(require_admin)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ADMIN_SERVICE_URL}/internal/stats",
            headers=INTERNAL_AUTH_HEADERS,
            timeout=15,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )


@router.post("/evaluation/run")
async def run_evaluation(current_user=Depends(require_admin)):
    # Runs the full 35-question LangSmith dataset through the RAG pipeline
    # and the LLM-judge evaluators — realistically 1-3 minutes, so this
    # stays synchronous rather than adding job-tracking infrastructure.
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ADMIN_SERVICE_URL}/internal/evaluation/run",
            headers=INTERNAL_AUTH_HEADERS,
            timeout=None,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )


@router.post("/test-chat")
async def test_chat(
    request: TestChatRequest,
    current_user=Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ADMIN_SERVICE_URL}/internal/test-chat",
            json={"question": request.question},
            headers=INTERNAL_AUTH_HEADERS,
            timeout=None,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )