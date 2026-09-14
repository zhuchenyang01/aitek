import unittest
from unittest.mock import MagicMock, patch

from app import create_app
from app.config import Config
from app.services.pipeline_orchestrator import PipelineOrchestrator


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    INTERNAL_TOKEN = 'test-token'


def _extract_gen(*args, **kwargs):
    yield {'kind': 'chunk', 'content': '[{"模块":"登录"'}
    yield {'kind': 'result', 'features': [{'模块': '登录', '功能点': '账号登录'}]}


def _split_gen(*args, **kwargs):
    yield {'kind': 'chunk', 'content': '[{"方向":"功能测试"'}
    yield {
        'kind': 'result',
        'directions': [{'模块': '登录', '功能点': '账号登录', '方向': '功能测试', '说明': ''}],
    }


class PipelineOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('app.services.pipeline_orchestrator.build_llm_client')
    @patch('app.services.pipeline_orchestrator.split_test_directions', side_effect=_split_gen)
    @patch('app.services.pipeline_orchestrator.extract_features', side_effect=_extract_gen)
    @patch('app.services.pipeline_orchestrator.get_knowledge_base')
    def test_run_pipeline_event_order(
        self,
        mock_get_kb,
        mock_extract,
        mock_split,
        mock_build_llm,
    ):
        req_kb = MagicMock(name='需求库')
        case_kb = MagicMock(name='用例库')
        mock_get_kb.side_effect = [req_kb, case_kb]
        mock_llm = mock_build_llm.return_value
        mock_llm.api_key = ''
        mock_llm.chat_stream.return_value = iter(['TC-001'])

        orchestrator = PipelineOrchestrator()
        orchestrator.generator.iter_retrieve = MagicMock(
            return_value=iter(
                [
                    {'kind': 'progress', 'content': '正在对查询做 Embedding…'},
                    {'kind': 'result', 'hits': [{'score': 0.9, 'knowledge_title': '登录需求'}]},
                ]
            )
        )

        events = list(orchestrator.run('生成用例', 1, 2, file_path=None))
        types = [event['response_type'] for event in events]
        kb_logs = [
            event['content']
            for event in events
            if event.get('response_type') == 'pipeline' and event.get('step') == 'kb_match'
        ]

        self.assertTrue(any('Embedding' in (item or '') for item in kb_logs))
        self.assertTrue(any('命中' in (item or '') for item in kb_logs))
        self.assertIn('llm_chunk', types)
        self.assertIn('feature_points', types)
        self.assertIn('matched_requirements', types)
        self.assertIn('test_directions', types)
        self.assertIn('answer', types)
        self.assertLess(types.index('llm_chunk'), types.index('feature_points'))
        self.assertLess(types.index('feature_points'), types.index('matched_requirements'))
        self.assertLess(types.index('matched_requirements'), types.index('test_directions'))
        llm_steps = [event['step'] for event in events if event['response_type'] == 'llm_chunk']
        self.assertIn('feature_extract', llm_steps)
        self.assertIn('direction_split', llm_steps)


if __name__ == '__main__':
    unittest.main()
