"""RAG 框架全局配置（无 LangChain）。"""
from __future__ import annotations

import os
from pathlib import Path

# 项目根：rag/
RAG_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", RAG_ROOT / "data"))
IMAGE_DIR = DATA_DIR / "images"
PURE_TEXT_PATH = DATA_DIR / "pure_text.md"
CHUNK_JSONL = DATA_DIR / "chunks.jsonl"
FEATURE_JSONL = DATA_DIR / "features.jsonl"
FEATURE_MD = DATA_DIR / "features.md"
FAISS_INDEX_PATH = DATA_DIR / "features.faiss"
FAISS_IDS_PATH = DATA_DIR / "features_ids.json"
ASSOC_JSON = DATA_DIR / "associations.json"
RERANK_JSON = DATA_DIR / "reranked.json"
ENHANCE_MD = DATA_DIR / "llm_enhance.md"

# DeepSeek 对话
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_CHAT_MODEL = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")

# 向量 / 视觉 / Rerank
# 默认使用本机 Ollama 的 bge-m3（与 WeKnora 配置一致，1024 维）
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "http://127.0.0.1:11434/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3:latest")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "16"))
EMBEDDING_CONCURRENCY = int(os.getenv("EMBEDDING_CONCURRENCY", "4"))
EMBEDDING_USE_LOCAL = os.getenv("EMBEDDING_USE_LOCAL", "").lower() in ("1", "true", "yes")

VISION_API_KEY = os.getenv("VISION_API_KEY", DEEPSEEK_API_KEY)
VISION_BASE_URL = os.getenv("VISION_BASE_URL", DEEPSEEK_BASE_URL)
VISION_MODEL = os.getenv("VISION_MODEL", "deepseek-chat")

RERANK_API_KEY = os.getenv("RERANK_API_KEY", "")
RERANK_BASE_URL = os.getenv("RERANK_BASE_URL", "")
RERANK_MODEL = os.getenv("RERANK_MODEL", "rerank")

# 分块 / 检索
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))
RETRIEVE_TOP_K = int(os.getenv("RAG_RETRIEVE_TOP_K", "5"))
RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "3"))

HTTP_TIMEOUT = float(os.getenv("RAG_HTTP_TIMEOUT", "120"))


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
