from functools import wraps

from flask import current_app, jsonify, request


def require_internal_auth(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        expected = (current_app.config.get('INTERNAL_TOKEN') or '').strip()
        if expected:
            token = (request.headers.get('X-Internal-Token') or '').strip()
            if token != expected:
                return jsonify({'code': 1, 'msg': 'Unauthorized internal request'}), 401
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({'code': 1, 'msg': 'Missing X-User-Id header'}), 400
        request.user_id = user_id
        return view_func(*args, **kwargs)

    return wrapper
