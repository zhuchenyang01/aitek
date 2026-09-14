from flask import current_app

from app.extensions import db
from app.services.config_factory import build_embedding_client
from app.services.kb_repository import bulk_create_chunks, create_document, get_knowledge_base
from app.utils.chunk import chunk_text


def ingest_document(knowledge_base_id, title, content_text, source_filename='', embedding_config=None):
    kb = get_knowledge_base(knowledge_base_id)
    if kb is None:
        raise ValueError('知识库不存在')

    text = (content_text or '').strip()
    if not text:
        raise ValueError('文档内容不能为空')

    document = create_document(knowledge_base_id, title, text, source_filename)
    chunks = chunk_text(
        text,
        chunk_size=current_app.config['RAG_CHUNK_SIZE'],
        overlap=current_app.config['RAG_CHUNK_OVERLAP'],
    )
    if not chunks:
        db.session.commit()
        return document.id, 0

    embedder = build_embedding_client(embedding_config)
    vectors = embedder.embed_batch(chunks)
    chunk_count = bulk_create_chunks(knowledge_base_id, document.id, chunks, vectors)
    return document.id, chunk_count
