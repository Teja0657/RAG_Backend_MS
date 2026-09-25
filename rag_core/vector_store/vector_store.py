import time

from langchain_chroma import Chroma


CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "knowledge_base"

BATCH_SIZE = 90
BATCH_DELAY = 60


# ==========================================================
# VECTOR STORE
# ==========================================================

def get_vector_store(embedding_model):
    """
    Create or load the Chroma vector store.
    """

    return Chroma(
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
    )


# ==========================================================
# DOCUMENT-SCOPED SYNC
# ==========================================================

def sync_document_chunks(
    document_id,
    chunks,
    embedding_model,
):
    """
    Synchronize chunks for ONE document safely.

    New chunks:
        -> embed + add

    Changed chunks:
        -> new chunk is embedded + added
        -> old chunk is deleted only after successful addition

    Unchanged chunks:
        -> keep

    Removed chunks:
        -> delete after successful additions

    Other documents:
        -> completely untouched
    """

    vector_store = get_vector_store(
        embedding_model
    )

    collection = vector_store._collection

    # ------------------------------------------------------
    # Current chunk IDs
    # ------------------------------------------------------

    current_ids = {
        chunk.metadata["chunk_id"]
        for chunk in chunks
    }

    # ------------------------------------------------------
    # Existing chunks for THIS document only
    # ------------------------------------------------------

    existing_data = collection.get(
        where={
            "document_id": document_id
        },
        include=["metadatas"],
    )

    existing_ids = set(
        existing_data["ids"]
    )

    # ------------------------------------------------------
    # NEW / CHANGED chunks
    # ------------------------------------------------------

    new_chunks = [
        chunk
        for chunk in chunks
        if chunk.metadata["chunk_id"]
        not in existing_ids
    ]

    # ------------------------------------------------------
    # REMOVED / OLD chunks
    # ------------------------------------------------------

    stale_ids = (
        existing_ids - current_ids
    )

    # ------------------------------------------------------
    # ADD NEW CHUNKS FIRST
    # ------------------------------------------------------
    #
    # Important:
    # We intentionally add new chunks BEFORE deleting
    # stale chunks.
    #
    # If embedding fails here, the old chunks remain intact.
    # ------------------------------------------------------

    if new_chunks:

        print(
            f"Adding {len(new_chunks)} "
            f"new/changed chunks..."
        )

        for start in range(
            0,
            len(new_chunks),
            BATCH_SIZE,
        ):

            batch = new_chunks[
                start:start + BATCH_SIZE
            ]

            print(
                f"Adding batch "
                f"{start // BATCH_SIZE + 1} "
                f"({len(batch)} chunks)"
            )

            vector_store.add_documents(
                batch,
                ids=[
                    chunk.metadata["chunk_id"]
                    for chunk in batch
                ],
            )

            # --------------------------------------------------
            # Gemini embedding rate-limit protection
            # --------------------------------------------------

            if (
                start + BATCH_SIZE
                < len(new_chunks)
            ):

                print(
                    f"Waiting {BATCH_DELAY} "
                    f"seconds before next batch..."
                )

                time.sleep(
                    BATCH_DELAY
                )

    # ------------------------------------------------------
    # DELETE STALE CHUNKS
    # ------------------------------------------------------
    #
    # This happens ONLY after all new chunks were added
    # successfully.
    # ------------------------------------------------------

    if stale_ids:

        print(
            f"Deleting {len(stale_ids)} "
            f"old chunks for document "
            f"{document_id}..."
        )

        collection.delete(
            ids=list(stale_ids)
        )

    # ------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------

    print("\nDocument sync complete")

    print(
        f"Document ID : {document_id}"
    )

    print(
        f"Existing    : {len(existing_ids)}"
    )

    print(
        f"Added       : {len(new_chunks)}"
    )

    print(
        f"Deleted     : {len(stale_ids)}"
    )

    print(
        f"Current     : {len(current_ids)}"
    )

    return {
        "existing": len(existing_ids),
        "added": len(new_chunks),
        "deleted": len(stale_ids),
        "current": len(current_ids),
    }

# ==========================================================
# DELETE DOCUMENT
# ==========================================================

def delete_document_chunks(
    document_id,
    embedding_model,
):
    """
    Delete all Chroma chunks belonging
    to one document.
    """

    vector_store = get_vector_store(
        embedding_model
    )

    collection = vector_store._collection

    # ------------------------------------------------------
    # Find chunks belonging to this document
    # ------------------------------------------------------

    existing_data = collection.get(
        where={
            "document_id": document_id
        },
        include=["metadatas"],
    )

    existing_ids = existing_data["ids"]

    # ------------------------------------------------------
    # Nothing to delete
    # ------------------------------------------------------

    if not existing_ids:

        print(
            f"No chunks found for document "
            f"{document_id}"
        )

        return {
            "deleted": 0
        }

    # ------------------------------------------------------
    # Delete chunks
    # ------------------------------------------------------

    collection.delete(
        ids=existing_ids
    )

    print(
        f"Deleted {len(existing_ids)} chunks "
        f"for document {document_id}"
    )

    return {
        "deleted": len(existing_ids)
    }

# ==========================================================
# COLLECTION STATS
# ==========================================================

def get_indexed_chunk_count(embedding_model):
    """
    Return the total number of chunks currently
    indexed in the Chroma collection.
    """
    vector_store = get_vector_store(
        embedding_model
    )
    collection = vector_store._collection
    return collection.count() 

