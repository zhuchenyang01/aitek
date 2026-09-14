"""Step2: 视觉模型把图片转成文字（去噪音）。"""
from __future__ import annotations

from typing import Any

from rag.models.vision_client import VisionClient
from rag.utils.timing import timed


@timed("step2_vision_to_text")
def run(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    print("=" * 60)
    print("Step2 视觉模型：图片 -> 文字（无噪音）")
    print("=" * 60)
    vision = VisionClient()
    out: list[dict[str, Any]] = []
    for b in blocks:
        if b["type"] != "image":
            out.append(dict(b))
            continue
        text = vision.image_to_text(b["path"])
        item = dict(b)
        item["type"] = "image_text"
        item["content"] = text
        out.append(item)
        print(f"  图片已转写: {b.get('path')} -> {len(text)} 字")
    return out
