from langchain_core.documents import Document

from rag_core.retrieval.semantic_retrieval import retrieve_documents
from rag_core.retrieval.lexical_retrieval import lexical_search


SEMANTIC_K = 8
BM25_K = 8
RRF_CANDIDATES = 8
RRF_K = 60


def get_chunk_id(document):
    return document.metadata.get("chunk_id") or document.page_content


def hybrid_search(question, k=RRF_CANDIDATES, verbose=False, metadata_filter=None):

    # --------------------------------------------------
    # Semantic retrieval
    # --------------------------------------------------

    semantic_results = retrieve_documents(
        question,
        k=SEMANTIC_K,
        metadata_filter=metadata_filter
    )

    # --------------------------------------------------
    # BM25 retrieval
    # --------------------------------------------------

    bm25_results = lexical_search(
        question,
        k=BM25_K,
        metadata_filter=metadata_filter
    )

    # --------------------------------------------------
    # Prepare ranked lists
    # --------------------------------------------------

    ranked_lists = []

    documents = {}

    # Semantic results
    semantic_docs = []

    for doc in semantic_results:

        chunk_id = get_chunk_id(doc)

        semantic_docs.append(chunk_id)

        documents[chunk_id] = doc

    ranked_lists.append(semantic_docs)

    # BM25 results
    bm25_docs = []

    for result in bm25_results:

        doc = Document(
            page_content=result["document"],
            metadata=result["metadata"]
        )

        chunk_id = get_chunk_id(doc)

        bm25_docs.append(chunk_id)

        documents[chunk_id] = doc

    ranked_lists.append(bm25_docs)

    # --------------------------------------------------
    # Reciprocal Rank Fusion
    # --------------------------------------------------

    rrf_scores = {}

    for ranked_list in ranked_lists:

        for rank, chunk_id in enumerate(
            ranked_list,
            start=1
        ):

            rrf_scores[chunk_id] = (
                rrf_scores.get(chunk_id, 0)
                + 1 / (RRF_K + rank)
            )

    # --------------------------------------------------
    # Sort by RRF score
    # --------------------------------------------------

    ranked_chunks = sorted(
        rrf_scores,
        key=rrf_scores.get,
        reverse=True
    )[:k]

    # --------------------------------------------------
    # Optional debugging
    # --------------------------------------------------

    if verbose:

        print(
            f"\nSemantic results: "
            f"{len(semantic_docs)}"
        )

        print(
            f"BM25 results: "
            f"{len(bm25_docs)}"
        )

        print(
            f"Final hybrid results: "
            f"{len(ranked_chunks)}"
        )

        for rank, chunk_id in enumerate(
            ranked_chunks,
            start=1
        ):

            doc = documents[chunk_id]

            page = doc.metadata.get("page")

            page_display = (
                page + 1
                if isinstance(page, int)
                else page
            )

            print(
                f"\nRank {rank} | "
                f"Page {page_display} | "
                f"RRF: {rrf_scores[chunk_id]:.6f}"
            )

            print(
                doc.page_content[:500]
            )

    return [
        documents[chunk_id]
        for chunk_id in ranked_chunks
    ]