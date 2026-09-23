import re
import unicodedata

import chromadb
from rank_bm25 import BM25Okapi


CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "knowledge_base"

DEFAULT_K = 5


def tokenize(text):

    text = unicodedata.normalize(
        "NFKC",
        text
    ).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return re.findall(
        r"[a-z0-9]+(?:[._-][a-z0-9]+)*|[a-z](?=\.)",
        text
    )


def lexical_search(
    question,
    k=DEFAULT_K,
    metadata_filter=None
):
    """
    BM25 lexical retrieval.

    metadata_filter:
        Optional Chroma metadata filter.
    """

    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    collection = client.get_collection(
        COLLECTION_NAME
    )

    # --------------------------------------------------
    # Retrieve documents from Chroma
    # --------------------------------------------------

    data = collection.get(
        where=metadata_filter
    )

    documents = data["documents"]
    metadatas = data["metadatas"]

    if not documents:
        return []

    # --------------------------------------------------
    # Build BM25 index
    # --------------------------------------------------

    tokenized_documents = [
        tokenize(document)
        for document in documents
    ]

    bm25 = BM25Okapi(
        tokenized_documents
    )

    query_tokens = tokenize(question)

    scores = bm25.get_scores(
        query_tokens
    )

    # --------------------------------------------------
    # Rank documents
    # --------------------------------------------------

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True
    )

    results = []

    for index in ranked_indices[:k]:

        results.append({
            "document": documents[index],
            "metadata": metadatas[index],
            "score": float(scores[index])
        })

    return results


bm25_search = lexical_search