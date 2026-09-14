import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Sequence

import httpx
import numpy as np


def _local_hash_embed(text: str, dim: int = 384) -> list[float]:
    vec = np.zeros(dim, dtype=np.float32)
    digest = hashlib.sha256(text.encode('utf-8')).digest()
    for i in range(dim):
        vec[i] = ((digest[i % len(digest)] / 255.0) * 2 - 1) * (1.0 / (1 + (i % 17)))
    vec[0] += len(text) % 97 / 97.0
    n = np.linalg.norm(vec)
    if n > 0:
        vec = vec / n
    return vec.tolist()


class EmbeddingClient:
    def __init__(
        self,
        api_key='',
        base_url=None,
        model=None,
        batch_size=16,
        concurrency=4,
        timeout=120.0,
        use_local=False,
    ):
        self.api_key = api_key or ''
        self.base_url = (base_url or 'http://127.0.0.1:11434/v1').rstrip('/')
        self.model = model or 'bge-m3:latest'
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.timeout = float(timeout or 120)
        self.use_local = bool(use_local)
        if not self.use_local and not self.api_key:
            self.api_key = 'ollama'

    def _embed_one_batch(self, texts: list[str]) -> list[list[float]]:
        if self.use_local:
            return [_local_hash_embed(t) for t in texts]
        url = f'{self.base_url}/embeddings'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {'model': self.model, 'input': texts}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        items = sorted(data['data'], key=lambda x: x.get('index', 0))
        return [it['embedding'] for it in items]

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        text_list = list(texts)
        if not text_list:
            return []
        batches = [text_list[i : i + self.batch_size] for i in range(0, len(text_list), self.batch_size)]
        results: list[list[list[float]] | None] = [None] * len(batches)
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {pool.submit(self._embed_one_batch, batch): idx for idx, batch in enumerate(batches)}
            for fut in as_completed(futures):
                results[futures[fut]] = fut.result()
        vectors: list[list[float]] = []
        for part in results:
            assert part is not None
            vectors.extend(part)
        return vectors
