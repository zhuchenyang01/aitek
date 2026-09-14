from rag.models.embedding_client import EmbeddingClient
from rag.models.llm_client import LLMClient
from rag.models.rerank_client import RerankClient
from rag.models.vision_client import VisionClient

from .models import UserLLMConfig

OLLAMA_BASE_URL = 'http://127.0.0.1:11434/v1'

PROVIDER_PRESETS = {
    UserLLMConfig.PROVIDER_DEEPSEEK: {
        'base_url': 'https://api.deepseek.com/v1',
        'model': 'deepseek-chat',
    },
    UserLLMConfig.PROVIDER_OPENAI: {
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4o-mini',
    },
    UserLLMConfig.PROVIDER_QWEN: {
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model': 'qwen-plus',
    },
    UserLLMConfig.PROVIDER_MOONSHOT: {
        'base_url': 'https://api.moonshot.cn/v1',
        'model': 'moonshot-v1-8k',
    },
    UserLLMConfig.PROVIDER_ZHIPU: {
        'base_url': 'https://open.bigmodel.cn/api/paas/v4',
        'model': 'glm-4',
    },
    UserLLMConfig.PROVIDER_OLLAMA: {
        'base_url': OLLAMA_BASE_URL,
        'model': 'qwen2.5',
    },
    UserLLMConfig.PROVIDER_CUSTOM: {
        'base_url': '',
        'model': '',
    },
}

TYPE_DEFAULT_MODEL = {
    UserLLMConfig.TYPE_CHAT: 'deepseek-chat',
    UserLLMConfig.TYPE_EMBEDDING: 'bge-m3:latest',
    UserLLMConfig.TYPE_RERANK: 'rerank',
    UserLLMConfig.TYPE_VISION: 'gpt-4o',
    UserLLMConfig.TYPE_VOICE: 'whisper-1',
}


def mask_api_key(api_key):
    key = (api_key or '').strip()
    if not key:
        return ''
    if len(key) <= 8:
        return '****'
    return f'{key[:3]}****{key[-4:]}'


def is_local_source(config):
    return config.source == UserLLMConfig.SOURCE_OLLAMA or config.provider == UserLLMConfig.PROVIDER_OLLAMA


def apply_provider_defaults(attrs):
    model_type = attrs.get('model_type') or UserLLMConfig.TYPE_CHAT
    source = attrs.get('source') or UserLLMConfig.SOURCE_API
    if source == UserLLMConfig.SOURCE_OLLAMA:
        attrs['provider'] = UserLLMConfig.PROVIDER_OLLAMA
        if not (attrs.get('base_url') or '').strip():
            attrs['base_url'] = OLLAMA_BASE_URL
        if not (attrs.get('model') or '').strip():
            attrs['model'] = TYPE_DEFAULT_MODEL.get(model_type, 'qwen2.5')
        return attrs

    preset = PROVIDER_PRESETS.get(attrs.get('provider')) or {}
    if not (attrs.get('base_url') or '').strip() and preset.get('base_url'):
        attrs['base_url'] = preset['base_url']
    if not (attrs.get('model') or '').strip():
        attrs['model'] = preset.get('model') or TYPE_DEFAULT_MODEL.get(model_type, '')
    return attrs


def set_default_config(config):
    UserLLMConfig.objects.filter(
        user=config.user,
        model_type=config.model_type,
        is_default=True,
    ).exclude(pk=config.pk).update(is_default=False)
    if not config.is_default:
        config.is_default = True
        config.save(update_fields=['is_default', 'updated_at'])


def ensure_default(user, model_type=UserLLMConfig.TYPE_CHAT, exclude_id=None):
    queryset = UserLLMConfig.objects.filter(user=user, model_type=model_type)
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    if queryset.filter(is_default=True).exists():
        return
    next_config = queryset.first()
    if next_config:
        next_config.is_default = True
        next_config.save(update_fields=['is_default', 'updated_at'])


def _api_key_for_config(config):
    api_key = (config.api_key or '').strip()
    if not api_key and is_local_source(config):
        api_key = 'ollama'
    return api_key


def build_llm_client(config):
    return LLMClient(
        api_key=_api_key_for_config(config),
        base_url=(config.base_url or '').strip() or None,
        model=(config.model or '').strip() or None,
    )


