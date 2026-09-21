from utils.user_errors import user_facing_error


def split_http(http):
    if not isinstance(http, dict):
        return {}, {}
    if http.get('request') or http.get('response'):
        return http.get('request') or {}, http.get('response') or {}
    request = {
        'method': http.get('method') or '',
        'url': http.get('url') or '',
        'headers': http.get('request_headers') or {},
        'params': http.get('request_params') or {},
        'cookies': http.get('request_cookies') or {},
        'body': http.get('request_body') if http.get('request_body') is not None else '',
    }
    response = {
        'status_code': http.get('status_code'),
        'headers': http.get('response_headers') or {},
        'body': http.get('response_text') if http.get('response_text') is not None else '',
        'elapsed_ms': http.get('elapsed_ms'),
    }
    return request, response


def public_run_step(item):
    if not isinstance(item, dict):
        return item
    payload = dict(item)
    payload.pop('unittest_output', None)
    payload.pop('logs', None)
    failures = []
    for row in payload.get('failures') or []:
        failures.append(user_facing_error(row, '执行失败'))
    payload['failures'] = failures
    logs = []
    for row in payload.get('result_logs') or []:
        if not isinstance(row, dict):
            continue
        copy_row = dict(row)
        copy_row.pop('traceback', None)
        if copy_row.get('message') in ('failed', 'error', 'passed'):
            copy_row['message'] = ''
        logs.append(copy_row)
    payload['result_logs'] = logs
    payload['assertion_logs'] = [user_facing_error(row, '断言未通过') for row in payload.get('assertion_logs') or []]
    request, response = split_http(payload.get('http') or {})
    payload['request'] = request
    payload['response'] = response
    return payload


def public_run_data(data):
    if not isinstance(data, dict):
        return data
    payload = dict(data)
    payload.pop('unittest_output', None)
    payload.pop('logs', None)
    if payload.get('failures'):
        payload['failures'] = [user_facing_error(item, '执行失败') for item in payload.get('failures') or []]
    if payload.get('steps'):
        payload['steps'] = [public_run_step(item) for item in payload['steps']]
    if payload.get('result_logs'):
        payload['result_logs'] = public_run_step({'result_logs': payload['result_logs']}).get('result_logs')
    return payload
