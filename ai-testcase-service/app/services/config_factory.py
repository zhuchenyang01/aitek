from app.clients.embedding_client import EmbeddingClient
from app.clients.llm_client import LLMClient
from app.clients.rerank_client import RerankClient
from app.clients.vision_client import VisionClient


def build_llm_client(config=None):
    config = config or {}
    return LLMClient(
        api_key=config.get('api_key') or '',
        base_url=config.get('base_url'),
        model=config.get('model'),
        timeout=config.get('timeout', 120),
    )


def build_embedding_client(config=None):
    config = config or {}
    return EmbeddingClient(
        api_key=config.get('api_key') or '',
        base_url=config.get('base_url'),
        model=config.get('model'),
        timeout=config.get('timeout', 120),
        use_local=bool(config.get('use_local')),
    )


def build_rerank_client(config=None, embedder=None):
    config = config or {}
    return RerankClient(
        api_key=config.get('api_key') or '',
        base_url=config.get('base_url'),
        model=config.get('model'),
        timeout=config.get('timeout', 120),
        embedder=embedder or build_embedding_client(config.get('embedding_config')),
    )


def build_vision_client(config=None):
    config = config or {}
    return VisionClient(
        api_key=config.get('api_key') or '',
        base_url=config.get('base_url'),
        model=config.get('model'),
        timeout=config.get('timeout', 120),
    )
