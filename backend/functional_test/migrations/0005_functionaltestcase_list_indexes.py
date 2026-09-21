from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('functional_test', '0004_generation_pipeline_snapshot'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='functionaltestcase',
            index=models.Index(fields=['user', 'created_at'], name='ftc_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='functionaltestcase',
            index=models.Index(fields=['user', 'project', 'created_at'], name='ftc_user_proj_created_idx'),
        ),
        migrations.AddIndex(
            model_name='functionaltestcase',
            index=models.Index(fields=['user', 'requirement', 'created_at'], name='ftc_user_req_created_idx'),
        ),
    ]
