"""Model registry and global defaults."""

MODELS = {
    # DEFAULT — 384 dims, ~37MB vectors for 100k chunks (int8), MAP=0.34 on Sonar
    "bge-small": {"name": "BAAI/bge-small-en-v1.5", "dim": 384},
    # Research — 1024 dims, ~100MB (int8), MAP=0.37 on Sonar
    "bge-large": {"name": "BAAI/bge-large-en-v1.5", "dim": 1024},
}

DEFAULT_MODEL = "bge-small"
DEFAULT_TOP_K = 10
DEFAULT_TOP_N = 10
DEFAULT_TOP_M = 5

# Storage directory relative to working directory
STORE_DIR = ".simargl"
