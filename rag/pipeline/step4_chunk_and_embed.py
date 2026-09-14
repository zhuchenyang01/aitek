"""Step4: 分块 -> 转向量 -> 存 jsonl（文档块向量库）。"""
from __future__ import annotations

from typing import Any

from rag import config
from rag.models.embedding_client import EmbeddingClient
from rag.store.jsonl_store import save_jsonl
from rag.utils.timing import timed


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


@timed("step4_chunk_and_embed")
def run(pure_text: str) -> list[dict[str, Any]]:
    print("=" * 60)
    print("Step4 分块 / 转向量 / 存向量库(jsonl)")
    print("=" * 60)
    config.ensure_dirs()
    chunks = chunk_text(pure_text)
    print(f"[Step4] 分块数={len(chunks)} size={config.CHUNK_SIZE} overlap={config.CHUNK_OVERLAP}")
    embedder = EmbeddingClient()
    vectors = embedder.embed_batch(chunks)
    rows = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        rows.append(
            {
                "id": f"chunk_{i:04d}",
                "feature": chunk,  # 块内容
                "vector": vec,
                "kind": "chunk",
            }
        )
    save_jsonl(config.CHUNK_JSONL, rows)
    print(f"[Step4] 完成，示例首块预览: {chunks[0][:80] if chunks else ''}")
    return rows
