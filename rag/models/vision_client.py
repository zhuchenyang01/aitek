"""视觉模型：图片转文字（OpenAI 兼容 vision / 多模态 chat）。"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import httpx

from rag import config
from rag.utils.timing import timed

VISION_PROMPT = (
    "你是需求分析助手。请把图片中的需求相关内容转成清晰中文文字。"
    "只保留与业务功能、流程、字段、规则相关的信息，不要噪音："
    "不要描述装饰性背景、不要猜测无关细节、不要输出 markdown 花哨格式。"
    "若图中是表格/流程图，用简洁条目复述。"
)


class VisionClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else config.VISION_API_KEY
        self.base_url = (base_url or config.VISION_BASE_URL).rstrip("/")
        self.model = model or config.VISION_MODEL
        self.timeout = timeout or config.HTTP_TIMEOUT

    def _data_url(self, image_path: Path) -> str:
        mime, _ = mimetypes.guess_type(str(image_path))
        mime = mime or "image/png"
        b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"

    @timed("vision.image_to_text")
    def image_to_text(self, image_path: str | Path) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(path)
        if not self.api_key:
            # 无密钥时降级：返回占位说明，保证流水线可跑通结构
            msg = f"[视觉降级] 未配置 VISION_API_KEY，跳过图片转写: {path.name}"
            print(msg)
            return msg

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": self._data_url(path)},
                        },
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1024,
        }
        print(f"[Vision] 转写图片: {path.name}")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            print(f"[Vision] 完成: {path.name}, 字数={len(text)}")
            return text
        except Exception as exc:  # noqa: BLE001
            # 部分模型不支持 vision，降级
            msg = f"[视觉降级] 调用失败({exc})，文件={path.name}"
            print(msg)
            return msg
