"""调用 Agent JSON-RPC + 拉取埋点日志，完成真实用例执行与校验。"""

from __future__ import annotations

import ast
import json
import re
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import requests


def parse_expected_tools(tool_chain: str) -> List[str]:
    text = (tool_chain or '').strip()
    if not text:
        return []
    if text.startswith('['):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except json.JSONDecodeError:
            pass
    parts = re.split(r'\s*(?:->|,|，|；|;|\|)\s*', text)
    return [p.strip() for p in parts if p.strip() and p.strip() != '无']


_TURN_SPLIT = re.compile(
    r'(?:^|\n)\s*(?:Turn\s*\d+|turn\s*\d+|第\s*\d+\s*轮|轮次\s*\d+)\s*[:：\.、\)]\s*',
    re.IGNORECASE,
)


def parse_turns(user_input: str) -> List[str]:
    """将多轮用例输入拆成多段。支持 Turn1: / 第1轮: / 空行 / 多行短句。"""
    text = (user_input or '').strip()
    if not text:
        return []
    if _TURN_SPLIT.search(text):
        chunks = [c.strip() for c in _TURN_SPLIT.split(text) if c and c.strip()]
        if chunks:
            return chunks
    paras = [p.strip() for p in re.split(r'\n\s*\n+', text) if p.strip()]
    if len(paras) > 1:
        return paras
    # 多行且每行都不太长：按单行拆成多轮（兼容「一行一轮」的用例文本）
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 2 and max(len(ln) for ln in lines) <= 180:
        return lines
    return [text]


