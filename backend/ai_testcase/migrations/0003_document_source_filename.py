from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_testcase', '0002_local_rag'),
    ]

    operations = [
        migrations.AddField(
            model_name='knowledgedocument',
            name='source_filename',
            field=models.CharField('源文件名', max_length=255, blank=True, default=''),
        ),
    ]
