from __future__ import annotations

import json
from datetime import timedelta

from django.utils import timezone

from .collector import SSHCollectError, collect_raw, compute_rates, test_connection
from .crypto_util import decrypt_password
from .models import MetricSample, MonitorServer

RETENTION_DAYS = 7


def _f(val, default=None):
    if val is None or val == '':
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _i(val, default=None):
    if val is None or val == '':
        return default
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


def cleanup_old_samples(server: MonitorServer | None = None) -> int:
    cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
    qs = MetricSample.objects.filter(collected_at__lt=cutoff)
    if server is not None:
        qs = qs.filter(server=server)
    deleted, _ = qs.delete()
    return deleted


def get_password(server: MonitorServer) -> str:
    try:
        return decrypt_password(server.password_enc)
    except Exception as exc:
        raise SSHCollectError(f'密码解密失败: {exc}') from exc


def run_test(server: MonitorServer) -> dict:
    password = get_password(server)
    try:
        info = test_connection(server.host, server.port, server.username, password)
        server.last_status = MonitorServer.STATUS_OK
        server.last_error = ''
        server.save(update_fields=['last_status', 'last_error', 'update_time'])
        return info
    except SSHCollectError as exc:
        server.last_status = MonitorServer.STATUS_ERROR
        server.last_error = str(exc)[:512]
        server.save(update_fields=['last_status', 'last_error', 'update_time'])
        raise


def collect_and_store(server: MonitorServer) -> MetricSample:
    password = get_password(server)
    try:
        raw = collect_raw(server.host, server.port, server.username, password)
    except SSHCollectError as exc:
        server.last_status = MonitorServer.STATUS_ERROR
        server.last_error = str(exc)[:512]
        server.save(update_fields=['last_status', 'last_error', 'update_time'])
        raise

    prev = (
        MetricSample.objects.filter(server=server)
        .order_by('-collected_at')
        .first()
    )
    prev_raw = None
    if prev and prev.raw_json:
        try:
            prev_raw = json.loads(prev.raw_json)
        except json.JSONDecodeError:
            prev_raw = None

    rates = compute_rates(raw, prev_raw)
    now = timezone.now()
    sample = MetricSample.objects.create(
        server=server,
        collected_at=now,
        cpu_percent=_f(raw.get('cpu_percent')),
        load1=_f(raw.get('load1')),
        load5=_f(raw.get('load5')),
        load15=_f(raw.get('load15')),
        mem_total=_i(raw.get('mem_total')),
        mem_used=_i(raw.get('mem_used')),
        mem_percent=_f(raw.get('mem_percent')),
        swap_percent=_f(raw.get('swap_percent')),
        disk_percent=_f(raw.get('disk_percent')),
        disk_read_bps=rates.get('disk_read_bps'),
        disk_write_bps=rates.get('disk_write_bps'),
        net_rx_bps=rates.get('net_rx_bps'),
        net_tx_bps=rates.get('net_tx_bps'),
        raw_json=json.dumps(raw, ensure_ascii=False),
    )
    server.last_status = MonitorServer.STATUS_OK
    server.last_error = ''
    server.last_collect_at = now
    server.save(update_fields=['last_status', 'last_error', 'last_collect_at', 'update_time'])
    cleanup_old_samples(server)
    return sample
