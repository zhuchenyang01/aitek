"""JSONL / Markdown 存储：[id, 功能点, 向量数组]。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def save_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[JSONL] 已写入: {path}")


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    print(f"[JSONL] 已读取 {len(rows)} 行: {path}")
    return rows


def export_features_md(path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# 功能点清单\n"]
    for row in rows:
        rid = row.get("id", "")
        feature = row.get("feature", "")
        module = row.get("module", "")
        lines.append(f"- `{rid}` [{module}] {feature}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[MD] 已导出: {path}")
