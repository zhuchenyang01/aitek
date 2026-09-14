import base64
import mimetypes
from pathlib import Path

import httpx


class VisionClient:
    def __init__(self, api_key='', base_url=None, model=None, timeout=120.0, prompt=''):
        self.api_key = api_key or ''
        self.base_url = (base_url or 'https://api.openai.com/v1').rstrip('/')
        self.model = model or 'gpt-4o'
        self.timeout = float(timeout or 120)
        self.prompt = prompt or '请分析图片中的业务交互规则。'

    @property
    def enabled(self):
        return bool(self.api_key)

    def _data_url(self, image_path: Path) -> str:
        mime, _ = mimetypes.guess_type(str(image_path))
        mime = mime or 'image/png'
        b64 = base64.b64encode(image_path.read_bytes()).decode('ascii')
        return f'data:{mime};base64,{b64}'

    def analyze_image(self, image_path, extra_context=''):
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(path)
        if not self.enabled:
            return f'[视觉降级] 未配置视觉模型，跳过图片分析: {path.name}'

        prompt = self.prompt
        if extra_context:
            prompt = f'{prompt}\n\n补充上下文：{extra_context}'

        url = f'{self.base_url}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {'type': 'image_url', 'image_url': {'url': self._data_url(path)}},
                    ],
                }
            ],
            'temperature': 0.1,
            'max_tokens': 1024,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            return (data['choices'][0]['message']['content'] or '').strip()
        except Exception as exc:
            return f'[视觉降级] 调用失败({exc})，文件={path.name}'