def build_dialogue_turns(user_input: str, run_detail: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """供列表/详情展示：每一轮用户输入与对应输出。"""
    detail = run_detail if isinstance(run_detail, dict) else {}
    stored = detail.get('turns')
    if isinstance(stored, list) and stored:
        result = []
        for item in stored:
            if not isinstance(item, dict):
                continue
            answer = str(item.get('answer') or item.get('output') or '')
            if not answer and item.get('tool_traces'):
                tools = item.get('tool_traces') or []
                names = [str(t.get('tool')) for t in tools if isinstance(t, dict) and t.get('tool')]
                if names:
                    answer = '本轮已调用工具：' + ' → '.join(names)
            result.append(
                {
                    'turn': item.get('turn') or len(result) + 1,
                    'user_input': str(item.get('user_input') or ''),
                    'answer': answer,
                    'request_id': str(item.get('request_id') or ''),
                    'elapsed_ms': item.get('elapsed_ms'),
                    'executed': bool(item.get('request_id') or answer),
                }
            )
        if result:
            return result
    inputs = parse_turns(user_input or '')
    final_answer = str(detail.get('actual_answer') or '')
    # 仅有整包结果、没有按轮 turns：不要把唯一答案误挂到最后一轮
    if len(inputs) <= 1:
        return [
            {
                'turn': 1,
                'user_input': (user_input or (inputs[0] if inputs else '')),
                'answer': final_answer,
                'request_id': str(detail.get('request_id') or ''),
                'elapsed_ms': detail.get('elapsed_ms'),
                'executed': bool(final_answer or detail.get('request_id')),
            }
        ]
    rows = []
    for idx, text in enumerate(inputs, 1):
        rows.append(
            {
                'turn': idx,
                'user_input': text,
                'answer': '',
                'request_id': '',
                'elapsed_ms': None,
                'executed': False,
                'legacy_note': '历史结果未按轮记录，请重新执行本用例',
            }
        )
    if final_answer:
        rows.append(
            {
                'turn': '汇总',
                'user_input': '（旧版单次执行的完整输出）',
                'answer': final_answer,
                'request_id': str(detail.get('request_id') or ''),
                'elapsed_ms': detail.get('elapsed_ms'),
                'executed': True,
            }
        )
    return rows


def extract_tools_from_logs(logs_payload: Optional[Dict[str, Any]]) -> List[str]:
    if not logs_payload:
        return []
    executed: List[str] = []
    for log in logs_payload.get('logs') or []:
        if log.get('step') != 'invoke':
            continue
        tool_name = log.get('tools_name') or ''
        raw = log.get('data')
        if raw:
            try:
                data_obj = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                try:
                    data_obj = ast.literal_eval(raw) if isinstance(raw, str) else raw
                except Exception:  # noqa: BLE001
                    data_obj = None
            if isinstance(data_obj, dict) and data_obj.get('tools_name'):
                tool_name = data_obj['tools_name']
        if tool_name:
            executed.append(str(tool_name))
    return executed


def validate_tools(actual: List[str], expected: List[str]) -> Dict[str, Any]:
    if not expected:
        return {
            'skipped': True,
            'match': True,
            'correct_order': True,
            'expected_tools': expected,
            'executed_tools': actual,
            'tools_score': 1.0,
            'message': '未配置预期工具链，跳过工具校验',
        }
    correct_order = actual == expected
    # 宽松：预期工具均出现（顺序不强制）时给部分分
    expected_set = set(expected)
    actual_set = set(actual)
    coverage = len(expected_set & actual_set) / len(expected_set) if expected_set else 1.0
    if correct_order:
        score = 1.0
    elif expected_set <= actual_set:
        score = 0.7
    else:
        score = round(coverage * 0.5, 2)
    return {
        'skipped': False,
        'match': correct_order or expected_set <= actual_set,
        'correct_order': correct_order,
        'expected_tools': expected,
        'executed_tools': actual,
        'tools_score': score,
        'message': (
            '工具链完全匹配'
            if correct_order
            else ('预期工具均已调用（顺序不完全一致）' if expected_set <= actual_set else '工具链不匹配')
        ),
    }


def soft_match_expected(expected: str, actual: str) -> Dict[str, Any]:
    exp = (expected or '').strip()
    act = (actual or '').strip()
    if not exp:
        return {'skipped': True, 'match': True, 'score': 1.0, 'message': '未配置预期结果，跳过结果校验'}
    if not act:
        return {'skipped': False, 'match': False, 'score': 0.0, 'message': '实际回复为空'}
    # 取预期中较长的关键词片段做包含判断
    keywords = [k.strip() for k in re.split(r'[,，;；\n]', exp) if len(k.strip()) >= 2]
    if not keywords:
        keywords = [exp[:40]]
    hits = [k for k in keywords if k in act]
    ratio = len(hits) / len(keywords) if keywords else 0
    ok = ratio >= 0.4 or exp[:20] in act
    return {
        'skipped': False,
        'match': ok,
        'score': 1.0 if ok else round(ratio, 2),
        'hit_keywords': hits,
        'message': '预期要点命中' if ok else '预期要点命中不足',
    }


def _safe_get_json(url: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(url, timeout=timeout, headers={'Accept': 'application/json'})
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        return None
    return None


def build_flow(
    request_id: str,
    elapsed_ms: float,
    chat_result: Dict[str, Any],
    logs: Optional[Dict[str, Any]],
    traces: Optional[Dict[str, Any]],
    summary: Optional[Dict[str, Any]],
    tool_validation: Dict[str, Any],
    result_validation: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """时间线式完整调用流，供前端默认折叠展示。"""
    flow: List[Dict[str, Any]] = []
    flow.append(
        {
            'step': 'request',
            'title': '发起 Agent JSON-RPC chat',
            'request_id': request_id,
            'elapsed_ms': elapsed_ms,
        }
    )
    if logs:
        for log in logs.get('logs') or []:
            step = log.get('step')
            title = {
                'arrive': '请求到达 (arrive)',
                'invoke': f"工具调用 (invoke): {log.get('tools_name') or '-'}",
                'response': '请求响应 (response)',
                'trace_execution': f"代码覆盖率 (trace): {log.get('tools_name') or '-'}",
            }.get(step, step or 'log')
            item = {
                'step': step,
                'title': title,
                'created_at': log.get('created_at'),
                'tools_name': log.get('tools_name'),
                'data': log.get('data'),
            }
            # 尝试解析 response 耗时
            if step == 'response' and log.get('data'):
                try:
                    data_obj = json.loads(log['data']) if isinstance(log['data'], str) else log['data']
                    resp_data = (data_obj or {}).get('response_data') or {}
                    item['execution_time_ms'] = resp_data.get('execution_time_ms')
                    item['tool_execution_times'] = resp_data.get('tool_execution_times')
                except Exception:  # noqa: BLE001
                    pass
            if step == 'invoke' and log.get('data'):
                try:
                    data_obj = json.loads(log['data']) if isinstance(log['data'], str) else log['data']
                    inv = (data_obj or {}).get('invoke_data') or {}
                    item['execution_time_ms'] = inv.get('execution_time_ms')
                    item['success'] = inv.get('success')
                except Exception:  # noqa: BLE001
                    pass
            flow.append(item)
    if traces and traces.get('traces'):
        for tr in traces['traces']:
            flow.append(
                {
                    'step': 'trace_detail',
                    'title': f"覆盖率详情: {tr.get('function_name')}",
                    'function_name': tr.get('function_name'),
                    'filename': tr.get('filename'),
                    'coverage_percentage': tr.get('coverage_percentage'),
                    'total_lines': tr.get('total_lines'),
                    'executed_lines': tr.get('executed_lines'),
                    'execution_details': tr.get('execution_details') or [],
                    'created_at': tr.get('created_at'),
                }
            )
    flow.append(
        {
            'step': 'validation',
            'title': '校验结果',
            'tool_validation': tool_validation,
            'result_validation': result_validation,
            'chat_answer_preview': (chat_result.get('response') or chat_result.get('answer') or '')[:500],
        }
    )
    if summary:
        flow.append({'step': 'summary', 'title': '埋点摘要', 'summary': summary})
    return flow


def _call_agent_chat(
    *,
    agent_url: str,
    user_input: str,
    history: List[Dict[str, str]],
    request_id: str,
    timeout: int,
) -> Tuple[Dict[str, Any], float, Optional[str]]:
    payload = {
        'jsonrpc': '2.0',
        'method': 'chat',
        'params': {
            'user_input': user_input or '',
            'history': history,
        },
        'id': request_id,
    }
    start = time.time()
    try:
        resp = requests.post(
            agent_url,
            json=payload,
            headers={'Content-Type': 'application/json', 'Connection': 'close'},
            timeout=timeout,
        )
        elapsed_ms = round((time.time() - start) * 1000, 2)
        return resp.json(), elapsed_ms, None
    except requests.Timeout:
        return {}, round((time.time() - start) * 1000, 2), f'Agent 请求超时（>{timeout}s）: {agent_url}'
    except requests.ConnectionError as exc:
        return {}, round((time.time() - start) * 1000, 2), f'无法连接 Agent: {agent_url} ({exc})'
    except Exception as exc:  # noqa: BLE001
        return {}, round((time.time() - start) * 1000, 2), f'调用 Agent 失败: {exc}'


def run_agent_case(
    *,
    user_input: str,
    tool_chain: str,
    expected_result: str,
    agent_url: str,
    buried_point_url: str,
    timeout: int = 120,
) -> Dict[str, Any]:
    agent_url = (agent_url or 'http://127.0.0.1:3001').rstrip('/')
    buried = (buried_point_url or 'http://127.0.0.1:5000').rstrip('/')
    turn_inputs = parse_turns(user_input)
    if not turn_inputs:
        turn_inputs = [user_input or '']

    history: List[Dict[str, str]] = []
    turns: List[Dict[str, Any]] = []
    all_tools: List[str] = []
    merged_logs: List[Any] = []
    merged_traces: List[Any] = []
    last_summary: Optional[Dict[str, Any]] = None
    last_chat_rpc: Dict[str, Any] = {}
    last_chat_result: Dict[str, Any] = {}
    total_elapsed = 0.0
    error: Optional[str] = None
    session_prefix = uuid.uuid4().hex[:10]

    for idx, turn_text in enumerate(turn_inputs, 1):
        request_id = f'fitness-{session_prefix}-t{idx}'
        chat_rpc, elapsed_ms, call_error = _call_agent_chat(
            agent_url=agent_url,
            user_input=turn_text,
            history=history,
            request_id=request_id,
            timeout=timeout,
        )
        total_elapsed += elapsed_ms
        last_chat_rpc = chat_rpc if isinstance(chat_rpc, dict) else {}

        chat_result: Dict[str, Any] = {}
        turn_error = call_error
        if isinstance(chat_rpc, dict):
            if chat_rpc.get('error'):
                turn_error = turn_error or chat_rpc['error'].get('message') or str(chat_rpc['error'])
            result = chat_rpc.get('result') or {}
            chat_result = result if isinstance(result, dict) else {'response': str(result)}
        last_chat_result = chat_result
        answer = str(chat_result.get('response') or chat_result.get('answer') or '')
        tool_traces = chat_result.get('tool_traces') or []

        time.sleep(0.5)
        logs = _safe_get_json(f'{buried}/logs/{request_id}')
        traces = _safe_get_json(f'{buried}/traces/{request_id}')
        summary = _safe_get_json(f'{buried}/summary/{request_id}')
        if logs and logs.get('logs'):
            merged_logs.extend(logs.get('logs') or [])
        if traces and traces.get('traces'):
            merged_traces.extend(traces.get('traces') or [])
        if summary:
            last_summary = summary

        turn_tools = extract_tools_from_logs(logs)
        if not turn_tools and tool_traces:
            turn_tools = [t.get('tool') for t in tool_traces if isinstance(t, dict) and t.get('tool')]
        all_tools.extend(turn_tools)

        # 仅工具调用、无文本时补一段可读输出，保证多轮详情每轮都有内容
        if not answer and tool_traces:
            msgs = []
            for t in tool_traces:
                if not isinstance(t, dict):
                    continue
                name = t.get('tool') or 'tool'
                result = t.get('result') if isinstance(t.get('result'), dict) else {}
                msgs.append(str(result.get('message') or f'{name} 执行完成'))
            answer = '本轮已完成工具调用：\n' + '\n'.join(msgs) if msgs else '本轮已调用工具：' + ' → '.join(turn_tools)

        turn_elapsed = elapsed_ms
        tel = chat_result.get('telemetry') or {}
        if summary and summary.get('execution_time_ms') is not None:
            try:
                turn_elapsed = float(summary['execution_time_ms'])
            except (TypeError, ValueError):
                pass
        elif tel.get('execution_time_ms') is not None:
            try:
                turn_elapsed = float(tel['execution_time_ms'])
            except (TypeError, ValueError):
                pass

        turns.append(
            {
                'turn': idx,
                'user_input': turn_text,
                'answer': answer,
                'request_id': request_id,
                'elapsed_ms': turn_elapsed,
                'actual_tools': turn_tools,
                'tool_traces': tool_traces,
                'error': turn_error,
                'executed': True,
            }
        )
        if turn_error:
            error = turn_error
            break

        history.append({'role': 'user', 'content': turn_text})
        history.append({'role': 'assistant', 'content': answer})

    primary_request_id = turns[0]['request_id'] if turns else f'fitness-{session_prefix}'
    actual_answer = turns[-1]['answer'] if turns else ''
    # 拼接多轮输出，便于摘要展示
    if len(turns) > 1:
        actual_answer_display = '\n\n'.join(
            f"【第{t['turn']}轮输出】\n{t['answer']}" for t in turns if t.get('answer')
        )
    else:
        actual_answer_display = actual_answer

    expected_tools = parse_expected_tools(tool_chain)
    tool_validation = validate_tools(all_tools, expected_tools)
    result_validation = soft_match_expected(expected_result, actual_answer)

    tools_score = float(tool_validation.get('tools_score') or 0)
    result_score = float(result_validation.get('score') or 0)
    elapsed_ms = round(total_elapsed, 2)
    if error:
        final_score = 0.0
        verify = 'failed'
        summary_text = error[:500]
    else:
        final_score = round(tools_score * 70 + result_score * 30, 2)
        tool_ok = bool(tool_validation.get('match'))
        result_ok = bool(result_validation.get('match'))
        verify = 'passed' if tool_ok and result_ok and final_score >= 60 else 'failed'
        summary_text = (
            f"{'通过' if verify == 'passed' else '未通过'} | "
            f"{len(turns)}轮 | 耗时 {elapsed_ms}ms | 工具 {tool_validation.get('message')} | "
            f"{result_validation.get('message')}"
        )[:500]

    merged_logs_payload = {'request_id': primary_request_id, 'logs': merged_logs, 'count': len(merged_logs)}
    merged_traces_payload = {
        'request_id': primary_request_id,
        'traces': merged_traces,
        'count': len(merged_traces),
    }
    flow = build_flow(
        request_id=primary_request_id,
        elapsed_ms=elapsed_ms,
        chat_result=last_chat_result,
        logs=merged_logs_payload,
        traces=merged_traces_payload,
        summary=last_summary,
        tool_validation=tool_validation,
        result_validation=result_validation,
    )
    # 在 flow 最前插入多轮对话配对
    flow.insert(
        0,
        {
            'step': 'dialogue',
            'title': f'多轮对话（共 {len(turns)} 轮）',
            'turns': turns,
        },
    )

    detail = {
        'request_id': primary_request_id,
        'request_ids': [t['request_id'] for t in turns],
        'agent_url': agent_url,
        'buried_point_url': buried,
        'elapsed_ms': elapsed_ms,
        'error': error,
        'user_input': user_input,
        'turns': turns,
        'expected_tools': expected_tools,
        'actual_tools': all_tools,
        'actual_answer': actual_answer_display or actual_answer,
        'tool_validation': tool_validation,
        'result_validation': result_validation,
        'chat_rpc': last_chat_rpc,
        'chat_result': last_chat_result,
        'buried': {
            'logs': merged_logs_payload,
            'traces': merged_traces_payload,
            'summary': last_summary,
        },
        'flow': flow,
    }

    turn_lines = []
    for t in turns:
        turn_lines.append(f"第{t['turn']}轮输入：{(t.get('user_input') or '')[:120]}")
        turn_lines.append(f"第{t['turn']}轮输出：{(t.get('answer') or '')[:200]}")
    short_result = (
        f"request_id={primary_request_id}\n"
        f"轮次={len(turns)} 耗时={elapsed_ms}ms\n"
        f"状态={verify} 评分={final_score}\n"
        f"预期工具={expected_tools}\n"
        f"实际工具={all_tools}\n"
        + '\n'.join(turn_lines)
        + '\n（完整埋点流请展开详情查看）'
    )

    return {
        'request_id': primary_request_id,
        'verify_status': verify,
        'score': Decimal(str(final_score)),
        'elapsed_ms': elapsed_ms,
        'summary': summary_text,
        'last_run_result': short_result,
        'detail': detail,
    }
