import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-testcase-service-dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:password@127.0.0.1:3306/aitek?charset=utf8mb4',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    INTERNAL_TOKEN = os.environ.get('AI_SERVICE_INTERNAL_TOKEN', '')
    RAG_RETRIEVE_TOP_K = int(os.environ.get('RAG_RETRIEVE_TOP_K', '5'))
    RAG_RERANK_TOP_K = int(os.environ.get('RAG_RERANK_TOP_K', '3'))
    RAG_CHUNK_SIZE = int(os.environ.get('RAG_CHUNK_SIZE', '500'))
    RAG_CHUNK_OVERLAP = int(os.environ.get('RAG_CHUNK_OVERLAP', '80'))
    RAG_HTTP_TIMEOUT = float(os.environ.get('RAG_HTTP_TIMEOUT', '120'))
