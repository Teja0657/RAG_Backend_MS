import time

from rag_core.retrieval.hybrid_retrieval import hybrid_search
from rag_core.reranking.reranking import rerank_documents
from rag_core.generation.generation import generate_answer


def retrieve_node(state):
    start = time.perf_counter()

    documents = hybrid_search(state["question"], k=8)

    elapsed_ms = round((time.perf_counter() - start) * 1000)

    return {
        "documents": documents,
        "timings": {**state.get("timings", {}), "retrieval_ms": elapsed_ms},
    }


def rerank_node(state):
    start = time.perf_counter()

    reranked = rerank_documents(state["question"], state["documents"], top_k=5)

    elapsed_ms = round((time.perf_counter() - start) * 1000)

    return {
        "reranked": reranked,
        "timings": {**state["timings"], "reranking_ms": elapsed_ms},
    }


def generate_node(state):
    start = time.perf_counter()

    answer = generate_answer(state["question"], state["reranked"])

    elapsed_ms = round((time.perf_counter() - start) * 1000)

    return {
        "answer": answer,
        "timings": {**state["timings"], "generation_ms": elapsed_ms},
    }
