"""向量模型客户端：支持 batch 与并发。"""
from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Sequence

import httpx
import numpy as np

from rag import config
from rag.utils.timing import timed


def _local_hash_embed(text: str, dim: int = 384) -> list[float]:
    """无 API 时的确定性伪向量，便于离线跑通流程。"""
    vec = np.zeros(dim, dtype=np.float32)
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    for i in range(dim):
        vec[i] = ((digest[i % len(digest)] / 255.0) * 2 - 1) * (1.0 / (1 + (i % 17)))
    # 混入长度信息
    vec[0] += len(text) % 97 / 97.0
    n = np.linalg.norm(vec)
    if n > 0:
        vec = vec / n
    return vec.tolist()


class EmbeddingClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        batch_size: int | None = None,
        concurrency: int | None = None,
        timeout: float | None = None,
        use_local: bool | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else config.EMBEDDING_API_KEY
        self.base_url = (base_url or config.EMBEDDING_BASE_URL).rstrip("/")
        self.model = model or config.EMBEDDING_MODEL
        self.batch_size = batch_size or config.EMBEDDING_BATCH_SIZE
        self.concurrency = concurrency or config.EMBEDDING_CONCURRENCY
        self.timeout = timeout or config.HTTP_TIMEOUT
        if use_local is None:
            use_local = config.EMBEDDING_USE_LOCAL or os.getenv("EMBEDDING_USE_LOCAL", "").lower() in (
                "1",
                "true",
                "yes",
            )
        self.use_local = bool(use_local)
        # Ollama 等本地服务不需要真实 Key；无 Key 时仍走 HTTP，避免误入哈希伪向量
        if not self.use_local and not self.api_key:
            self.api_key = "ollama"

    def _embed_one_batch(self, texts: list[str]) -> list[list[float]]:
        if self.use_local:
            print(f"[Embed] 本地伪向量 batch={len(texts)}")
            return [_local_hash_embed(t) for t in texts]

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": texts}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        # OpenAI 风格：data[].embedding，按 index 排序
        items = sorted(data["data"], key=lambda x: x.get("index", 0))
        return [it["embedding"] for it in items]

    @timed("embedding.embed_batch")
    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        text_list = list(texts)
        if not text_list:
            return []

        batches = [
            text_list[i : i + self.batch_size]
            for i in range(0, len(text_list), self.batch_size)
        ]
        print(
            f"[Embed] 文本数={len(text_list)}, batch_size={self.batch_size}, "
            f"batches={len(batches)}, concurrency={self.concurrency}, local={self.use_local}"
        )

        results: list[list[list[float]] | None] = [None] * len(batches)
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {
                pool.submit(self._embed_one_batch, batch): idx
                for idx, batch in enumerate(batches)
            }
            for fut in as_completed(futures):
                idx = futures[fut]
                results[idx] = fut.result()

        vectors: list[list[float]] = []
        for part in results:
            assert part is not None
            vectors.extend(part)
        print(f"[Embed] 完成向量数={len(vectors)}, dim={len(vectors[0]) if vectors else 0}")
        return vectors
