from flask import Blueprint, jsonify, request

from app.auth import require_internal_auth
from app.services.ingest_service import ingest_document

ingest_bp = Blueprint('ingest', __name__)


@ingest_bp.post('/internal/v1/ingest')
@require_internal_auth
def ingest():
    payload = request.get_json(silent=True) or {}
    knowledge_base_id = payload.get('knowledge_base_id')
    if not knowledge_base_id:
        return jsonify({'code': 1, 'msg': 'knowledge_base_id 不能为空'}), 400

    try:
        document_id, chunk_count = ingest_document(
            knowledge_base_id=knowledge_base_id,
            title=payload.get('title') or '',
            content_text=payload.get('content_text') or '',
            source_filename=payload.get('source_filename') or '',
            embedding_config=payload.get('embedding_config') or {},
        )
    except ValueError as exc:
        return jsonify({'code': 1, 'msg': str(exc)}), 400
    except Exception as exc:
        return jsonify({'code': 1, 'msg': f'入库失败：{exc}'}), 500

    return jsonify({
        'code': 0,
        'msg': 'ok',
        'data': {
            'document_id': document_id,
            'chunk_count': chunk_count,
        },
    })
