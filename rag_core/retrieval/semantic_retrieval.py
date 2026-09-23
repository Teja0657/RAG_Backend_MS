from functools import lru_cache

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings


CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "knowledge_base"

DEFAULT_TOP_K = 5


@lru_cache(maxsize=1)
def get_vector_store():

    embedding_model = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001"
    )

    return Chroma(
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
    )


def retrieve_documents(
    question,
    k=DEFAULT_TOP_K,
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