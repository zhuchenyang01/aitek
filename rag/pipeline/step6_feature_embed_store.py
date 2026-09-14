"""Step6: 功能点转向量，写入 FAISS + jsonl/md。"""
from __future__ import annotations

from typing import Any

from rag import config
from rag.models.embedding_client import EmbeddingClient
from rag.store.faiss_store import FaissStore
from rag.store.jsonl_store import export_features_md, save_jsonl
from rag.utils.timing import timed


@timed("step6_feature_embed_store")
def run(features: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], FaissStore]:
    print("=" * 60)
    print("Step6 功能点转向量 -> FAISS / jsonl / md")
    print("=" * 60)
    config.ensure_dirs()
    if not features:
        raise ValueError("功能点为空，无法建库")

    texts = [f["feature"] for f in features]
    ids = [f["id"] for f in features]
    embedder = EmbeddingClient()
    vectors = embedder.embed_batch(texts)

    rows: list[dict[str, Any]] = []
    for f, vec in zip(features, vectors):
        rows.append(
            {
                "id": f["id"],
                "module": f.get("module", ""),
                "feature": f["feature"],
                "vector": vec,
            }
        )

    save_jsonl(config.FEATURE_JSONL, rows)
    export_features_md(config.FEATURE_MD, rows)

    store = FaissStore()
    store.build(ids, vectors)
    store.save(config.FAISS_INDEX_PATH, config.FAISS_IDS_PATH)
    print(f"[Step6] 完成: faiss={config.FAISS_INDEX_PATH}, jsonl={config.FEATURE_JSONL}")
    return rows, store
