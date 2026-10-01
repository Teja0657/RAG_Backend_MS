from typing import TypedDict


class RagState(TypedDict):
    question: str
    documents: list
    reranked: list
    answer: str
    timings: dict
