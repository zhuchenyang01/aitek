"""Step1: 读取需求文档，分离文字与图片。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from rag import config
from rag.loaders.document_loader import load_document
from rag.utils.timing import timed


@timed("step1_parse_document")
def run(doc_path: str | Path) -> list[dict[str, Any]]:
    print("=" * 60)
    print("Step1 解析文档：分离文字 / 图片")
    print("=" * 60)
    config.ensure_dirs()
    blocks = load_document(doc_path, config.IMAGE_DIR)
    for b in blocks[:8]:
        preview = (b.get("content") or b.get("path") or "")[:80]
        print(f"  - [{b['order']}] type={b['type']} page={b.get('page')} | {preview}")
    if len(blocks) > 8:
        print(f"  ... 其余 {len(blocks) - 8} 块省略")
    return blocks
