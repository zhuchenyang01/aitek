from django.core.management.base import BaseCommand

from monitor.collector import SSHCollectError
from monitor.models import MonitorServer
from monitor.services import collect_and_store


class Command(BaseCommand):
    help = '对 enabled=True 的监控服务器批量 SSH 采集并落库'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='采集全部服务器（忽略 enabled 开关）',
        )

    def handle(self, *args, **options):
        qs = MonitorServer.objects.all().order_by('id')
        if not options.get('all'):
            qs = qs.filter(enabled=True)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('没有需要采集的服务器'))
            return

        ok_count = 0
        fail_count = 0
        for server in qs:
            try:
                sample = collect_and_store(server)
                ok_count += 1
                self.stdout.write(
                    f'[OK] #{server.id} {server.name} cpu={sample.cpu_percent}% mem={sample.mem_percent}%'
                )
            except SSHCollectError as exc:
                fail_count += 1
                self.stderr.write(f'[FAIL] #{server.id} {server.name}: {exc}')
            except Exception as exc:
                fail_count += 1
                self.stderr.write(f'[ERROR] #{server.id} {server.name}: {exc}')

        self.stdout.write(
            self.style.SUCCESS(f'完成: 成功 {ok_count}, 失败 {fail_count}, 合计 {total}')
        )
