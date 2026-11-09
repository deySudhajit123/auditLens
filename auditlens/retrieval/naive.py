"""Naive RAG: the control group. Deliberately weak, so do not improve it.

Run: python -m auditlens.retrieval.naive "your question"
"""
from __future__ import annotations

import sys

import ollama
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

from auditlens.config import (
    COLLECTION,
    EMBED_MODEL,
    LLM_MODEL,
    LLM_NUM_CTX,
    QDRANT_URL,
    TOP_K,
)


def query(question: str) -> dict:
    embedder = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL, encode_kwargs={"normalize_embeddings": True}
    )
    hits = QdrantClient(url=QDRANT_URL).query_points(
        COLLECTION, query=embedder.embed_query(question), limit=TOP_K
    ).points

    context = "\n\n".join(hit.payload["text"] for hit in hits)
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": f"{context}\n\nQuestion: {question}"}],
        options={"num_ctx": LLM_NUM_CTX},
    )
    return {
        "answer": response.message.content,
        "sources": [
            {k: v for k, v in hit.payload.items() if k != "text"} for hit in hits
        ],
    }


if __name__ == "__main__":
    result = query(sys.argv[1])
    print(result["answer"])
    for source in result["sources"]:
        print(source)
