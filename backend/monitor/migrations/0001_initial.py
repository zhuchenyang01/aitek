import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MonitorServer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, verbose_name='名称')),
                ('host', models.CharField(max_length=255, verbose_name='主机')),
                ('port', models.PositiveIntegerField(default=22, verbose_name='SSH 端口')),
                ('username', models.CharField(max_length=128, verbose_name='用户名')),
                ('auth_type', models.CharField(choices=[('password', '密码')], default='password', max_length=16, verbose_name='认证方式')),
                ('password_enc', models.TextField(blank=True, default='', verbose_name='加密密码')),
                ('enabled', models.BooleanField(default=False, verbose_name='持续采集')),
                ('collect_interval', models.PositiveIntegerField(default=5, verbose_name='采集间隔(秒)')),
                ('last_status', models.CharField(choices=[('unknown', '未知'), ('ok', '正常'), ('error', '异常')], default='unknown', max_length=16, verbose_name='最近状态')),
                ('last_error', models.CharField(blank=True, default='', max_length=512, verbose_name='最近错误')),
                ('last_collect_at', models.DateTimeField(blank=True, null=True, verbose_name='最近采集时间')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='monitor_servers', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '监控服务器',
                'verbose_name_plural': '监控服务器',
                'db_table': 'monitor_server',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='MetricSample',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('collected_at', models.DateTimeField(db_index=True, verbose_name='采集时间')),
                ('cpu_percent', models.FloatField(blank=True, null=True, verbose_name='CPU%')),
                ('load1', models.FloatField(blank=True, null=True, verbose_name='Load1')),
                ('load5', models.FloatField(blank=True, null=True, verbose_name='Load5')),
                ('load15', models.FloatField(blank=True, null=True, verbose_name='Load15')),
                ('mem_total', models.BigIntegerField(blank=True, null=True, verbose_name='内存总量(字节)')),
                ('mem_used', models.BigIntegerField(blank=True, null=True, verbose_name='内存已用(字节)')),
                ('mem_percent', models.FloatField(blank=True, null=True, verbose_name='内存%')),
                ('swap_percent', models.FloatField(blank=True, null=True, verbose_name='Swap%')),
                ('disk_percent', models.FloatField(blank=True, null=True, verbose_name='根盘%')),
                ('disk_read_bps', models.FloatField(blank=True, null=True, verbose_name='磁盘读(B/s)')),
                ('disk_write_bps', models.FloatField(blank=True, null=True, verbose_name='磁盘写(B/s)')),
                ('net_rx_bps', models.FloatField(blank=True, null=True, verbose_name='网络收(B/s)')),
                ('net_tx_bps', models.FloatField(blank=True, null=True, verbose_name='网络发(B/s)')),
                ('raw_json', models.TextField(blank=True, default='', verbose_name='原始 JSON')),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='samples', to='monitor.monitorserver', verbose_name='服务器')),
            ],
            options={
                'verbose_name': '指标采样',
                'verbose_name_plural': '指标采样',
                'db_table': 'monitor_metric_sample',
                'ordering': ['collected_at'],
            },
        ),
        migrations.AddIndex(
            model_name='monitorserver',
            index=models.Index(fields=['user', 'create_time'], name='mon_srv_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='metricsample',
            index=models.Index(fields=['server', 'collected_at'], name='mon_sample_srv_ts_idx'),
        ),
    ]
