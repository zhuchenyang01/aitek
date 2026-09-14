from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('functional_test', '0003_functionaltestcase_module'),
    ]

    operations = [
        migrations.AddField(
            model_name='testcasegeneration',
            name='feature_points',
            field=models.JSONField(blank=True, default=list, verbose_name='功能点拆分'),
        ),
        migrations.AddField(
            model_name='testcasegeneration',
            name='test_directions',
            field=models.JSONField(blank=True, default=list, verbose_name='测试方向拆分'),
        ),
    ]
