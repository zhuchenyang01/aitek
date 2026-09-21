import uuid

from flask import Blueprint, current_app, jsonify, request

from app.auth import require_internal_auth
from app.framework.runner import run_api_suite, run_api_test

run_bp = Blueprint('run', __name__)


@run_bp.post('/api/run')
@require_internal_auth
def run_case():
    spec = request.get_json(silent=True) or {}
    if not (spec.get('url') or spec.get('path')):
        return jsonify({'code': 1, 'msg': '缺少请求地址'}), 400
    timeout = spec.get('timeout')
    if timeout is None:
        timeout = current_app.config.get('HTTP_TIMEOUT', 30)
    run_id = str(uuid.uuid4())
    try:
        payload = run_api_test(
            spec,
            timeout=float(timeout),
            report_dir=current_app.config['REPORT_DIR'],
            run_id=run_id,
            log_dir=current_app.config['LOG_DIR'],
            screenshot_dir=current_app.config.get('SCREENSHOT_DIR'),
        )
    except Exception:
        return jsonify({'code': 1, 'msg': '执行失败'}), 400
    msg = '接口测试执行成功' if payload.get('passed') else '接口测试执行失败'
    return jsonify({'code': 0, 'msg': msg, 'data': payload})


@run_bp.post('/api/run-suite')
@require_internal_auth
def run_suite():
    body = request.get_json(silent=True) or {}
    steps = body.get('steps') or []
    if not steps:
        return jsonify({'code': 1, 'msg': '套件步骤为空'}), 400
    timeout = body.get('timeout')
    if timeout is None:
        timeout = current_app.config.get('HTTP_TIMEOUT', 30)
    run_id = str(uuid.uuid4())
    try:
        payload = run_api_suite(
            steps,
            timeout=float(timeout),
            report_dir=current_app.config['REPORT_DIR'],
            run_id=run_id,
            log_dir=current_app.config['LOG_DIR'],
            screenshot_dir=current_app.config.get('SCREENSHOT_DIR'),
        )
    except Exception:
        return jsonify({'code': 1, 'msg': '套件执行失败'}), 400
    msg = '套件执行成功' if payload.get('passed') else '套件执行失败'
    return jsonify({'code': 0, 'msg': msg, 'data': payload})
