"""Every tunable, in one place."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Paths
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PARSED_DIR = DATA_DIR / "parsed"
MANIFEST_PATH = DATA_DIR / "manifest.json"
CHUNKS_DIR = PARSED_DIR / "chunks"

# Parsing
MIN_TABLE_CHARS = 40       # below this a <table> is layout, not data

# Embedding
EMBED_MODEL = "BAAI/bge-small-en-v1.5"   # 384-dim, local, free
EMBED_DIM = 384
EMBED_BATCH_SIZE = 64

# Chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
SEMANTIC_BREAKPOINT_TYPE = "percentile"
SEMANTIC_BREAKPOINT_AMOUNT = 95

# Retrieval
TOP_K = 5
COLLECTION = "auditlens"
QDRANT_URL = "http://localhost:6333"

# Generation
LLM_MODEL = "..."     # whatever you're using to generate
