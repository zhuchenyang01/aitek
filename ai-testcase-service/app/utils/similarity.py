from typing import Sequence

import numpy as np


def batch_cosine(query: Sequence[float], matrix: np.ndarray) -> np.ndarray:
    q = np.asarray(query, dtype=np.float32)
    m = np.asarray(matrix, dtype=np.float32)
    if m.ndim != 2:
        raise ValueError('matrix 需为二维 [N, D]')
    if q.ndim != 1 or q.shape[0] != m.shape[1]:
        raise ValueError(
            f'向量维度不一致：查询 {int(q.shape[0]) if q.ndim == 1 else q.shape}，'
            f'知识库 {int(m.shape[1]) if m.ndim == 2 else m.shape}。'
            '请使用与入库时相同的 Embedding 模型，或重新入库需求文档。'
        )
    q_norm = np.linalg.norm(q)
    m_norm = np.linalg.norm(m, axis=1)
    denom = q_norm * m_norm
    dots = m @ q
    out = np.zeros(m.shape[0], dtype=np.float32)
    mask = denom > 0
    out[mask] = dots[mask] / denom[mask]
    return out
