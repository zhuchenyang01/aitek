"""Step5: 对话模型提炼独立模块与功能点。"""
from __future__ import annotations

import json
import re
from typing import Any

from rag.models.llm_client import LLMClient
from rag.utils.timing import timed

EXTRACT_PROMPT = """你是资深测试架构师。请从需求纯文本中提炼「独立模块」和「功能点」。
只输出 JSON 数组，不要其它说明。每项格式：
{"module": "模块名", "feature": "功能点描述"}

要求：
1. 功能点尽量原子、可测试
2. 不要编造原文没有的能力
3. 数量控制在 5~30 条

需求文本：
"""


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    # 提取 ```json ... ``` 或 首个 [...]
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("期望 JSON 数组")
    return data


def _fallback_features(pure_text: str) -> list[dict[str, Any]]:
    """无 API 时按段落粗分功能点，保证流程可演示。"""
    paras = [p.strip() for p in re.split(r"\n{2,}", pure_text) if p.strip()]
    rows = []
    for i, p in enumerate(paras[:20]):
        rows.append({"module": "未分类", "feature": p[:200]})
    if not rows:
        rows = [{"module": "未分类", "feature": pure_text[:200] or "空文档"}]
    print(f"[Step5] 降级：按段落生成 {len(rows)} 条功能点")
    return rows


@timed("step5_extract_features")
def run(pure_text: str) -> list[dict[str, Any]]:
    print("=" * 60)
    print("Step5 对话模型：提炼模块 / 功能点")
    print("=" * 60)
    # 过长则截断，避免超上下文
    content = pure_text if len(pure_text) <= 12000 else pure_text[:12000] + "\n...(截断)"
    try:
        llm = LLMClient()
        raw = llm.chat(
            [
                {"role": "system", "content": "你只输出合法 JSON 数组。"},
                {"role": "user", "content": EXTRACT_PROMPT + content},
            ],
            temperature=0.1,
        )
        items = _parse_json_array(raw)
    except Exception as exc:  # noqa: BLE001
        print(f"[Step5] LLM 抽取失败，降级: {exc}")
        items = _fallback_features(pure_text)

    features: list[dict[str, Any]] = []
    for i, it in enumerate(items):
        module = str(it.get("module") or "未分类").strip()
        feature = str(it.get("feature") or "").strip()
        if not feature:
            continue
        features.append(
            {
                "id": f"fp_{i:04d}",
                "module": module,
                "feature": feature,
            }
        )
    print(f"[Step5] 功能点数={len(features)}")
    for f in features[:5]:
        print(f"  - {f['id']} [{f['module']}] {f['feature'][:60]}")
    return features
