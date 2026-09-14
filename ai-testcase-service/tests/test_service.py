import os
import unittest

os.environ.setdefault('AI_SERVICE_INTERNAL_TOKEN', 'test-token')

from app import create_app
from app.config import Config
from app.sse import sse_bytes
from app.utils.chunk import chunk_text


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    INTERNAL_TOKEN = 'test-token'


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def test_packed_vectors_keep_multiple_dims(self):
        from app.utils.vector_store import packed_vector, vector_for_dim

        stored = packed_vector([0.1] * 1024)
        stored = packed_vector([0.2] * 2048, stored)
        self.assertEqual(len(vector_for_dim(stored, 1024)), 1024)
        self.assertEqual(len(vector_for_dim(stored, 2048)), 2048)
        self.assertEqual(vector_for_dim([0.3] * 1024, 1024)[0], 0.3)
        self.assertIsNone(vector_for_dim([0.3] * 1024, 2048))

    def test_health(self):
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['status'], 'ok')

    def test_ingest_requires_internal_token(self):
        res = self.client.post('/internal/v1/ingest', json={'knowledge_base_id': 1})
        self.assertEqual(res.status_code, 401)

    def test_generate_requires_user_header(self):
        res = self.client.post(
            '/internal/v1/generate/stream',
            json={'query': 'test', 'requirement_kb_id': 1, 'testcase_kb_id': 2},
            headers={'X-Internal-Token': 'test-token'},
        )
        self.assertEqual(res.status_code, 400)

    def test_chunk_text(self):
        text = 'a' * 1000
        chunks = chunk_text(text, chunk_size=300, overlap=50)
        self.assertGreater(len(chunks), 1)

    def test_batch_cosine_rejects_dim_mismatch(self):
        from app.utils.similarity import batch_cosine
        import numpy as np

        with self.assertRaises(ValueError) as ctx:
            batch_cosine([0.1] * 2048, np.zeros((2, 1024), dtype=np.float32))
        self.assertIn('向量维度不一致', str(ctx.exception))

    def test_sse_bytes(self):
        payload = sse_bytes({'response_type': 'answer', 'content': 'hi', 'done': False})
        self.assertIn(b'data:', payload)


if __name__ == '__main__':
    unittest.main()
