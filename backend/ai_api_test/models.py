import os
import uuid

from django.conf import settings
from django.db import models

from functional_test.models import FunctionalProject


def api_doc_upload_to(instance, filename):
    safe_name = os.path.basename(filename)
    return f'api_test/docs/{instance.user_id}/{safe_name}'


class ApiInterface(models.Model):
    METHOD_CHOICES = (
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
        ('HEAD', 'HEAD'),
        ('OPTIONS', 'OPTIONS'),
    )
    BODY_MODE_CHOICES = (
        ('none', 'none'),
        ('raw', 'raw'),
        ('json', 'json'),
        ('form-data', 'form-data'),
        ('urlencoded', 'urlencoded'),
    )
    AUTH_CHOICES = (
        ('none', 'none'),
        ('bearer', 'bearer'),
        ('basic', 'basic'),
        ('apikey', 'apikey'),
    )
    SOURCE_CHOICES = (
        ('manual', '手动创建'),
        ('openapi', 'OpenAPI/Swagger'),
        ('postman', 'Postman'),
        ('word', 'Word 文档'),
    )

    uid = models.UUIDField('唯一标识', default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_interfaces',
        verbose_name='用户',
    )
    project = models.ForeignKey(
        FunctionalProject,
        on_delete=models.CASCADE,
        related_name='api_interfaces',
        verbose_name='项目',
    )
    name = models.CharField('接口名称', max_length=255)
    method = models.CharField('方法', max_length=16, choices=METHOD_CHOICES, default='GET')
    url = models.CharField('请求地址', max_length=2048, blank=True, default='')
    path = models.CharField('路径', max_length=1024, blank=True, default='')
    host = models.CharField('Host', max_length=255, blank=True, default='')
    protocol = models.CharField('协议', max_length=16, blank=True, default='https')
    version = models.CharField('版本号', max_length=64, blank=True, default='')
    description = models.TextField('描述', blank=True, default='')
    headers = models.JSONField('请求头', default=list, blank=True)
    query_params = models.JSONField('Query 参数', default=list, blank=True)
    path_params = models.JSONField('Path 参数', default=list, blank=True)
    body_mode = models.CharField('请求体类型', max_length=32, choices=BODY_MODE_CHOICES, default='none')
    body_raw = models.TextField('请求体', blank=True, default='')
    body_form = models.JSONField('表单参数', default=list, blank=True)
    auth_type = models.CharField('鉴权类型', max_length=32, choices=AUTH_CHOICES, default='none')
    auth_config = models.JSONField('鉴权配置', default=dict, blank=True)
    content_type = models.CharField('Content-Type', max_length=128, blank=True, default='')
    timeout_ms = models.PositiveIntegerField('超时(ms)', default=30000)
    request_example = models.TextField('请求示例', blank=True, default='')
    response_status = models.CharField('响应状态码', max_length=16, blank=True, default='')
    response_headers = models.JSONField('响应头', default=list, blank=True)
    response_body = models.TextField('响应体示例', blank=True, default='')
    source_type = models.CharField('来源', max_length=32, choices=SOURCE_CHOICES, default='manual')
    source_filename = models.CharField('源文件名', max_length=255, blank=True, default='')
    source_file = models.FileField('源文件', upload_to=api_doc_upload_to, blank=True, null=True)
    cookies = models.JSONField('Cookie', default=list, blank=True)
    setup_script = models.TextField('前置操作', blank=True, default='')
    teardown_script = models.TextField('后置操作', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'api_interface'
        ordering = ['-id']
        verbose_name = '接口'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.method} {self.name}'


class ApiInterfaceData(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_interface_data',
        verbose_name='用户',
    )
    interface = models.ForeignKey(
        ApiInterface,
        on_delete=models.CASCADE,
        related_name='test_data',
        verbose_name='关联接口',
    )
    description = models.CharField('数据描述', max_length=255)
    payload = models.JSONField('数据', default=dict)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'api_interface_data'
        ordering = ['-id']
        verbose_name = '接口测试数据'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.id} {self.description}'


