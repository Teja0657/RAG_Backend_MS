from contextlib import asynccontextmanager

from fastapi import FastAPI

from rag_service.routes.query import router as query_router
from rag_service.routes.documents import router as documents_router
from rag_core.embedding.embedding import get_embedding_model

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Starting RAG Service...")

    print("Loading embedding model...")
    embedding_model = get_embedding_model()

    app.state.embedding_model = embedding_model

    print("RAG Service ready.")

    yield

    print("Shutting down RAG Service...")


app = FastAPI(
    title="Hybrid RAG Service",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/internal/health")
def health_check():
    return {
        "status": "ok",
        "service": "rag-service"
    }


app.include_router(query_router)

app.include_router(documents_router)