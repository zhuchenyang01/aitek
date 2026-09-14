from django.test import SimpleTestCase

from system.ollama import fetch_ollama_models, ollama_native_base


class OllamaHelperTests(SimpleTestCase):
    def test_ollama_native_base_strips_v1(self):
        self.assertEqual(
            ollama_native_base('http://127.0.0.1:11434/v1'),
            'http://127.0.0.1:11434',
        )
        self.assertEqual(
            ollama_native_base('http://127.0.0.1:11434'),
            'http://127.0.0.1:11434',
        )

    def test_fetch_ollama_models_parses_tags(self):
        from unittest.mock import MagicMock, patch

        payload = {
            'models': [
                {'name': 'bge-m3:latest', 'size': 100, 'modified_at': '2026-01-01'},
                {'name': 'qwen2.5:latest', 'size': 200, 'modified_at': '2026-01-02'},
            ]
        }
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = response

        with patch('system.ollama.httpx.Client', return_value=client):
            models = fetch_ollama_models('http://127.0.0.1:11434/v1')

        client.get.assert_called_once_with('http://127.0.0.1:11434/api/tags')
        self.assertEqual([item['name'] for item in models], ['bge-m3:latest', 'qwen2.5:latest'])
