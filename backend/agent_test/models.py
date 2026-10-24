from django.conf import settings
from django.db import models


class AgentProject(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_PENDING, '未理解'),
        (STATUS_RUNNING, '理解中'),
        (STATUS_DONE, '已理解'),
        (STATUS_FAILED, '理解失败'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_projects',
        verbose_name='用户',
    )
    name = models.CharField('项目名称', max_length=255)
    path = models.CharField('项目路径', max_length=1024, help_text='Agent 代码目录绝对路径')
    agent_url = models.CharField(
        'Agent JSON-RPC 地址',
        max_length=512,
        blank=True,
        default='http://127.0.0.1:3001',
        help_text='例如 http://127.0.0.1:3001',
    )
    buried_point_url = models.CharField(
        '埋点服务地址',
        max_length=512,
        blank=True,
        default='http://127.0.0.1:5000',
        help_text='例如 http://127.0.0.1:5000',
    )
    understand_status = models.CharField(
        '理解状态',
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'agent_project'
        ordering = ['-id']
        verbose_name = 'Agent 测试项目'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user', 'created_at'], name='agent_proj_user_created_idx'),
        ]

    def __str__(self):
        return self.name


class AgentProjectProfile(models.Model):
    """项目理解档案：与项目一对一，承载模型生成/人工修订的理解文案。"""

    SOURCE_LLM = 'llm'
    SOURCE_MANUAL = 'manual'
    SOURCE_CHOICES = (
        (SOURCE_LLM, '模型生成'),
        (SOURCE_MANUAL, '人工编辑'),
    )

    project = models.OneToOneField(
        AgentProject,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='所属项目',
    )
    content = models.TextField('项目理解', blank=True, default='')
    source = models.CharField('来源', max_length=16, choices=SOURCE_CHOICES, default=SOURCE_LLM)
    llm_model = models.CharField('生成所用模型', max_length=128, blank=True, default='')
    llm_config_id = models.IntegerField('模型配置 ID', null=True, blank=True)
    error_message = models.CharField('最近失败原因', max_length=512, blank=True, default='')
    content_version = models.PositiveIntegerField('文案版本', default=1)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'agent_project_profile'
        verbose_name = 'Agent 项目理解'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'理解#{self.project_id}'


class AgentTestCase(models.Model):
    """Agent 测试用例，归属某个 Agent 项目。"""

    VERIFY_PENDING = 'pending'
    VERIFY_PASSED = 'passed'
    VERIFY_FAILED = 'failed'
    VERIFY_SKIPPED = 'skipped'
    VERIFY_CHOICES = (
        (VERIFY_PENDING, '未校验'),
        (VERIFY_PASSED, '通过'),
        (VERIFY_FAILED, '未通过'),
        (VERIFY_SKIPPED, '已跳过'),
    )

    LEVEL_CHOICES = (
        ('P0', 'P0'),
        ('P1', 'P1'),
        ('P2', 'P2'),
        ('P3', 'P3'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_test_cases',
        verbose_name='用户',
    )
    project = models.ForeignKey(
        AgentProject,
        on_delete=models.CASCADE,
        related_name='test_cases',
        verbose_name='所属项目',
    )
    task_name = models.CharField('任务名称', max_length=255)
    session_id = models.CharField('会话 ID', max_length=128, blank=True, default='')
    tool_chain = models.TextField('工具链', blank=True, default='')
    knowledge_base = models.CharField('知识库', max_length=255, blank=True, default='')
    expected_result = models.TextField('预期结果', blank=True, default='')
    verify_status = models.CharField(
        '校验状态',
        max_length=32,
        choices=VERIFY_CHOICES,
        default=VERIFY_PENDING,
        db_index=True,
    )
    score = models.DecimalField('评分', max_digits=5, decimal_places=2, null=True, blank=True)
    level = models.CharField('等级', max_length=8, choices=LEVEL_CHOICES, default='P2')
    test_reason = models.TextField('测试理由', blank=True, default='')
    dimensions = models.JSONField('覆盖维度', default=list, blank=True)
    user_input = models.TextField('用户输入/提示', blank=True, default='')
    last_run_result = models.TextField('最近执行结果', blank=True, default='')
    last_run_detail = models.JSONField('最近执行详情(完整埋点流)', default=dict, blank=True)
    last_run_at = models.DateTimeField('最近执行时间', null=True, blank=True)
    source_type = models.CharField('来源', max_length=32, default='llm')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'agent_test_case'
        ordering = ['-id']
        verbose_name = 'Agent 测试用例'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user', 'project', 'created_at'], name='agent_case_user_proj_idx'),
        ]

    def __str__(self):
        return self.task_name or f'用例#{self.id}'


class AgentTestRun(models.Model):
    """单次用例执行报告（含完整 Agent 调用与埋点信息）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_test_runs',
        verbose_name='用户',
    )
    project = models.ForeignKey(
        AgentProject,
        on_delete=models.CASCADE,
        related_name='test_runs',
        verbose_name='所属项目',
    )
    case = models.ForeignKey(
        AgentTestCase,
        on_delete=models.CASCADE,
        related_name='runs',
        verbose_name='所属用例',
    )
    request_id = models.CharField('埋点 request_id', max_length=128, blank=True, default='', db_index=True)
    verify_status = models.CharField(
        '校验状态',
        max_length=32,
        choices=AgentTestCase.VERIFY_CHOICES,
        default=AgentTestCase.VERIFY_PENDING,
        db_index=True,
    )
    score = models.DecimalField('评分', max_digits=5, decimal_places=2, null=True, blank=True)
    elapsed_ms = models.FloatField('整轮耗时(ms)', default=0)
    summary = models.CharField('摘要', max_length=512, blank=True, default='')
    detail = models.JSONField('完整执行详情', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'agent_test_run'
        ordering = ['-id']
        verbose_name = 'Agent 测试执行报告'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user', 'project', 'created_at'], name='agent_run_user_proj_idx'),
        ]

    def __str__(self):
        return f'Run#{self.id} case={self.case_id}'
