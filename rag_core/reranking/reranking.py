import json

from rag_core.generation.generation import get_llm, extract_text
from rag_core.config import RERANK_MODEL, RERANK_DEFAULT_TOP_K

from langsmith import traceable, get_current_run_tree

@traceable(
    name="Reranking",
    tags=["rag","reranking"],
    metadata={
        "default_top_k": RERANK_DEFAULT_TOP_K,
    }

    )
def rerank_documents(
    question,
    documents,
    top_k=RERANK_DEFAULT_TOP_K
):
    """
    Rerank retrieved documents using an LLM.
    """

    if not documents:
        return []

    llm = get_llm(RERANK_MODEL)

    # --------------------------------------------------
    # Prepare candidate documents
    # --------------------------------------------------

    candidates = []

    for index, document in enumerate(documents):

        candidates.append({
            "id": index,
            "content": document.page_content
        })

    # --------------------------------------------------
    # Reranking prompt
    # --------------------------------------------------

    prompt = f"""
You are a document relevance reranker.

Your task is to rank the provided documents according
to their relevance to the user's question.

User question:
{question}

Documents:
{json.dumps(candidates, indent=2)}

Instructions:

1. Evaluate every document against the user's question.
2. Prefer documents that directly contain information
   useful for answering the question.
3. Consider semantic meaning, not just keyword overlap.
4. Do not rank a document highly merely because it
   shares a few keywords.
5. Rank all documents from most relevant to least relevant.
6. Return ONLY a JSON array containing the document IDs.
7. Do not include explanations, markdown, or additional text.

Example:
[3, 0, 5, 1, 2, 4]
"""

    # --------------------------------------------------
    # Call LLM
    # --------------------------------------------------

    response = llm.invoke(prompt)

    # --------------------------------------------------
    # Normalize LLM response
    # --------------------------------------------------

    content = extract_text(response.content).strip()

    # --------------------------------------------------
    # Remove markdown code fences if present
    # --------------------------------------------------

    if content.startswith("```"):

        content = content.replace(
            "```json",
            ""
        )

        content = content.replace(
            "```",
            ""
        )

        content = content.strip()

    # --------------------------------------------------
    # Parse JSON
    # --------------------------------------------------

    try:

        ranked_ids = json.loads(content)

    except json.JSONDecodeError:

        print(
            "Warning: Reranker returned invalid JSON."
        )

        print(
            f"Reranker response: {content}"
        )

        return documents[:top_k]

    # --------------------------------------------------
    # Validate ranked IDs
    # --------------------------------------------------

    ranked_documents = []

    seen = set()

    for document_id in ranked_ids:

        if (
            isinstance(document_id, int)
            and 0 <= document_id < len(documents)
            and document_id not in seen
        ):

            ranked_documents.append(
                documents[document_id]
            )

            seen.add(document_id)

    # --------------------------------------------------
    # Fallback for omitted documents
    # --------------------------------------------------

    for index, document in enumerate(documents):

        if index not in seen:

            ranked_documents.append(
                document
            )

    # --------------------------------------------------
    # Return final Top-K
    # --------------------------------------------------

    final_documents = ranked_documents[:top_k]

    run_tree = get_current_run_tree()

    if run_tree is not None:
        run_tree.add_metadata({
            "candidates_in": len(documents),
            "reranked_out": len(final_documents),
        })

    return final_documents