from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from rag_core.ingestion.ingestion import load_document
from rag_core.chunking.chunking import create_chunks
from rag_core.vector_store.vector_store import (
   sync_document_chunks,delete_document_chunks,
)


router = APIRouter()


class DocumentIndexRequest(BaseModel):

    document_id: str
    document_version: int
    file_path: str


@router.post("/internal/documents/index")
def index_document(
    request: Request,
    document: DocumentIndexRequest
):

    embedding_model = request.app.state.embedding_model

    file_path = Path(
        document.file_path
    )

    if not file_path.exists():

        return {
            "status": "error",
            "message": "File not found"
        }

    # --------------------------------------------------
    # Load document
    # --------------------------------------------------

    documents = load_document(
        str(file_path)
    )

    # --------------------------------------------------
    # Create chunks
    # --------------------------------------------------

    chunks = create_chunks(
        documents,
        document_id=document.document_id,
        document_version=document.document_version
    )

    # --------------------------------------------------
    # Synchronize Chroma
    # --------------------------------------------------

    sync_result=sync_document_chunks(
        document.document_id,
        chunks,
        embedding_model
    )

    return {
        "status": "success",
        "document_id": document.document_id,
        "document_version": document.document_version,
        "chunks_indexed": len(chunks),
        "sync": sync_result
    }


@router.delete("/internal/documents/{document_id}")
def delete_document(
    request: Request,
    document_id: str 
):
    embedding_model=(request.app.state.embedding_model)
    result= delete_document_chunks(document_id, embedding_model)

    return{
        "status": "success",
        "document_id":document_id,
        "deleted_chunks": result["deleted"]
    }

