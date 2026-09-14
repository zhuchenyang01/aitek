from django.db import migrations, models


def set_existing_chat_type(apps, schema_editor):
    UserLLMConfig = apps.get_model('system', 'UserLLMConfig')
    UserLLMConfig.objects.filter(provider='ollama').update(source='ollama')
    UserLLMConfig.objects.all().update(model_type='chat')


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0001_user_llm_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='userllmconfig',
            name='dimension',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='向量维度'),
        ),
        migrations.AddField(
            model_name='userllmconfig',
            name='model_type',
            field=models.CharField(
                choices=[
                    ('chat', '对话'),
                    ('embedding', 'Embedding'),
                    ('rerank', 'ReRank'),
                    ('vision', '视觉'),
                    ('voice', '语音'),
                ],
                default='chat',
                max_length=16,
                verbose_name='模型类型',
            ),
        ),
        migrations.AddField(
            model_name='userllmconfig',
            name='source',
            field=models.CharField(
                choices=[('api', 'API'), ('ollama', 'Ollama')],
                default='api',
                max_length=16,
                verbose_name='模型来源',
            ),
        ),
        migrations.RunPython(set_existing_chat_type, migrations.RunPython.noop),
    ]
