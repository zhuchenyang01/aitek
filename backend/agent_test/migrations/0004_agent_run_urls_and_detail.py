from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('agent_test', '0003_agenttestcase'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentproject',
            name='agent_url',
            field=models.CharField(
                blank=True,
                default='http://127.0.0.1:3001',
                help_text='例如 http://127.0.0.1:3001',
                max_length=512,
                verbose_name='Agent JSON-RPC 地址',
            ),
        ),
        migrations.AddField(
            model_name='agentproject',
            name='buried_point_url',
            field=models.CharField(
                blank=True,
                default='http://127.0.0.1:5000',
                help_text='例如 http://127.0.0.1:5000',
                max_length=512,
                verbose_name='埋点服务地址',
            ),
        ),
        migrations.AddField(
            model_name='agenttestcase',
            name='last_run_detail',
            field=models.JSONField(blank=True, default=dict, verbose_name='最近执行详情(完整埋点流)'),
        ),
        migrations.CreateModel(
            name='AgentTestRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_id', models.CharField(blank=True, db_index=True, default='', max_length=128, verbose_name='埋点 request_id')),
                ('verify_status', models.CharField(choices=[('pending', '未校验'), ('passed', '通过'), ('failed', '未通过'), ('skipped', '已跳过')], db_index=True, default='pending', max_length=32, verbose_name='校验状态')),
                ('score', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='评分')),
                ('elapsed_ms', models.FloatField(default=0, verbose_name='整轮耗时(ms)')),
                ('summary', models.CharField(blank=True, default='', max_length=512, verbose_name='摘要')),
                ('detail', models.JSONField(blank=True, default=dict, verbose_name='完整执行详情')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='agent_test.agenttestcase', verbose_name='所属用例')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_runs', to='agent_test.agentproject', verbose_name='所属项目')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agent_test_runs', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': 'Agent 测试执行报告',
                'verbose_name_plural': 'Agent 测试执行报告',
                'db_table': 'agent_test_run',
                'ordering': ['-id'],
            },
        ),
        migrations.AddIndex(
            model_name='agenttestrun',
            index=models.Index(fields=['user', 'project', 'created_at'], name='agent_run_user_proj_idx'),
        ),
    ]
