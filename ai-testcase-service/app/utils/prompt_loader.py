import json
from functools import lru_cache
from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parents[1] / 'prompts'


@lru_cache(maxsize=16)
def load_prompt(name):
    path = PROMPTS_DIR / f'{name}.json'
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def render_prompt(name, **kwargs):
    data = load_prompt(name)
    template = data.get('prompt_template') or ''
    rendered = template
    for key, value in kwargs.items():
        rendered = rendered.replace('{' + key + '}', str(value))
    return rendered
