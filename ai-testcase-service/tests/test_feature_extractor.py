import unittest
from unittest.mock import patch

from app.services.feature_extractor import extract_features


def _collect(gen):
    chunks = []
    features = None
    for item in gen:
        if item.get('kind') == 'chunk':
            chunks.append(item.get('content') or '')
        elif item.get('kind') == 'result':
            features = item.get('features')
    return chunks, features


class FeatureExtractorTests(unittest.TestCase):
    @patch('app.services.feature_extractor.build_llm_client')
    def test_extract_features_parses_json(self, mock_build):
        mock_llm = mock_build.return_value
        mock_llm.api_key = 'test-key'
        mock_llm.chat_stream.return_value = iter(['[{"模块":"登录",', '"功能点":"账号密码登录"}]'])
        chunks, features = _collect(extract_features('用户登录需求文档'))
        self.assertTrue(chunks)
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0]['模块'], '登录')

    @patch('app.services.feature_extractor.build_llm_client')
    def test_extract_features_fallback_without_api_key(self, mock_build):
        mock_llm = mock_build.return_value
        mock_llm.api_key = ''
        _, features = _collect(extract_features('第一行\n第二行'))
        self.assertGreaterEqual(len(features), 1)


if __name__ == '__main__':
    unittest.main()
