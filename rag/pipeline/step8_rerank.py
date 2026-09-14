"""Step8: rerank 重排关联结果。"""
from __future__ import annotations

import json
from typing import Any

from rag import config
from rag.models.rerank_client import RerankClient
from rag.utils.timing import timed


@timed("step8_rerank")
def run(associations: list[dict[str, Any]], top_k: int | None = None) -> list[dict[str, Any]]:
    print("=" * 60)
    print("Step8 Rerank 重排")
    print("=" * 60)
    top_k = top_k or config.RERANK_TOP_K
    reranker = RerankClient()
    reranked: list[dict[str, Any]] = []

    for item in associations:
        query = item["feature"]
        docs = item.get("related") or []
        if not docs:
            reranked.append({**item, "related": []})
            continue
        ranked = reranker.rerank(query, docs, top_k=top_k, text_key="feature")
        reranked.append({**item, "related": ranked})
        print(f"  {item['id']} rerank -> {len(ranked)} 条")

    config.RERANK_JSON.write_text(
        json.dumps(reranked, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[Step8] 已写入: {config.RERANK_JSON}")
    return reranked
