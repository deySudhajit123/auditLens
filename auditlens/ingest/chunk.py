"""Split parsed 10-K sections into chunks, using two strategies for comparison.

Input:  data/parsed/*.json
Output: data/parsed/chunks/<doc_id>_<strategy>.jsonl

Run: python -m auditlens.ingest.chunk
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable

from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from auditlens.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNKS_DIR,
    EMBED_MODEL,
    PARSED_DIR,
    SEMANTIC_BREAKPOINT_AMOUNT,
    SEMANTIC_BREAKPOINT_TYPE,
)

Splitter = Callable[[str], list[str]]

TABLE_RE = re.compile(r"(\[TABLE\].*?\[/TABLE\])", re.DOTALL)


def build_splitters() -> dict[str, Splitter]:
    recursive = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    semantic = SemanticChunker(
        HuggingFaceEmbeddings(
            model_name=EMBED_MODEL, encode_kwargs={"normalize_embeddings": True}
        ),
        breakpoint_threshold_type=SEMANTIC_BREAKPOINT_TYPE,
        breakpoint_threshold_amount=SEMANTIC_BREAKPOINT_AMOUNT,
    )
    return {"recursive": recursive.split_text, "semantic": semantic.split_text}


def split_section(text: str, split: Splitter) -> list[str]:
    """Split prose with `split`; each [TABLE] block stays whole as its own chunk."""
    pieces: list[str] = []
    # re.split with a capture group puts the table blocks at odd indexes.
    for i, part in enumerate(TABLE_RE.split(text)):
        if i % 2:
            pieces.append(part)
        elif part.strip():
            pieces.extend(split(part.strip()))
    return [p.strip() for p in pieces if p.strip()]


def chunk_document(sections: list[dict], strategy: str, split: Splitter) -> list[dict]:
    chunks = []
    for section in sections:
        metadata = {k: v for k, v in section.items() if k != "text"}
        metadata["section_char_len"] = metadata.pop("char_len")
        for text in split_section(section["text"], split):
            index = len(chunks)
            chunks.append({
                **metadata,
                "chunk_id": f"{section['doc_id']}_{strategy}_{index:05d}",
                "chunk_index": index,
                "chunk_strategy": strategy,
                "char_len": len(text),
                "text": text,
            })
    return chunks


def main() -> None:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    splitters = build_splitters()
    totals = dict.fromkeys(splitters, 0)

    for path in sorted(PARSED_DIR.glob("*.json")):
        sections = json.loads(path.read_text(encoding="utf-8"))
        for strategy, split in splitters.items():
            chunks = chunk_document(sections, strategy, split)
            out = CHUNKS_DIR / f"{path.stem}_{strategy}.jsonl"
            with out.open("w", encoding="utf-8") as f:
                for chunk in chunks:
                    f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            totals[strategy] += len(chunks)
            print(f"  {path.stem}: {strategy}={len(chunks):,}", flush=True)

    print("  total: " + " | ".join(f"{k}={v:,}" for k, v in totals.items()))


if __name__ == "__main__":
    main()
