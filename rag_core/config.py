# LLM models (LangChain init_chat_model "provider:model" format)
GENERATION_MODEL = "google_genai:gemini-3.5-flash-lite"#"anthropic:claude-sonnet-4-6"
RERANK_MODEL = "google_genai:gemini-3.5-flash-lite"#"anthropic:claude-sonnet-4-6"

# Embedding
EMBEDDING_MODEL = "gemini-embedding-001"

# Chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Vector store
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "knowledge_base"
BATCH_SIZE = 90
BATCH_DELAY = 60

# Retrieval
SEMANTIC_K = 8
BM25_K = 8
RRF_CANDIDATES = 8
RRF_K = 60

# Reranking
RERANK_DEFAULT_TOP_K = 5