def build_embedding_client(config):
    return EmbeddingClient(
        api_key=_api_key_for_config(config),
        base_url=(config.base_url or '').strip() or None,
        model=(config.model or '').strip() or None,
        use_local=False,
    )


def build_rerank_client(config, embedder=None):
    return RerankClient(
        api_key=_api_key_for_config(config),
        base_url=(config.base_url or '').strip() or None,
        model=(config.model or '').strip() or None,
        embedder=embedder,
    )


def build_vision_client(config):
    return VisionClient(
        api_key=_api_key_for_config(config),
        base_url=(config.base_url or '').strip() or None,
        model=(config.model or '').strip() or None,
    )


def _pick_config(queryset, config_id=None, required=False):
    if config_id not in (None, ''):
        config = queryset.filter(pk=config_id).first()
        if config is None and required:
            raise LookupError('模型配置不存在')
        return config
    return queryset.filter(is_default=True).first() or queryset.first()


def resolve_llm_client(user, llm_config_id=None):
    queryset = UserLLMConfig.objects.filter(user=user, model_type=UserLLMConfig.TYPE_CHAT)
    config = _pick_config(queryset, llm_config_id, required=llm_config_id not in (None, ''))
    if config is None:
        return None
    if config.model_type != UserLLMConfig.TYPE_CHAT:
        raise LookupError('所选配置不是对话模型')
    return build_llm_client(config)


def resolve_embedding_client(user, config_id=None):
    queryset = UserLLMConfig.objects.filter(user=user, model_type=UserLLMConfig.TYPE_EMBEDDING)
    config = _pick_config(queryset, config_id, required=config_id not in (None, ''))
    if config is None:
        return None
    return build_embedding_client(config)


def resolve_rerank_client(user, config_id=None):
    embedder = resolve_embedding_client(user)
    queryset = UserLLMConfig.objects.filter(user=user, model_type=UserLLMConfig.TYPE_RERANK)
    config = _pick_config(queryset, config_id, required=config_id not in (None, ''))
    if config is None:
        return RerankClient(embedder=embedder)
    return build_rerank_client(config, embedder=embedder)


def resolve_vision_client(user, config_id=None):
    queryset = UserLLMConfig.objects.filter(user=user, model_type=UserLLMConfig.TYPE_VISION)
    config = _pick_config(queryset, config_id, required=config_id not in (None, ''))
    if config is None:
        return None
    if config.model_type != UserLLMConfig.TYPE_VISION:
        raise LookupError('所选配置不是视觉模型')
    return build_vision_client(config)


def test_model_connection(config):
    if config.model_type == UserLLMConfig.TYPE_CHAT:
        client = build_llm_client(config)
        answer = client.chat([{'role': 'user', 'content': 'ping'}], temperature=0, max_tokens=8)
        return {'ok': True, 'message': '连接成功', 'sample': (answer or '')[:80]}

    if config.model_type == UserLLMConfig.TYPE_EMBEDDING:
        client = build_embedding_client(config)
        vectors = client.embed_batch(['连接测试'])
        if not vectors:
            raise RuntimeError('未返回向量')
        dimension = len(vectors[0])
        config.dimension = dimension
        if config.pk:
            config.save(update_fields=['dimension', 'updated_at'])
        return {'ok': True, 'message': f'连接成功，向量维度 {dimension}', 'dimension': dimension}

    if config.model_type == UserLLMConfig.TYPE_RERANK:
        client = build_rerank_client(config, embedder=resolve_embedding_client(config.user))
        ranked = client.rerank(
            '连接测试',
            [{'content': '示例文档 A'}, {'content': '示例文档 B'}],
            top_k=1,
            text_key='content',
        )
        if not ranked:
            raise RuntimeError('Rerank 未返回结果')
        return {'ok': True, 'message': '连接成功', 'sample_score': ranked[0].get('rerank_score')}

    if config.model_type in (UserLLMConfig.TYPE_VISION, UserLLMConfig.TYPE_VOICE):
        client = build_llm_client(config)
        client.chat([{'role': 'user', 'content': 'ping'}], temperature=0, max_tokens=8)
        return {'ok': True, 'message': '接口可达（按 OpenAI 兼容接口校验）'}

    raise RuntimeError('不支持的模型类型')
