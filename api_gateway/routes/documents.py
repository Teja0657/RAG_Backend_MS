import os

import httpx
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse

from api_gateway.auth import require_admin


router = APIRouter(
    prefix="/api/admin",
    tags=["admin-documents"],
)

DOCUMENT_SERVICE_URL = os.getenv(
    "DOCUMENT_SERVICE_URL",
    "http://127.0.0.1:8002",
)


# ==========================================================
# UPLOAD DOCUMENT
# ==========================================================

@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
):
    file_content = await file.read()

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
            timeout=None,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )


# ==========================================================
# LIST DOCUMENTS
# ==========================================================

@router.get("/documents")
async def list_documents(
    current_user=Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DOCUMENT_SERVICE_URL}/internal/documents",
            timeout=None,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )


# ==========================================================
# UPDATE DOCUMENT
# ==========================================================

@router.put("/documents/{document_id}")
async def update_document(
    document_id: str,
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
):
    file_content = await file.read()

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{DOCUMENT_SERVICE_URL}/internal/documents/{document_id}",
            files={
                "file": (
                    file.filename,
                    file_content,
                    file.content_type,
                )
            },
            timeout=None,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )


# ==========================================================
# DELETE DOCUMENT
# ==========================================================

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user=Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{DOCUMENT_SERVICE_URL}/internal/documents/{document_id}",
            timeout=None,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )


# ==========================================================
# REINDEX ALL DOCUMENTS
# ==========================================================

@router.post("/documents/reindex-all")
async def reindex_all_documents(
    current_user=Depends(require_admin),
):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DOCUMENT_SERVICE_URL}/internal/documents/reindex-all",
            timeout=None,
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
    )