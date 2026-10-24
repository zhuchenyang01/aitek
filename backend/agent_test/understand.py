"""从 Agent 代码目录抽取上下文，调用对话模型生成项目理解文案。"""

from __future__ import annotations

import os
from pathlib import Path

SKIP_DIRS = {
    '.git',
    '.svn',
    '.hg',
    '__pycache__',
    '.venv',
    'venv',
    'node_modules',
    '.idea',
    '.vscode',
    'dist',
    'build',
    '.pytest_cache',
    '.mypy_cache',
}

CODE_SUFFIXES = {'.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml'}
MAX_FILES = 24
MAX_FILE_CHARS = 6000
MAX_TOTAL_CHARS = 48000

UNDERSTAND_PROMPT = """你是资深 AI Agent / 测试架构师。请根据以下代码与文档，输出一份可直接用于测试设计的「项目理解」文案。

要求：
1. 使用中文 Markdown。
2. 结构固定为以下章节（有则写，无则写「暂无」）：
   - 项目定位
   - 核心能力
   - 主要模块与职责
   - 对外交互（API / 工具 / 数据源）
   - 关键输入输出与约束
   - 测试关注点（功能、异常、集成）
3. 依据代码事实，不要编造不存在的能力。
4. 控制在 800～1500 字。

项目名称：{name}
项目路径：{path}

代码摘录：
{context}
"""


def collect_project_context(project_path: str) -> str:
    root = Path(project_path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f'项目路径不存在：{project_path}')
    if not root.is_dir():
        raise NotADirectoryError(f'项目路径不是目录：{project_path}')

    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.startswith('.')]
        for filename in filenames:
            suffix = Path(filename).suffix.lower()
            if suffix not in CODE_SUFFIXES:
                continue
            full = Path(dirpath) / filename
            try:
                if full.stat().st_size > 512 * 1024:
                    continue
            except OSError:
                continue
            files.append(full)

    files.sort(key=lambda item: (0 if item.name.lower().startswith('readme') else 1, str(item)))
    chunks = []
    total = 0
    for path in files[:MAX_FILES]:
        try:
            text = path.read_text(encoding='utf-8', errors='ignore').strip()
        except OSError:
            continue
        if not text:
            continue
        rel = path.relative_to(root).as_posix()
        body = text[:MAX_FILE_CHARS]
        piece = f'### 文件: {rel}\n```\n{body}\n```\n'
        if total + len(piece) > MAX_TOTAL_CHARS:
            break
        chunks.append(piece)
        total += len(piece)

    if not chunks:
        raise ValueError('目录下未找到可读的代码或文档（支持 .py/.md/.txt/.json/.yaml）')
    return '\n'.join(chunks)


def generate_understanding(llm, *, name: str, path: str) -> str:
    context = collect_project_context(path)
    prompt = UNDERSTAND_PROMPT.format(name=name, path=path, context=context)
    answer = llm.chat(
        [{'role': 'user', 'content': prompt}],
        temperature=0.2,
        max_tokens=4096,
    )
    text = (answer or '').strip()
    if not text:
        raise ValueError('模型未返回有效理解文案')
    return text
