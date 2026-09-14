from app.extensions import db
from app.models.kb import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.utils.vector_store import packed_vector


def get_knowledge_base(kb_id):
    return KnowledgeBase.query.filter_by(id=kb_id).first()


def find_document_by_source(knowledge_base_id, source_filename):
    return KnowledgeDocument.query.filter_by(
        knowledge_base_id=knowledge_base_id,
        source_filename=source_filename,
    ).first()


def list_chunks_with_documents(knowledge_base_id):
    return (
        KnowledgeChunk.query.filter_by(knowledge_base_id=knowledge_base_id)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .add_columns(KnowledgeDocument.title)
        .all()
    )


def create_document(knowledge_base_id, title, content, source_filename=''):
    document = KnowledgeDocument(
        knowledge_base_id=knowledge_base_id,
        title=(title or '').strip(),
        source_filename=(source_filename or '').strip(),
        content=content,
    )
    db.session.add(document)
    db.session.flush()
    return document


def bulk_create_chunks(knowledge_base_id, document_id, chunks, vectors):
    rows = []
    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        rows.append(
            KnowledgeChunk(
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                content=chunk,
                vector=packed_vector(vector),
                chunk_index=index,
            )
        )
    db.session.add_all(rows)
    db.session.commit()
    return len(rows)


def save_chunk_vectors(pairs):
    for chunk, vector in pairs:
        chunk.vector = packed_vector(vector, chunk.vector)
    if pairs:
        db.session.commit()