class ApiTestCase(models.Model):
    PRIORITY_CHOICES = (
        ('P0', 'P0'),
        ('P1', 'P1'),
        ('P2', 'P2'),
        ('P3', 'P3'),
    )
    SOURCE_CHOICES = (
        ('llm', '大模型生成'),
        ('manual', '手动创建'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_test_cases',
        verbose_name='用户',
    )
    interface = models.ForeignKey(
        ApiInterface,
        on_delete=models.CASCADE,
        related_name='test_cases',
        verbose_name='关联接口',
    )
    name = models.CharField('用例名称', max_length=255)
    priority = models.CharField('优先级', max_length=8, choices=PRIORITY_CHOICES, default='P2')
    case_type = models.CharField('用例类型', max_length=32, blank=True, default='正向')
    description = models.TextField('用例描述', blank=True, default='')
    preconditions = models.TextField('前置条件', blank=True, default='')
    request_headers = models.JSONField('请求头', default=list, blank=True)
    request_query = models.JSONField('Query', default=list, blank=True)
    request_body = models.TextField('请求体', blank=True, default='')
    expected_status = models.CharField('期望状态码', max_length=16, blank=True, default='200')
    expected_body = models.TextField('期望响应', blank=True, default='')
    assertions = models.JSONField('断言', default=list, blank=True)
    source_type = models.CharField('来源', max_length=32, choices=SOURCE_CHOICES, default='llm')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'api_test_case'
        ordering = ['-id']
        verbose_name = '接口用例'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ApiTestRunLog(models.Model):
    OUTCOME_CHOICES = (
        ('running', '执行中'),
        ('stopped', '结束'),
        ('success', '成功'),
        ('failure', '失败'),
        ('error', '错误'),
        ('skip', '跳过'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_test_run_logs',
        verbose_name='用户',
    )
    case = models.ForeignKey(
        ApiTestCase,
        on_delete=models.CASCADE,
        related_name='run_logs',
        verbose_name='用例',
    )
    run_id = models.CharField('运行ID', max_length=64, db_index=True)
    event = models.CharField('事件', max_length=64)
    outcome = models.CharField('结果', max_length=16, choices=OUTCOME_CHOICES, default='running')
    test_name = models.CharField('测试名', max_length=255, blank=True, default='')
    message = models.TextField('说明', blank=True, default='')
    traceback = models.TextField('堆栈', blank=True, default='')
    screenshot_path = models.CharField('截图路径', max_length=1024, blank=True, default='')
    extra = models.JSONField('执行数据', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'api_test_run_log'
        ordering = ['id']
        verbose_name = '接口用例执行日志'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.run_id} {self.event}'


class ApiTestSuite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_test_suites',
        verbose_name='用户',
    )
    project = models.ForeignKey(
        FunctionalProject,
        on_delete=models.CASCADE,
        related_name='api_test_suites',
        verbose_name='项目',
    )
    name = models.CharField('套件名称', max_length=255)
    description = models.TextField('描述', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'api_test_suite'
        ordering = ['-id']
        verbose_name = '接口执行套件'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ApiTestSuiteStep(models.Model):
    suite = models.ForeignKey(
        ApiTestSuite,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name='套件',
    )
    case = models.ForeignKey(
        ApiTestCase,
        on_delete=models.CASCADE,
        related_name='suite_steps',
        verbose_name='用例',
    )
    order = models.PositiveIntegerField('顺序', default=1)
    extractors = models.JSONField('变量提取', default=list, blank=True)

    class Meta:
        db_table = 'api_test_suite_step'
        ordering = ['order', 'id']
        verbose_name = '套件步骤'
        verbose_name_plural = verbose_name


class ApiTestRun(models.Model):
    STATUS_CHOICES = (
        ('running', '执行中'),
        ('success', '成功'),
        ('fail', '失败'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_test_runs',
        verbose_name='用户',
    )
    project = models.ForeignKey(
        FunctionalProject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_test_runs',
        verbose_name='项目',
    )
    suite = models.ForeignKey(
        ApiTestSuite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='runs',
        verbose_name='套件',
    )
    case = models.ForeignKey(
        ApiTestCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='runs',
        verbose_name='用例',
    )
    name = models.CharField('执行名称', max_length=255)
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES, default='running')
    total = models.PositiveIntegerField('总数', default=0)
    passed = models.PositiveIntegerField('通过', default=0)
    failed = models.PositiveIntegerField('失败', default=0)
    skipped = models.PositiveIntegerField('跳过', default=0)
    summary = models.TextField('摘要', blank=True, default='')
    service_run_id = models.CharField('服务运行ID', max_length=64, blank=True, default='')
    started_at = models.DateTimeField('开始时间', auto_now_add=True)
    finished_at = models.DateTimeField('结束时间', null=True, blank=True)

    class Meta:
        db_table = 'api_test_run'
        ordering = ['-id']
        verbose_name = '接口测试执行'
        verbose_name_plural = verbose_name

    @property
    def pass_rate(self):
        if not self.total:
            return '0%'
        return f'{round(self.passed * 100 / self.total)}%'


class ApiTestRunStepResult(models.Model):
    run = models.ForeignKey(
        ApiTestRun,
        on_delete=models.CASCADE,
        related_name='step_results',
        verbose_name='执行记录',
    )
    case = models.ForeignKey(
        ApiTestCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='run_step_results',
        verbose_name='用例',
    )
    step_index = models.PositiveIntegerField('步骤', default=1)
    case_name = models.CharField('用例名称', max_length=255, blank=True, default='')
    passed = models.BooleanField('通过', default=False)
    http = models.JSONField('请求响应', default=dict, blank=True)
    extracts = models.JSONField('提取变量', default=dict, blank=True)
    assertion_logs = models.JSONField('断言', default=list, blank=True)
    result_logs = models.JSONField('过程', default=list, blank=True)
    screenshots = models.JSONField('截图', default=list, blank=True)
    unittest_output = models.TextField('unittest输出', blank=True, default='')
    failures = models.JSONField('失败信息', default=list, blank=True)

    class Meta:
        db_table = 'api_test_run_step'
        ordering = ['step_index', 'id']
        verbose_name = '执行步骤结果'
        verbose_name_plural = verbose_name
