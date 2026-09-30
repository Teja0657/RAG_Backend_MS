from functools import lru_cache

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from langsmith import traceable

from rag_core.config import (
    CHROMA_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    SEMANTIC_K,
)


@lru_cache(maxsize=1)
def get_vector_store():

    embedding_model = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL
    )

    return Chroma(
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
    )

@traceable(
    name="Semanti Retrieval",
    tags=["rag", "retrieval","semantic"],
        metadata={
            "default_top_k": SEMANTIC_K,
            "embedding_model": EMBEDDING_MODEL,
            "vector_store": "chroma",
        }
    )
def retrieve_documents(
    question,
    k=SEMANTIC_K,
    metadata_filter=None
):
    """
    Semantic similarity retrieval.

    metadata_filter:
        Optional Chroma metadata filter.

        Examples:
            {"source": "policy.pdf"}
            {"file_type": "pdf"}
    """

    vector_store = get_vector_store()

    results = vector_store.similarity_search_with_relevance_scores(
        question,
        k=k,
        filter=metadata_filter
    )

    return [
        document
        for document, score in results
    ]