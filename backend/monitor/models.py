from django.conf import settings
from django.db import models


class MonitorServer(models.Model):
    AUTH_PASSWORD = 'password'
    AUTH_CHOICES = (
        (AUTH_PASSWORD, '密码'),
    )

    STATUS_UNKNOWN = 'unknown'
    STATUS_OK = 'ok'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = (
        (STATUS_UNKNOWN, '未知'),
        (STATUS_OK, '正常'),
        (STATUS_ERROR, '异常'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='monitor_servers',
        verbose_name='用户',
    )
    name = models.CharField('名称', max_length=128)
    host = models.CharField('主机', max_length=255)
    port = models.PositiveIntegerField('SSH 端口', default=22)
    username = models.CharField('用户名', max_length=128)
    auth_type = models.CharField(
        '认证方式',
        max_length=16,
        choices=AUTH_CHOICES,
        default=AUTH_PASSWORD,
    )
    password_enc = models.TextField('加密密码', blank=True, default='')
    enabled = models.BooleanField('持续采集', default=False)
    collect_interval = models.PositiveIntegerField('采集间隔(秒)', default=5)
    last_status = models.CharField(
        '最近状态',
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_UNKNOWN,
    )
    last_error = models.CharField('最近错误', max_length=512, blank=True, default='')
    last_collect_at = models.DateTimeField('最近采集时间', null=True, blank=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'monitor_server'
        ordering = ['-id']
        verbose_name = '监控服务器'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user', 'create_time'], name='mon_srv_user_created_idx'),
        ]

    def __str__(self):
        return f'{self.name} ({self.host})'


class MetricSample(models.Model):
    server = models.ForeignKey(
        MonitorServer,
        on_delete=models.CASCADE,
        related_name='samples',
        verbose_name='服务器',
    )
    collected_at = models.DateTimeField('采集时间', db_index=True)
    cpu_percent = models.FloatField('CPU%', null=True, blank=True)
    load1 = models.FloatField('Load1', null=True, blank=True)
    load5 = models.FloatField('Load5', null=True, blank=True)
    load15 = models.FloatField('Load15', null=True, blank=True)
    mem_total = models.BigIntegerField('内存总量(字节)', null=True, blank=True)
    mem_used = models.BigIntegerField('内存已用(字节)', null=True, blank=True)
    mem_percent = models.FloatField('内存%', null=True, blank=True)
    swap_percent = models.FloatField('Swap%', null=True, blank=True)
    disk_percent = models.FloatField('根盘%', null=True, blank=True)
    disk_read_bps = models.FloatField('磁盘读(B/s)', null=True, blank=True)
    disk_write_bps = models.FloatField('磁盘写(B/s)', null=True, blank=True)
    net_rx_bps = models.FloatField('网络收(B/s)', null=True, blank=True)
    net_tx_bps = models.FloatField('网络发(B/s)', null=True, blank=True)
    raw_json = models.TextField('原始 JSON', blank=True, default='')

    class Meta:
        db_table = 'monitor_metric_sample'
        ordering = ['collected_at']
        verbose_name = '指标采样'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['server', 'collected_at'], name='mon_sample_srv_ts_idx'),
        ]

    def __str__(self):
        return f'{self.server_id}@{self.collected_at}'
