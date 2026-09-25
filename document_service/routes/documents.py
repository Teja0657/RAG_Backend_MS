import shutil

import hashlib
from pathlib import Path

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException,
    UploadFile
)
from sqlalchemy.orm import Session

from document_service.database import get_db, SessionLocal
from document_service.models import Document


router = APIRouter()


STORAGE_DIR = Path("document_storage")
RAG_SERVICE_URL = "http://127.0.0.1:8001"


# ==========================================================
# UPLOAD DOCUMENT
# ==========================================================

@router.post("/internal/documents")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # ------------------------------------------------------
    # 1. Validate filename
    # ------------------------------------------------------

    if not file.filename:

        return {
            "status": "error",
            "message": "Filename is required",
        }

    # ------------------------------------------------------
    # 2. Generate document ID
    # ------------------------------------------------------

    document_id = hashlib.sha256(
        file.filename.encode("utf-8")
    ).hexdigest()

    # ------------------------------------------------------
    # 3. Check whether document already exists
    # ------------------------------------------------------

    existing_document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if existing_document:

        return {
            "status": "error",
            "message": (
                "A document with this filename "
                "already exists. Use the update endpoint "
                "to replace it."
            ),
            "document_id": document_id,
        }

    # ------------------------------------------------------
    # 4. Create storage directory
    # ------------------------------------------------------

    STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ------------------------------------------------------
    # 5. Save physical file
    # ------------------------------------------------------

    file_path = STORAGE_DIR / file.filename

    with open(file_path, "wb") as output_file:

        while chunk := await file.read(1024 * 1024):

            output_file.write(chunk)

    # ------------------------------------------------------
    # 6. Create MySQL record
    # ------------------------------------------------------

    document = Document(
        id=document_id,
        filename=file.filename,
        file_path=str(file_path),
        version=1,
        status="PROCESSING",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # ------------------------------------------------------
    # 7. Tell RAG Service to index the document
    # ------------------------------------------------------

    try:

        async with httpx.AsyncClient() as client:

            response = await client.post(
                f"{RAG_SERVICE_URL}/internal/documents/index",
                json={
                    "document_id": document.id,
                    "document_version": document.version,
                    "file_path": document.file_path,
                },
                timeout=None,
            )

            response.raise_for_status()

        # --------------------------------------------------
        # 8. Mark document READY
        # --------------------------------------------------

        document.status = "READY"

        db.commit()

    except Exception as e:

        document.status = "FAILED"

        db.commit()

        return {
            "status": "error",
            "document_id": document.id,
            "message": str(e),
        }

    return {
        "status": "success",
        "document_id": document.id,
        "filename": document.filename,
        "version": document.version,
        "status": document.status,
    }


# ==========================================================
# LIST DOCUMENTS
# ==========================================================

@router.get("/internal/documents")
def list_documents(
    db: Session = Depends(get_db),
):
    documents = (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .all()
    )

    return {
        "documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "version": document.version,
                "status": document.status,
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            }
            for document in documents
        ]
    }


# ==========================================================
# UPDATE DOCUMENT
# ==========================================================

