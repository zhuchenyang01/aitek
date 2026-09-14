from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('functional_test', '0002_testcasegeneration_functionaltestcase'),
    ]

    operations = [
        migrations.AddField(
            model_name='functionaltestcase',
            name='module',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='模块'),
        ),
        migrations.AlterField(
            model_name='functionaltestcase',
            name='case_no',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='用例编号'),
        ),
    ]
