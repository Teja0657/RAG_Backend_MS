import hashlib
from pathlib import Path

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
)
from sqlalchemy.orm import Session

from document_service.database import get_db
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
    # 2. Find existing document
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
    
    previous_status= document.status
    document.status="PROCESSING"

    # ------------------------------------------------------
    # 3. Prepare storage
    # ------------------------------------------------------

    STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    old_file_path = Path(
        document.file_path
    )

    # Temporary file used for safe indexing
    file_extenstion=Path(file.filename).suffix
    temp_file_path=(
        STORAGE_DIR
        /f".{document_id}.update{file_extenstion}"
    )
    # ------------------------------------------------------
    # 4. Save replacement file temporarily
    # ------------------------------------------------------

    try:

        with open(
            temp_file_path,
            "wb",
        ) as output_file:

            while chunk := await file.read(
                1024 * 1024
            ):

                output_file.write(chunk)

        # --------------------------------------------------
        # 5. Calculate next version
        # --------------------------------------------------

        new_version = document.version + 1

        # --------------------------------------------------
        # 6. Mark as PROCESSING
        # --------------------------------------------------

        document.status = "PROCESSING"

        db.commit()

        # --------------------------------------------------
        # 7. Ask RAG Service to index NEW file
        # --------------------------------------------------

        async with httpx.AsyncClient() as client:

            response = await client.post(
                f"{RAG_SERVICE_URL}/internal/documents/index",
                json={
                    "document_id": document.id,
                    "document_version": new_version,
                    "file_path": str(temp_file_path),
                },
                timeout=None,
            )

            response.raise_for_status()

        # --------------------------------------------------
        # 8. RAG indexing succeeded
        # --------------------------------------------------

        # Replace old physical file only AFTER successful
        # RAG indexing.
        temp_file_path.replace(old_file_path)

        # --------------------------------------------------
        # 9. Update MySQL metadata
        # --------------------------------------------------

        document.version = new_version
        document.filename = file.filename
        document.file_path = str(old_file_path)
        document.status = "READY"

        db.commit()
        db.refresh(document)

        return {
            "status": "success",
            "document_id": document.id,
            "filename": document.filename,
            "version": document.version,
            "status": document.status,
        }

    except Exception as e:

        # --------------------------------------------------
        # Cleanup temporary file
        # --------------------------------------------------

        if temp_file_path.exists():

            temp_file_path.unlink()

        # --------------------------------------------------
        # Keep original document metadata
        # --------------------------------------------------

        document.status = previous_status

        db.commit()

        return {
            "status": "error",
            "document_id": document.id,
            "version": document.version,
            "message": str(e),
        }


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