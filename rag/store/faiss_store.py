"""FAISS 向量库：[id, vector]。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import faiss
import numpy as np

from rag.utils.similarity import l2_normalize
from rag.utils.timing import timed


class FaissStore:
    def __init__(self) -> None:
        self.index: faiss.Index | None = None
        self.ids: list[str] = []

    @timed("faiss.build")
    def build(self, ids: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
        if len(ids) != len(vectors):
            raise ValueError("ids 与 vectors 数量不一致")
        if not ids:
            self.index = None
            self.ids = []
            return
        mat = l2_normalize(np.asarray(vectors, dtype=np.float32))
        dim = mat.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(mat)
        self.ids = list(ids)
        print(f"[FAISS] 构建完成 n={len(ids)} dim={dim}")

    @timed("faiss.search")
    def search(self, query_vector: Sequence[float], top_k: int = 5) -> list[tuple[str, float]]:
        if self.index is None or not self.ids:
            return []
        q = l2_normalize(np.asarray(query_vector, dtype=np.float32)).reshape(1, -1)
        k = min(top_k, len(self.ids))
        scores, indices = self.index.search(q, k)
        out: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            out.append((self.ids[int(idx)], float(score)))
        return out

    def save(self, index_path: str | Path, ids_path: str | Path) -> None:
        index_path = Path(index_path)
        ids_path = Path(ids_path)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        if self.index is None:
            raise RuntimeError("index 为空，无法保存")
        faiss.write_index(self.index, str(index_path))
        ids_path.write_text(json.dumps(self.ids, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[FAISS] 已保存: {index_path}, {ids_path}")

    def load(self, index_path: str | Path, ids_path: str | Path) -> None:
        self.index = faiss.read_index(str(index_path))
        self.ids = json.loads(Path(ids_path).read_text(encoding="utf-8"))
        print(f"[FAISS] 已加载 n={len(self.ids)}")
