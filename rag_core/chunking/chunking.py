import hashlib

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def generate_content_hash(content):
    """
    Generate SHA-256 hash from chunk content.

    Same content
        -> same hash

    Changed content
        -> different hash
    """

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def generate_chunk_id(document_id, content_hash):
    """
    Generate deterministic chunk ID.

    Same document + same content
        -> same chunk ID

    Same document + changed content
        -> different chunk ID
    """

    raw_id = f"{document_id}_{content_hash}"

    return hashlib.sha256(
        raw_id.encode("utf-8")
    ).hexdigest()


def create_chunks(
    documents,
    document_id="default_document",
    document_version=1
):
    """
    Split documents and assign document/chunk metadata.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks):

        content_hash = generate_content_hash(
            chunk.page_content
        )

        chunk_id = generate_chunk_id(
            document_id,
            content_hash
        )

        chunk.metadata["document_id"] = document_id
        chunk.metadata["document_version"] = document_version
        chunk.metadata["content_hash"] = content_hash
        chunk.metadata["chunk_id"] = chunk_id
        chunk.metadata["chunk_index"] = index

    return chunks