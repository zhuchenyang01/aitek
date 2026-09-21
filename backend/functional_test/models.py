import os

from django.conf import settings
from django.db import models


def requirement_upload_to(instance, filename):
    safe_name = os.path.basename(filename)
    return f'functional_test/requirements/{instance.project_id}/{safe_name}'


class FunctionalProject(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='functional_projects',
        verbose_name='用户',
    )
    name = models.CharField('项目名称', max_length=255)
    description = models.TextField('描述', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'functional_project'
        ordering = ['-id']
        verbose_name = '功能测试项目'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class RequirementDocument(models.Model):
    project = models.ForeignKey(
        FunctionalProject,
        on_delete=models.CASCADE,
        related_name='requirements',
        verbose_name='项目',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requirement_documents',
        verbose_name='用户',
    )
    title = models.CharField('标题', max_length=255, blank=True, default='')
    source_filename = models.CharField('源文件名', max_length=255, blank=True, default='')
    file = models.FileField('文件', upload_to=requirement_upload_to)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'functional_requirement_document'
        ordering = ['-id']
        verbose_name = '需求文档'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title or self.source_filename or f'需求#{self.id}'


class TestCaseGeneration(models.Model):
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_COMPLETED, '已完成'),
        (STATUS_FAILED, '失败'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='testcase_generations',
        verbose_name='用户',
    )
    project = models.ForeignKey(
        FunctionalProject,
        on_delete=models.CASCADE,
        related_name='testcase_generations',
        verbose_name='项目',
    )
    requirement = models.ForeignKey(
        RequirementDocument,
        on_delete=models.CASCADE,
        related_name='testcase_generations',
        verbose_name='需求文档',
    )
    query = models.TextField('生成问题', blank=True, default='')
    answer_raw = models.TextField('原始回答', blank=True, default='')
    thinking = models.TextField('思考过程', blank=True, default='')
    references = models.JSONField('引用', default=list, blank=True)
    feature_points = models.JSONField('功能点拆分', default=list, blank=True)
    test_directions = models.JSONField('测试方向拆分', default=list, blank=True)
    llm_config_id = models.IntegerField('模型配置 ID', null=True, blank=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default=STATUS_COMPLETED)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'functional_testcase_generation'
        ordering = ['-id']
        verbose_name = '测试用例生成记录'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'生成#{self.id}'


class FunctionalTestCase(models.Model):
    generation = models.ForeignKey(
        TestCaseGeneration,
        on_delete=models.CASCADE,
        related_name='cases',
        verbose_name='生成记录',
    )
    project = models.ForeignKey(
        FunctionalProject,
        on_delete=models.CASCADE,
        related_name='functional_testcases',
        verbose_name='项目',
    )
    requirement = models.ForeignKey(
        RequirementDocument,
        on_delete=models.CASCADE,
        related_name='functional_testcases',
        verbose_name='需求文档',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='functional_testcases',
        verbose_name='用户',
    )
    case_no = models.CharField('用例编号', max_length=128, blank=True, default='')
    module = models.CharField('模块', max_length=128, blank=True, default='')
    title = models.CharField('标题', max_length=255, blank=True, default='')
    precondition = models.TextField('前置条件', blank=True, default='')
    steps = models.TextField('测试步骤', blank=True, default='')
    expected_result = models.TextField('预期结果', blank=True, default='')
    priority = models.CharField('优先级', max_length=32, blank=True, default='')
    sort_order = models.PositiveIntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'functional_testcase'
        ordering = ['sort_order', 'id']
        verbose_name = '功能测试用例'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user', 'created_at'], name='ftc_user_created_idx'),
            models.Index(fields=['user', 'project', 'created_at'], name='ftc_user_proj_created_idx'),
            models.Index(fields=['user', 'requirement', 'created_at'], name='ftc_user_req_created_idx'),
        ]

    def __str__(self):
        return self.title or self.case_no or f'用例#{self.id}'
