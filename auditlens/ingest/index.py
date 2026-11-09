"""Embed every chunk and load it into Qdrant, rebuilding the collection.

Input:  data/parsed/chunks/*.jsonl
Output: the Qdrant collection named by config.COLLECTION

Run: python -m auditlens.ingest.index
"""
from __future__ import annotations

import json
import uuid

from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from auditlens.config import (
    CHUNKS_DIR,
    COLLECTION,
    EMBED_BATCH_SIZE,
    EMBED_DIM,
    EMBED_MODEL,
    QDRANT_URL,
)


def point_id(chunk_id: str) -> str:
    """Qdrant only accepts integers or UUIDs, so derive a stable UUID."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def load_chunks() -> list[dict]:
    chunks = []
    for path in sorted(CHUNKS_DIR.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            chunks.extend(json.loads(line) for line in f)
    return chunks


def main() -> None:
    chunks = load_chunks()
    embedder = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True, "batch_size": EMBED_BATCH_SIZE},
    )
    client = QdrantClient(url=QDRANT_URL)

    # Rebuild from scratch so points from an earlier chunking run cannot linger.
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        COLLECTION,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )

    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start:start + EMBED_BATCH_SIZE]
        vectors = embedder.embed_documents([chunk["text"] for chunk in batch])
        client.upsert(
            COLLECTION,
            points=[
                PointStruct(id=point_id(chunk["chunk_id"]), vector=vector, payload=chunk)
                for chunk, vector in zip(batch, vectors)
            ],
            wait=True,
        )
        print(f"  {start + len(batch):,}/{len(chunks):,}", flush=True)

    print(f"  count={client.count(COLLECTION).count:,} | chunks={len(chunks):,}")


if __name__ == "__main__":
    main()
