from datetime import datetime

from app.extensions import db


class KnowledgeBase(db.Model):
    __tablename__ = 'ai_testcase_knowledge_base'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    kb_type = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class KnowledgeDocument(db.Model):
    __tablename__ = 'ai_testcase_knowledge_document'

    id = db.Column(db.Integer, primary_key=True)
    knowledge_base_id = db.Column(db.Integer, db.ForeignKey('ai_testcase_knowledge_base.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False, default='')
    source_filename = db.Column(db.String(255), nullable=False, default='')
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class KnowledgeChunk(db.Model):
    __tablename__ = 'ai_testcase_knowledge_chunk'

    id = db.Column(db.Integer, primary_key=True)
    knowledge_base_id = db.Column(db.Integer, db.ForeignKey('ai_testcase_knowledge_base.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('ai_testcase_knowledge_document.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    vector = db.Column(db.JSON, nullable=False, default=list)
    chunk_index = db.Column(db.Integer, nullable=False, default=0)
