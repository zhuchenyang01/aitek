from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ai_testcase', '0003_document_source_filename'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestCaseMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', '用户'), ('assistant', '助手')], max_length=16, verbose_name='角色')),
                ('content', models.TextField(blank=True, default='', verbose_name='内容')),
                ('thinking', models.TextField(blank=True, default='', verbose_name='思考过程')),
                ('references', models.JSONField(blank=True, default=list, verbose_name='引用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                (
                    'session',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='messages',
                        to='ai_testcase.testcasesession',
                        verbose_name='会话',
                    ),
                ),
            ],
            options={
                'verbose_name': '会话消息',
                'verbose_name_plural': '会话消息',
                'db_table': 'ai_testcase_message',
                'ordering': ['id'],
            },
        ),
    ]
