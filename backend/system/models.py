from django.conf import settings
from django.db import models


class UserLLMConfig(models.Model):
    TYPE_CHAT = 'chat'
    TYPE_EMBEDDING = 'embedding'
    TYPE_RERANK = 'rerank'
    TYPE_VISION = 'vision'
    TYPE_VOICE = 'voice'
    TYPE_CHOICES = (
        (TYPE_CHAT, '对话'),
        (TYPE_EMBEDDING, 'Embedding'),
        (TYPE_RERANK, 'ReRank'),
        (TYPE_VISION, '视觉'),
        (TYPE_VOICE, '语音'),
    )

    SOURCE_API = 'api'
    SOURCE_OLLAMA = 'ollama'
    SOURCE_CHOICES = (
        (SOURCE_API, 'API'),
        (SOURCE_OLLAMA, 'Ollama'),
    )

    PROVIDER_DEEPSEEK = 'deepseek'
    PROVIDER_OPENAI = 'openai'
    PROVIDER_QWEN = 'qwen'
    PROVIDER_MOONSHOT = 'moonshot'
    PROVIDER_ZHIPU = 'zhipu'
    PROVIDER_OLLAMA = 'ollama'
    PROVIDER_CUSTOM = 'custom'
    PROVIDER_CHOICES = (
        (PROVIDER_DEEPSEEK, 'DeepSeek'),
        (PROVIDER_OPENAI, 'OpenAI'),
        (PROVIDER_QWEN, '通义千问'),
        (PROVIDER_MOONSHOT, 'Moonshot'),
        (PROVIDER_ZHIPU, '智谱 GLM'),
        (PROVIDER_OLLAMA, 'Ollama'),
        (PROVIDER_CUSTOM, '自定义 OpenAI 兼容'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='llm_configs',
        verbose_name='用户',
    )
    model_type = models.CharField('模型类型', max_length=16, choices=TYPE_CHOICES, default=TYPE_CHAT)
    source = models.CharField('模型来源', max_length=16, choices=SOURCE_CHOICES, default=SOURCE_API)
    name = models.CharField('显示名称', max_length=128)
    provider = models.CharField('提供商', max_length=32, choices=PROVIDER_CHOICES)
    model = models.CharField('模型名', max_length=128)
    base_url = models.CharField('接口地址', max_length=512)
    api_key = models.CharField('API Key', max_length=512, blank=True, default='')
    dimension = models.PositiveIntegerField('向量维度', null=True, blank=True)
    is_default = models.BooleanField('默认模型', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'system_user_llm_config'
        ordering = ['-is_default', '-id']
        verbose_name = '用户模型配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.name}({self.model})'
