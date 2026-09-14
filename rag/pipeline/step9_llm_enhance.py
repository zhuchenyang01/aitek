"""Step9: LLM 做增强（基于关联/重排上下文）。"""
from __future__ import annotations

from typing import Any

from rag import config
from rag.models.llm_client import LLMClient
from rag.utils.timing import timed


def _build_context(reranked: list[dict[str, Any]], limit: int = 15) -> str:
    lines: list[str] = []
    for item in reranked[:limit]:
        lines.append(f"### 功能点 {item['id']} [{item.get('module','')}]")
        lines.append(item.get("feature", ""))
        related = item.get("related") or []
        if related:
            lines.append("关联功能点：")
            for r in related:
                score = r.get("rerank_score", r.get("score", ""))
                lines.append(f"- {r.get('id')} (score={score}): {r.get('feature','')}")
        lines.append("")
    return "\n".join(lines)


@timed("step9_llm_enhance")
def run(
    reranked: list[dict[str, Any]],
    task: str = "请基于以上功能点与关联关系，输出：1) 模块划分建议 2) 高优先级测试点 3) 风险提示。用中文简洁条目。",
) -> str:
    print("=" * 60)
    print("Step9 LLM 增强生成")
    print("=" * 60)
    context = _build_context(reranked)
    try:
        llm = LLMClient()
        result = llm.chat(
            [
                {
                    "role": "system",
                    "content": "你是 AI 测试专家，根据检索到的功能点做增强分析。",
                },
                {
                    "role": "user",
                    "content": f"{task}\n\n---\n上下文：\n{context}",
                },
            ],
            temperature=0.3,
        )
    except Exception as exc:  # noqa: BLE001
        result = (
            f"[LLM 降级] 无法调用对话 API: {exc}\n\n"
            f"已汇总 {len(reranked)} 个功能点及其关联，请配置 DEEPSEEK_API_KEY 后重试增强生成。\n"
        )
        print(result)

    config.ENHANCE_MD.write_text(result, encoding="utf-8")
    print(f"[Step9] 增强结果已写入: {config.ENHANCE_MD}")
    print(result[:500] + ("..." if len(result) > 500 else ""))
    return result
