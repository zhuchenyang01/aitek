"""Step7: 循环所有功能点，找出每个功能点关联的功能点。"""
from __future__ import annotations

import json
from typing import Any

from rag import config
from rag.store.faiss_store import FaissStore
from rag.utils.timing import timed


@timed("step7_associate_retrieve")
def run(
    feature_rows: list[dict[str, Any]],
    store: FaissStore,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    print("=" * 60)
    print("Step7 循环功能点：检索关联功能点")
    print("=" * 60)
    top_k = top_k or config.RETRIEVE_TOP_K
    id_to_row = {r["id"]: r for r in feature_rows}
    associations: list[dict[str, Any]] = []

    for row in feature_rows:
        # 多取 1 个以便排除自身
        hits = store.search(row["vector"], top_k=top_k + 1)
        related = []
        for rid, score in hits:
            if rid == row["id"]:
                continue
            other = id_to_row.get(rid)
            if not other:
                continue
            related.append(
                {
                    "id": rid,
                    "module": other.get("module", ""),
                    "feature": other.get("feature", ""),
                    "score": score,
                }
            )
            if len(related) >= top_k:
                break
        associations.append(
            {
                "id": row["id"],
                "module": row.get("module", ""),
                "feature": row.get("feature", ""),
                "related": related,
            }
        )
        print(f"  {row['id']} 关联 {len(related)} 条")

    config.ASSOC_JSON.write_text(
        json.dumps(associations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[Step7] 已写入: {config.ASSOC_JSON}")
    return associations
