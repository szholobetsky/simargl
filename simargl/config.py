"""Model registry and global defaults."""

MODELS = {
    # DEFAULT — 384 dims, ~37MB vectors for 100k chunks (int8), MAP=0.34 on Sonar
    "bge-small": {"name": "BAAI/bge-small-en-v1.5", "dim": 384},
    # Research — 1024 dims, ~100MB (int8), MAP=0.37 on Sonar
    "bge-large": {"name": "BAAI/bge-large-en-v1.5", "dim": 1024},
    # Code-specific — 768 dims, trained on code + natural language pairs
    # Handles camelCase, snake_case, identifiers natively
    # Requires trust_remote_code=True (Jina custom pooling layer)
    # batch_size=1: ALiBi attention is quadratic in seq_len; large batches OOM on CPU
    # max_seq_length=512: caps input to avoid 18GB+ attention matrices
    "jina-code": {"name": "jinaai/jina-embeddings-v2-base-code", "dim": 768,
                  "trust_remote_code": True, "batch_size": 1, "max_seq_length": 512},
}

DEFAULT_MODEL = "bge-small"
DEFAULT_TOP_K = 10
DEFAULT_TOP_N = 10
DEFAULT_TOP_M = 5

# Storage directory relative to working directory
STORE_DIR = ".simargl"