@router.put("/internal/documents/{document_id}")
async def update_document(
    document_id: str,
    file: UploadFile = File(...),
):
    db = SessionLocal()

    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        db.close()
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    old_file_path = Path(document.file_path)

    # Keep the same document ID, but create a temporary replacement file
    temp_file_path = (
        STORAGE_DIR
        / f".{document_id}.update{Path(file.filename).suffix}"
    )

    try:
        # -------------------------------------------------
        # 1. Save new file temporarily
        # -------------------------------------------------
        with temp_file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        new_version = document.version + 1

        # -------------------------------------------------
        # 2. Ask RAG service to index the new version
        # -------------------------------------------------
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/internal/documents/index",
                json={
                    "document_id": document_id,
                    "document_version": new_version,
                    "file_path": str(temp_file_path.resolve()),
                },
                timeout=None,
            )

        # IMPORTANT:
        # Do not treat HTTP 200 alone as success.
        response_data = response.json()

        if (
            response.status_code != 200
            or response_data.get("status") != "success"
        ):
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "RAG indexing failed",
                    "rag_response": response_data,
                },
            )

        # -------------------------------------------------
        # 3. Replace the old physical file
        # -------------------------------------------------
        temp_file_path.replace(old_file_path)

        # -------------------------------------------------
        # 4. Update database ONLY after RAG succeeds
        # -------------------------------------------------
        document.filename = file.filename
        document.file_path = str(old_file_path)
        document.version = new_version
        document.status = "READY"

        db.commit()
        db.refresh(document)

        return {
            "status": "success",
            "message": "Document updated successfully",
            "document": {
                "id": document.id,
                "filename": document.filename,
                "version": document.version,
                "status": document.status,
            },
            "rag": response_data,
        }

    except HTTPException:
        if temp_file_path.exists():
            temp_file_path.unlink()

        document.status = "FAILED"
        db.commit()

        raise

    except Exception as e:
        if temp_file_path.exists():
            temp_file_path.unlink()

        document.status = "FAILED"
        db.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Document update failed: {str(e)}",
        )

    finally:
        db.close()


# ==========================================================
# DELETE DOCUMENT
# ==========================================================

@router.delete("/internal/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    # ------------------------------------------------------
    # 1. Find document
    # ------------------------------------------------------

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:

        return {
            "status": "error",
            "message": "Document not found",
            "document_id": document_id,
        }

    file_path = Path(
        document.file_path
    )

    # ------------------------------------------------------
    # 2. Delete Chroma chunks FIRST
    # ------------------------------------------------------

    try:

        async with httpx.AsyncClient() as client:

            response = await client.delete(
                f"{RAG_SERVICE_URL}/internal/documents/"
                f"{document_id}",
                timeout=None,
            )

            response.raise_for_status()

            rag_result = response.json()

    except Exception as e:

        return {
            "status": "error",
            "document_id": document_id,
            "message": (
                "RAG deletion failed. "
                "Document was not deleted from MySQL."
            ),
            "error": str(e),
        }

    # ------------------------------------------------------
    # 3. Delete physical file
    # ------------------------------------------------------

    try:

        if file_path.exists():

            file_path.unlink()

    except Exception as e:

        return {
            "status": "error",
            "document_id": document_id,
            "message": (
                "Chroma chunks were deleted, "
                "but the physical file could not be deleted."
            ),
            "error": str(e),
        }

    # ------------------------------------------------------
    # 4. Delete MySQL record
    # ------------------------------------------------------

    db.delete(document)
    db.commit()

    return {
        "status": "success",
        "document_id": document_id,
        "rag_result": rag_result,
    }


# ==========================================================
# REINDEX ALL DOCUMENTS
# ==========================================================

@router.post("/internal/documents/reindex-all")
async def reindex_all_documents(
    db: Session = Depends(get_db),
):
    """
    Re-index every document registered in MySQL.

    Used as a bootstrap/recovery operation.
    """

    documents = (
        db.query(Document)
        .order_by(Document.created_at.asc())
        .all()
    )

    results = []

    async with httpx.AsyncClient() as client:

        for document in documents:

            try:

                response = await client.post(
                    f"{RAG_SERVICE_URL}/internal/documents/index",
                    json={
                        "document_id": document.id,
                        "document_version": document.version,
                        "file_path": document.file_path,
                    },
                    timeout=None,
                )

                response.raise_for_status()

                result = response.json()

                document.status = "READY"

                results.append({
                    "document_id": document.id,
                    "filename": document.filename,
                    "status": "READY",
                    "rag_result": result,
                })

            except Exception as e:

                document.status = "FAILED"

                results.append({
                    "document_id": document.id,
                    "filename": document.filename,
                    "status": "FAILED",
                    "error": str(e),
                })

    db.commit()

    return {
        "status": "completed",
        "total_documents": len(documents),
        "results": results,
    }