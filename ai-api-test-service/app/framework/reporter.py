import json
from datetime import datetime
from html import escape
from pathlib import Path


def write_reports(report_dir, run_id, payload):
    folder = Path(report_dir)
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / f'{run_id}.json'
    html_path = folder / f'{run_id}.html'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    result = payload.get('http') or {}
    assertions = payload.get('assertion_logs') or []
    logs = payload.get('logs') or []
    status = '成功' if payload.get('passed') else '失败'
    rows = ''.join(f'<li>{escape(str(item))}</li>' for item in assertions)
    log_rows = ''.join(f'<pre>{escape(str(item))}</pre>' for item in logs)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>接口测试报告 {escape(run_id)}</title></head>
<body>
<h1>接口测试报告</h1>
<p>用例：{escape(str(payload.get('case_name') or ''))}</p>
<p>结果：<strong>{status}</strong></p>
<p>时间：{escape(payload.get('finished_at') or '')}</p>
<p>请求：{escape(str(result.get('method') or ''))} {escape(str(result.get('url') or ''))}</p>
<p>状态码：{escape(str(result.get('status_code') or ''))} 耗时 {escape(str(result.get('elapsed_ms') or ''))} ms</p>
<h2>断言</h2>
<ul>{rows}</ul>
<h2>响应</h2>
<pre>{escape((result.get('response_text') or '')[:4000])}</pre>
<h2>日志</h2>
{log_rows}
</body>
</html>
"""
    html_path.write_text(html, encoding='utf-8')
    return str(html_path), str(json_path)


def now_text():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
