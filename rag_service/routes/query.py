import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse


from rag_core.retrieval.hybrid_retrieval import hybrid_search
from rag_core.reranking.reranking import rerank_documents
from rag_core.generation.generation import generate_answer, generate_answer_stream
from rag_service.internal_auth import verify_internal_secret


from langsmith import traceable, get_current_run_tree

router = APIRouter(dependencies=[Depends(verify_internal_secret)])


class QueryRequest(BaseModel):
    question: str


@router.post("/internal/query")
@traceable(name="RAG Query", tags=["rag", "query"],)
def query_rag(request: QueryRequest):

    retrieval_start = time.perf_counter()

    candidates = hybrid_search(
        request.question,
        k=8
    )

    retrieval_ms = round((time.perf_counter() - retrieval_start) * 1000)

    rerank_start = time.perf_counter()

    reranked_documents = rerank_documents(
        request.question,
        candidates,
        top_k=5,
        model="claude"
    )

    reranking_ms = round((time.perf_counter() - rerank_start) * 1000)

    generation_start = time.perf_counter()

    answer = generate_answer(
        request.question,
        reranked_documents,
        model="claude"
    )

    generation_ms = round((time.perf_counter() - generation_start) * 1000)

    run_tree = get_current_run_tree()
    trace_url = run_tree.get_url() if run_tree is not None else None

    return {
        "answer": answer,
        "context":[
            document.page_content
            for document in reranked_documents
        ],
        "timings": {
            "retrieval_ms": retrieval_ms,
            "reranking_ms": reranking_ms,
            "generation_ms": generation_ms,
        },
        "trace_url": trace_url,
    }

@traceable(name="RAG Query", tags=["rag", "query", "streaming"])
def _stream_rag_answer(question):

    candidates = hybrid_search(
        question,
        k=8
    )

    reranked_documents = rerank_documents(
        question,
        candidates,
        top_k=5,
        model="claude"
    )

    try:
        for chunk in generate_answer_stream(
            question,
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


@router.post("/internal/query/stream")
def query_rag_stream(request: QueryRequest):
    return EventSourceResponse(_stream_rag_answer(request.question))
