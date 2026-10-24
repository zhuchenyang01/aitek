"""SSH 采集：固定远程脚本，禁止用户自定义命令。"""
from __future__ import annotations

import json
import time
from typing import Any

import paramiko

# 远程一次性采样脚本：输出单行 JSON
REMOTE_SCRIPT = r'''
set +e
TS=$(date +%s)
# CPU: 两次 /proc/stat 间隔估算
read_cpu() {
  awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8,$5}' /proc/stat
}
read C1 I1 <<EOF
$(read_cpu)
EOF
sleep 0.4
read C2 I2 <<EOF
$(read_cpu)
EOF
DT=$((C2-C1)); DI=$((I2-I1))
if [ "$DT" -gt 0 ]; then
  CPU=$(awk -v dt="$DT" -v di="$DI" 'BEGIN{printf "%.2f", (1-di/dt)*100}')
else
  CPU=0
fi
# Load
read L1 L5 L15 _ < /proc/loadavg
# Memory
MEM_TOTAL=$(awk '/MemTotal/{print $2*1024}' /proc/meminfo)
MEM_AVAIL=$(awk '/MemAvailable/{print $2*1024}' /proc/meminfo)
if [ -z "$MEM_AVAIL" ] || [ "$MEM_AVAIL" = "0" ]; then
  MEM_FREE=$(awk '/MemFree/{print $2*1024}' /proc/meminfo)
  BUFF=$(awk '/Buffers/{print $2*1024}' /proc/meminfo)
  CACHE=$(awk '/^Cached/{print $2*1024}' /proc/meminfo)
  MEM_AVAIL=$((MEM_FREE+BUFF+CACHE))
fi
MEM_USED=$((MEM_TOTAL-MEM_AVAIL))
MEM_PCT=$(awk -v t="$MEM_TOTAL" -v u="$MEM_USED" 'BEGIN{if(t>0) printf "%.2f", u/t*100; else print 0}')
SWAP_T=$(awk '/SwapTotal/{print $2*1024}' /proc/meminfo)
SWAP_F=$(awk '/SwapFree/{print $2*1024}' /proc/meminfo)
SWAP_PCT=0
if [ "$SWAP_T" -gt 0 ] 2>/dev/null; then
  SWAP_PCT=$(awk -v t="$SWAP_T" -v f="$SWAP_F" 'BEGIN{printf "%.2f", (t-f)/t*100}')
fi
# Disk root
DISK_PCT=$(df -P / 2>/dev/null | awk 'NR==2{gsub(/%/,"",$5); print $5}')
# Diskstats aggregate (sectors); rates computed on server side vs previous sample
DISK_R=$(awk 'BEGIN{r=0;w=0} $3!~/^(loop|ram|dm-|sr)/{r+=$6;w+=$10} END{print r,w}' /proc/diskstats)
read DISK_RD DISK_WR <<EOF
$DISK_R
EOF
# Net (skip lo)
NET=$(awk 'BEGIN{rx=0;tx=0}
  NR>2{
    gsub(/:/,"",$1);
    if($1=="lo") next;
    rx+=$2; tx+=$10
  }
  END{print rx,tx}' /proc/net/dev)
read NET_RX NET_TX <<EOF
$NET
EOF
# Top processes (cpu)
TOP=$(ps -eo pid,comm,%cpu,%mem --sort=-%cpu 2>/dev/null | head -n 6 | awk 'NR>1{printf "%s|%s|%s|%s;",$1,$2,$3,$4}')
printf '{"ts":%s,"cpu_percent":%s,"load1":%s,"load5":%s,"load15":%s,"mem_total":%s,"mem_used":%s,"mem_percent":%s,"swap_percent":%s,"disk_percent":%s,"disk_read_sectors":%s,"disk_write_sectors":%s,"net_rx_bytes":%s,"net_tx_bytes":%s,"top":"%s"}\n' \
  "$TS" "$CPU" "$L1" "$L5" "$L15" "$MEM_TOTAL" "$MEM_USED" "$MEM_PCT" "$SWAP_PCT" \
  "${DISK_PCT:-0}" "${DISK_RD:-0}" "${DISK_WR:-0}" "${NET_RX:-0}" "${NET_TX:-0}" "$TOP"
'''


class SSHCollectError(Exception):
    pass


def _connect(host: str, port: int, username: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=int(port),
            username=username,
            password=password,
            timeout=8,
            banner_timeout=8,
            auth_timeout=8,
            allow_agent=False,
            look_for_keys=False,
        )
    except Exception as exc:
        client.close()
        raise SSHCollectError(f'SSH 连接失败: {exc}') from exc
    return client


def test_connection(host: str, port: int, username: str, password: str) -> dict[str, Any]:
    client = _connect(host, port, username, password)
    try:
        _stdin, stdout, stderr = client.exec_command('uname -a; cat /proc/uptime', timeout=15)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if not out and err:
            raise SSHCollectError(err[:200])
        return {'uname': out.split('\n')[0] if out else '', 'raw': out}
    finally:
        client.close()


def collect_raw(host: str, port: int, username: str, password: str) -> dict[str, Any]:
    client = _connect(host, port, username, password)
    try:
        _stdin, stdout, stderr = client.exec_command(REMOTE_SCRIPT, timeout=15)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if not out:
            raise SSHCollectError(err[:300] or '远程无输出')
        # 取最后一行 JSON（忽略可能的 warning）
        line = out.strip().splitlines()[-1]
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SSHCollectError(f'解析指标失败: {line[:200]}') from exc
        data['_collected_mono'] = time.time()
        return data
    finally:
        client.close()


def compute_rates(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, float | None]:
    """根据两次采样差分计算磁盘/网络速率。"""
    result = {
        'disk_read_bps': None,
        'disk_write_bps': None,
        'net_rx_bps': None,
        'net_tx_bps': None,
    }
    if not previous:
        return result

    dt = float(current.get('ts') or 0) - float(previous.get('ts') or 0)
    if dt <= 0:
        # fallback mono
        dt = float(current.get('_collected_mono') or 0) - float(previous.get('_collected_mono') or 0)
    if dt <= 0:
        return result

    def rate(cur_key: str, prev_key: str, scale: float = 1.0) -> float | None:
        try:
            cur = float(current.get(cur_key) or 0)
            prev = float(previous.get(prev_key) or 0)
        except (TypeError, ValueError):
            return None
        delta = cur - prev
        if delta < 0:
            return None
        return round(delta * scale / dt, 2)

    # sector size typically 512
    result['disk_read_bps'] = rate('disk_read_sectors', 'disk_read_sectors', 512)
    result['disk_write_bps'] = rate('disk_write_sectors', 'disk_write_sectors', 512)
    result['net_rx_bps'] = rate('net_rx_bytes', 'net_rx_bytes')
    result['net_tx_bps'] = rate('net_tx_bytes', 'net_tx_bytes')
    return result
