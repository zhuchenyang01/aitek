from pathlib import Path

from app.clients.vision_client import VisionClient
from app.utils.prompt_loader import render_prompt


def build_vision_client(vision_config=None):
    config = vision_config or {}
    prompt = render_prompt('image_analysis', extra_context='')
    return VisionClient(
        api_key=config.get('api_key') or '',
        base_url=config.get('base_url'),
        model=config.get('model'),
        timeout=config.get('timeout', 120),
        prompt=prompt,
    )


def analyze_images(blocks, vision_config=None):
    client = build_vision_client(vision_config)
    image_blocks = [block for block in (blocks or []) if block.get('type') == 'image' and block.get('path')]
    if not image_blocks:
        return {'insights': [], 'appendix_text': '', 'skipped': False, 'reason': '文档无图片'}

    if not client.enabled:
        return {
            'insights': [],
            'appendix_text': '',
            'skipped': True,
            'reason': '未配置视觉模型，已跳过图片理解',
        }

    insights = []
    lines = []
    for index, block in enumerate(image_blocks, start=1):
        order = block.get('order', index)
        page = block.get('page')
        page_hint = f'page={page}' if page else 'page=未知'
        extra = f'图片序号={index}，文档顺序 order={order}，{page_hint}'
        text = client.analyze_image(block['path'], extra_context=extra)
        insight = {
            'index': index,
            'order': order,
            'page': page,
            'path': block['path'],
            'analysis': text,
        }
        insights.append(insight)
        lines.append(f'[图片{index}@order={order}] {text}')

    return {
        'insights': insights,
        'appendix_text': '\n\n'.join(lines),
        'skipped': False,
        'reason': '',
    }


def merge_document_text(blocks, image_result):
    parts = []
    for block in blocks or []:
        if block.get('type') == 'text' and block.get('content'):
            parts.append(block['content'])
    appendix = (image_result or {}).get('appendix_text') or ''
    if appendix:
        parts.append('\n\n【图片理解附录】\n' + appendix)
    return '\n\n'.join(parts)
