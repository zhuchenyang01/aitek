from pathlib import Path

from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand

from functional_test.models import FunctionalProject, RequirementDocument

SAMPLE_FILENAME = '长银需求--B端投保.docx'
SAMPLE_TITLE = '长银需求--B端投保'
DEFAULT_PROJECT_NAME = '示例项目'


class Command(BaseCommand):
    help = '将仓库内的示例需求文档迁移到需求管理表格'

    def handle(self, *args, **options):
        sample_path = Path(__file__).resolve().parents[3] / SAMPLE_FILENAME
        if not sample_path.is_file():
            self.stderr.write(self.style.ERROR(f'示例文件不存在: {sample_path}'))
            return

        users = User.objects.filter(is_active=True)
        if not users.exists():
            self.stderr.write(self.style.ERROR('没有可用用户，请先注册账号'))
            return

        created_count = 0
        for user in users:
            project, project_created = FunctionalProject.objects.get_or_create(
                user=user,
                name=DEFAULT_PROJECT_NAME,
                defaults={'description': '默认示例项目'},
            )
            exists = RequirementDocument.objects.filter(
                project=project,
                source_filename=SAMPLE_FILENAME,
            ).exists()
            if exists:
                self.stdout.write(f'用户 {user.username} 已存在示例需求，跳过')
                continue

            with sample_path.open('rb') as handle:
                RequirementDocument.objects.create(
                    project=project,
                    user=user,
                    title=SAMPLE_TITLE,
                    source_filename=SAMPLE_FILENAME,
                    file=File(handle, name=SAMPLE_FILENAME),
                )
            created_count += 1
            action = '创建项目并' if project_created else ''
            self.stdout.write(self.style.SUCCESS(f'用户 {user.username}：{action}迁移示例需求成功'))

        if created_count:
            self.stdout.write(self.style.SUCCESS(f'共迁移 {created_count} 条示例需求'))
        else:
            self.stdout.write('无需迁移')
