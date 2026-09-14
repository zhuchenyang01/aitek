from django.db import models


class ProjectConfig(models.Model):
    key = models.CharField('KEY', max_length=64, unique=True)
    value = models.TextField('VALUE')
    remark = models.CharField('备注', max_length=255, blank=True, default='')
    create_time = models.DateTimeField('CREATE_TIME', auto_now_add=True)

    class Meta:
        db_table = 'project_config'
        ordering = ['-id']
        verbose_name = '项目配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key
