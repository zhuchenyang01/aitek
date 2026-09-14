"""Step3: 合并为纯文字文档。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from rag import config
from rag.utils.timing import timed


@timed("step3_merge_pure_text")
def run(blocks: list[dict[str, Any]], out_path: str | Path | None = None) -> str:
    print("=" * 60)
    print("Step3 合并纯文本文档")
    print("=" * 60)
    config.ensure_dirs()
    parts: list[str] = []
    for b in sorted(blocks, key=lambda x: x.get("order", 0)):
        content = (b.get("content") or "").strip()
        if not content:
            continue
        if b.get("type") == "image_text":
            parts.append(f"\n## [图片转写 p{b.get('page')}]\n{content}\n")
        else:
            parts.append(content)
    pure = "\n\n".join(parts).strip() + "\n"
    path = Path(out_path or config.PURE_TEXT_PATH)
    path.write_text(pure, encoding="utf-8")
    print(f"[Step3] 纯文本已写入: {path} | 字数={len(pure)}")
    return pure
