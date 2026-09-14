from flask import Blueprint, Response, jsonify, request, stream_with_context

from app.auth import require_internal_auth
from app.exceptions import RagError
from app.services.generator_service import TestCaseGenerator
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.sse import sse_bytes

generate_bp = Blueprint('generate', __name__)


@generate_bp.post('/internal/v1/generate/stream')
@require_internal_auth
def generate_stream():
    payload = request.get_json(silent=True) or {}
    query = (payload.get('query') or '').strip()
    requirement_kb_id = payload.get('requirement_kb_id')
    testcase_kb_id = payload.get('testcase_kb_id')
    file_path = (payload.get('file_path') or '').strip() or None
    pipeline = payload.get('pipeline', True)

    if not query:
        return jsonify({'code': 1, 'msg': 'query 不能为空'}), 400
    if not requirement_kb_id or not testcase_kb_id:
        return jsonify({'code': 1, 'msg': 'requirement_kb_id 与 testcase_kb_id 不能为空'}), 400

    llm_config = payload.get('llm_config') or {}
    embedding_config = payload.get('embedding_config') or {}
    rerank_config = payload.get('rerank_config') or {}
    vision_config = payload.get('vision_config') or {}

    @stream_with_context
    def event_stream():
        try:
            yield sse_bytes({
                'response_type': 'pipeline',
                'step': 'prepare',
                'step_label': '准备',
                'status': 'running',
                'content': 'AI 服务已接收请求，开始流水线…',
                'done': False,
            })
            if pipeline:
                orchestrator = PipelineOrchestrator(
                    llm_config=llm_config,
                    vision_config=vision_config,
                    embedding_config=embedding_config,
                    rerank_config=rerank_config,
                )
                for event in orchestrator.run(
                    query,
                    requirement_kb_id,
                    testcase_kb_id,
                    file_path=file_path,
                ):
                    yield sse_bytes(event)
            else:
                generator = TestCaseGenerator(
                    llm_config=llm_config,
                    embedding_config=embedding_config,
                    rerank_config=rerank_config,
                )
                for event in generator.generate_stream(query, requirement_kb_id, testcase_kb_id):
                    yield sse_bytes(event)
        except RagError as exc:
            yield sse_bytes({
                'response_type': 'error',
                'content': exc.message,
                'done': True,
            })
        except Exception as exc:
            yield sse_bytes({
                'response_type': 'error',
                'content': f'AI 服务内部错误：{exc}',
                'done': True,
            })

    response = Response(event_stream(), mimetype='text/event-stream; charset=utf-8')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response
