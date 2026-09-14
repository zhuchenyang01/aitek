from django.conf import settings
from django.db import models


class KnowledgeBase(models.Model):
    TYPE_REQUIREMENT = 'requirement'
    TYPE_TESTCASE = 'testcase'
    TYPE_CHOICES = (
        (TYPE_REQUIREMENT, '需求文档知识库'),
        (TYPE_TESTCASE, '测试用例知识库'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_testcase_knowledge_bases',
        verbose_name='用户',
    )
    name = models.CharField('名称', max_length=255)
    description = models.TextField('描述', blank=True, default='')
    kb_type = models.CharField('类型', max_length=32, choices=TYPE_CHOICES)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'ai_testcase_knowledge_base'
        ordering = ['-id']
        verbose_name = '知识库'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.name}({self.kb_type})'


class KnowledgeDocument(models.Model):
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='知识库',
    )
    title = models.CharField('标题', max_length=255, blank=True, default='')
    source_filename = models.CharField('源文件名', max_length=255, blank=True, default='')
    content = models.TextField('正文')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'ai_testcase_knowledge_document'
        ordering = ['-id']
        verbose_name = '知识文档'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title or f'文档#{self.id}'


class KnowledgeChunk(models.Model):
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name='知识库',
    )
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name='文档',
    )
    content = models.TextField('分块内容')
    vector = models.JSONField('向量', default=list)
    chunk_index = models.PositiveIntegerField('分块序号', default=0)

    class Meta:
        db_table = 'ai_testcase_knowledge_chunk'
        ordering = ['id']
        verbose_name = '知识分块'
        verbose_name_plural = verbose_name


class TestCaseSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_testcase_sessions',
        verbose_name='用户',
    )
    title = models.CharField('标题', max_length=255, blank=True, default='')
    description = models.TextField('描述', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'ai_testcase_session'
        ordering = ['-id']
        verbose_name = 'AI 测试用例会话'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title or f'会话#{self.id}'


class TestCaseQA(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_testcase_qas',
        verbose_name='用户',
    )
    session = models.ForeignKey(
        TestCaseSession,
        on_delete=models.CASCADE,
        related_name='qa_configs',
        verbose_name='会话',
    )
    requirement_kb = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='requirement_qas',
        verbose_name='需求文档知识库',
    )
    testcase_kb = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='testcase_qas',
        verbose_name='测试用例知识库',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'ai_testcase_qa'
        ordering = ['-id']
        verbose_name = 'AI 测试用例智能推理问答'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'QA#{self.id} session={self.session_id}'


class TestCaseMessage(models.Model):
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_CHOICES = (
        (ROLE_USER, '用户'),
        (ROLE_ASSISTANT, '助手'),
    )

    session = models.ForeignKey(
        TestCaseSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='会话',
    )
    role = models.CharField('角色', max_length=16, choices=ROLE_CHOICES)
    content = models.TextField('内容', blank=True, default='')
    thinking = models.TextField('思考过程', blank=True, default='')
    references = models.JSONField('引用', default=list, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'ai_testcase_message'
        ordering = ['id']
        verbose_name = '会话消息'
        verbose_name_plural = verbose_name
