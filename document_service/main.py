from fastapi import FastAPI

from document_service.database import Base, engine
from document_service.models import Document
from document_service.routes.documents import (router as documents_router)

Base.metadata.create_all(
    bind=engine
)


app = FastAPI(
    title="Document Service",
    version="1.0.0"
)


@app.get("/internal/health")
def health_check():

    return {
        "status": "ok",
        "service": "document-service"
    }

app.include_router(documents_router)