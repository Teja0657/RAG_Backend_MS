from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse

from rag_core.retrieval.hybrid_retrieval import hybrid_search
from rag_core.reranking.reranking import rerank_documents
from rag_core.generation.generation import generate_answer, generate_answer_stream



router = APIRouter()


class QueryRequest(BaseModel):
    question: str


@router.post("/internal/query")
def query_rag(request: QueryRequest):

    candidates = hybrid_search(
        request.question,
        k=8
    )

    reranked_documents = rerank_documents(
        request.question,
        candidates,
        top_k=5,
        model="claude"
    )

    answer = generate_answer(
        request.question,
        reranked_documents,
        model="claude"
    )

    return {
        "answer": answer
    }

@router.post("/internal/query/stream")
def query_rag_stream(request: QueryRequest):

    candidates = hybrid_search(
        request.question,
        k=8
    )

    reranked_documents = rerank_documents(
        request.question,
        candidates,
        top_k=5,
        model="claude"
    )

    def generate():
        try:
            for chunk in generate_answer_stream(
                request.question,
                reranked_documents
            ):
                yield {
                    "event" : "token",
                    "data" : chunk
                }
                yield{
                    "event": "done",
                    "data": "complete"
                }
        except Exception as e:
            yield{
                "event": "error",
                "data": str(e)
            }

    return EventSourceResponse(generate())
