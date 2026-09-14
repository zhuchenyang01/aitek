"""距离相似度 / 余弦相似度：math 单条 + numpy 批量。"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def euclidean_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """欧氏距离（math 实现）。"""
    if len(a) != len(b):
        raise ValueError("向量维度不一致")
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """余弦相似度（math 实现），范围约 [-1, 1]。"""
    if len(a) != len(b):
        raise ValueError("向量维度不一致")
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    na = math.sqrt(sum(float(x) ** 2 for x in a))
    nb = math.sqrt(sum(float(y) ** 2 for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def batch_euclidean(query: Sequence[float], matrix: np.ndarray) -> np.ndarray:
    """批量欧氏距离：query[D] vs matrix[N, D] -> [N]。"""
    q = np.asarray(query, dtype=np.float32)
    m = np.asarray(matrix, dtype=np.float32)
    if m.ndim != 2:
        raise ValueError("matrix 需为二维 [N, D]")
    diff = m - q.reshape(1, -1)
    return np.sqrt(np.sum(diff * diff, axis=1))


def batch_cosine(query: Sequence[float], matrix: np.ndarray) -> np.ndarray:
    """批量余弦相似度：query[D] vs matrix[N, D] -> [N]。"""
    q = np.asarray(query, dtype=np.float32)
    m = np.asarray(matrix, dtype=np.float32)
    if m.ndim != 2:
        raise ValueError("matrix 需为二维 [N, D]")
    q_norm = np.linalg.norm(q)
    m_norm = np.linalg.norm(m, axis=1)
    denom = q_norm * m_norm
    dots = m @ q
    out = np.zeros(m.shape[0], dtype=np.float32)
    mask = denom > 0
    out[mask] = dots[mask] / denom[mask]
    return out


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """行向量 L2 归一化，便于 FAISS 内积近似余弦。"""
    v = np.asarray(vectors, dtype=np.float32)
    if v.ndim == 1:
        n = np.linalg.norm(v)
        return v if n == 0 else v / n
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return v / norms


if __name__ == "__main__":
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    c = [0.0, 1.0, 0.0]
    print("euclidean a-b", euclidean_distance(a, b))
    print("cosine a-b", cosine_similarity(a, b))
    print("cosine a-c", cosine_similarity(a, c))
    mat = np.array([b, c], dtype=np.float32)
    print("batch_euclidean", batch_euclidean(a, mat))
    print("batch_cosine", batch_cosine(a, mat))
