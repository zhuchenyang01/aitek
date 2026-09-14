from typing import Any

import httpx
import numpy as np

from app.clients.embedding_client import EmbeddingClient
from app.utils.similarity import batch_cosine


class RerankClient:
    def __init__(self, api_key='', base_url=None, model=None, timeout=120.0, embedder=None):
        self.api_key = api_key or ''
        self.base_url = (base_url or '').rstrip('/')
        self.model = model or 'rerank'
        self.timeout = float(timeout or 120)
        self.embedder = embedder

    def rerank(self, query, documents, top_k=3, text_key='content'):
        if not documents:
            return []
        if self.api_key and self.base_url:
            try:
                return self._http_rerank(query, documents, top_k, text_key)
            except Exception:
                pass
        return self._local_cosine_rerank(query, documents, top_k, text_key)

    def _http_rerank(self, query, documents, top_k, text_key):
        url = f'{self.base_url}/rerank'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': self.model,
            'query': query,
            'documents': [d.get(text_key, '') for d in documents],
            'top_n': top_k,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        results = data.get('results') or data.get('data') or []
        ranked = []
        for item in results:
            idx = item.get('index', item.get('idx'))
            score = item.get('relevance_score', item.get('score', 0.0))
            if idx is None:
                continue
            row = dict(documents[int(idx)])
            row['rerank_score'] = float(score)
            ranked.append(row)
        ranked.sort(key=lambda x: x.get('rerank_score', 0.0), reverse=True)
        return ranked[:top_k]

    def _local_cosine_rerank(self, query, documents, top_k, text_key):
        embedder = self.embedder or EmbeddingClient()
        texts = [str(d.get(text_key, '')) for d in documents]
        q_vec = embedder.embed_batch([query])[0]
        doc_vecs = embedder.embed_batch(texts)
        matrix = np.asarray(doc_vecs, dtype=np.float32)
        scores = batch_cosine(q_vec, matrix)
        ranked = []
        for i, doc in enumerate(documents):
            row = dict(doc)
            row['rerank_score'] = float(scores[i])
            ranked.append(row)
        ranked.sort(key=lambda x: x.get('rerank_score', 0.0), reverse=True)
        return ranked[:top_k]
