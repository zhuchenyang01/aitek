"""Rerank 客户端：优先 HTTP API，否则本地余弦重排。"""
from __future__ import annotations

from typing import Any

import httpx
import numpy as np

from rag import config
from rag.models.embedding_client import EmbeddingClient
from rag.utils.similarity import batch_cosine
from rag.utils.timing import timed


class RerankClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        embedder: EmbeddingClient | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else config.RERANK_API_KEY
        self.base_url = (base_url or config.RERANK_BASE_URL).rstrip("/")
        self.model = model or config.RERANK_MODEL
        self.timeout = timeout or config.HTTP_TIMEOUT
        self.embedder = embedder

    @timed("rerank.rerank")
    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int | None = None,
        text_key: str = "feature",
    ) -> list[dict[str, Any]]:
        """
        documents: 至少含 text_key；可含 id/score。
        返回按相关性降序的前 top_k 条，附加 rerank_score。
        """
        top_k = top_k or config.RERANK_TOP_K
        if not documents:
            return []

        if self.api_key and self.base_url:
            try:
                return self._http_rerank(query, documents, top_k, text_key)
            except Exception as exc:  # noqa: BLE001
                print(f"[Rerank] HTTP 失败，降级本地余弦: {exc}")

        return self._local_cosine_rerank(query, documents, top_k, text_key)

    def _http_rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int,
        text_key: str,
    ) -> list[dict[str, Any]]:
        # 兼容常见 rerank 接口形态
        url = f"{self.base_url}/rerank"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "query": query,
            "documents": [d.get(text_key, "") for d in documents],
            "top_n": top_k,
        }
        print(f"[Rerank] HTTP POST {url}")
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results") or data.get("data") or []
        ranked: list[dict[str, Any]] = []
        for item in results:
            idx = item.get("index", item.get("idx"))
            score = item.get("relevance_score", item.get("score", 0.0))
            if idx is None:
                continue
            row = dict(documents[int(idx)])
            row["rerank_score"] = float(score)
            ranked.append(row)
        ranked.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        print(f"[Rerank] HTTP 完成 top_k={min(top_k, len(ranked))}")
        return ranked[:top_k]

    def _local_cosine_rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int,
        text_key: str,
    ) -> list[dict[str, Any]]:
        print("[Rerank] 使用本地余弦重排（无专用 rerank API）")
        embedder = self.embedder or EmbeddingClient()
        texts = [str(d.get(text_key, "")) for d in documents]
        q_vec = embedder.embed_batch([query])[0]
        doc_vecs = embedder.embed_batch(texts)
        matrix = np.asarray(doc_vecs, dtype=np.float32)
        scores = batch_cosine(q_vec, matrix)
        ranked = []
        for i, doc in enumerate(documents):
            row = dict(doc)
            row["rerank_score"] = float(scores[i])
            ranked.append(row)
        ranked.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        print(f"[Rerank] 本地重排完成 top_k={min(top_k, len(ranked))}")
        return ranked[:top_k]
