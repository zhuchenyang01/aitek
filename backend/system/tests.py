from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from system.models import UserLLMConfig


class UserLLMConfigApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='llm-user', password='pass123')
        self.other = User.objects.create_user(username='other', password='pass123')
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.key}')

    def test_create_list_masks_api_key(self):
        resp = self.client.post(
            '/api/system/llm-configs/',
            {
                'model_type': 'chat',
                'provider': 'deepseek',
                'model': 'deepseek-chat',
                'api_key': 'sk-abcdefghijklmnopqrstuvwxyz',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()['data']
        self.assertEqual(data['model_type'], 'chat')
        self.assertTrue(data['is_default'])
        self.assertNotIn('api_key', data)
        self.assertEqual(data['api_key_masked'], 'sk-****wxyz')
        self.assertTrue(data['has_api_key'])
        self.assertEqual(data['base_url'], 'https://api.deepseek.com/v1')

        listed = self.client.get('/api/system/llm-configs/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()['data']), 1)

    def test_filter_by_model_type(self):
        self.client.post(
            '/api/system/llm-configs/',
            {'model_type': 'chat', 'provider': 'deepseek', 'api_key': 'sk-chat-key-123456789'},
            format='json',
        )
        self.client.post(
            '/api/system/llm-configs/',
            {
                'model_type': 'embedding',
                'source': 'ollama',
                'model': 'bge-m3:latest',
                'base_url': 'http://127.0.0.1:11434/v1',
            },
            format='json',
        )
        chat_list = self.client.get('/api/system/llm-configs/', {'model_type': 'chat'})
        embed_list = self.client.get('/api/system/llm-configs/', {'model_type': 'embedding'})
        self.assertEqual(len(chat_list.json()['data']), 1)
        self.assertEqual(len(embed_list.json()['data']), 1)
        self.assertEqual(embed_list.json()['data'][0]['model'], 'bge-m3:latest')

    def test_update_keeps_api_key_when_blank(self):
        created = self.client.post(
            '/api/system/llm-configs/',
            {'provider': 'deepseek', 'api_key': 'sk-old-secret-key-1234'},
            format='json',
        ).json()['data']
        resp = self.client.patch(
            f'/api/system/llm-configs/{created["id"]}/',
            {'name': '工作模型', 'api_key': ''},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['data']['name'], '工作模型')
        config = UserLLMConfig.objects.get(pk=created['id'])
        self.assertEqual(config.api_key, 'sk-old-secret-key-1234')

    def test_cannot_access_other_user_config(self):
        other_config = UserLLMConfig.objects.create(
            user=self.other,
            name='别人的模型',
            model_type=UserLLMConfig.TYPE_CHAT,
            provider='openai',
            model='gpt-4o-mini',
            base_url='https://api.openai.com/v1',
            api_key='sk-other',
            is_default=True,
        )
        listed = self.client.get('/api/system/llm-configs/')
        self.assertEqual(listed.json()['data'], [])
        resp = self.client.get(f'/api/system/llm-configs/{other_config.id}/')
        self.assertEqual(resp.status_code, 404)

    def test_set_default_scoped_by_model_type(self):
        chat_a = self.client.post(
            '/api/system/llm-configs/',
            {'model_type': 'chat', 'provider': 'deepseek', 'name': 'Chat A', 'api_key': 'sk-aaaaaaaaaaaaaaa1'},
            format='json',
        ).json()['data']
        chat_b = self.client.post(
            '/api/system/llm-configs/',
            {'model_type': 'chat', 'provider': 'qwen', 'name': 'Chat B', 'api_key': 'sk-bbbbbbbbbbbbbbb2'},
            format='json',
        ).json()['data']
        embed = self.client.post(
            '/api/system/llm-configs/',
            {
                'model_type': 'embedding',
                'source': 'ollama',
                'model': 'bge-m3:latest',
                'base_url': 'http://127.0.0.1:11434/v1',
            },
            format='json',
        ).json()['data']
        self.assertTrue(chat_a['is_default'])
        self.assertFalse(chat_b['is_default'])
        self.assertTrue(embed['is_default'])

        self.client.post(f'/api/system/llm-configs/{chat_b["id"]}/default/')
        self.assertFalse(UserLLMConfig.objects.get(pk=chat_a['id']).is_default)
        self.assertTrue(UserLLMConfig.objects.get(pk=chat_b['id']).is_default)
        self.assertTrue(UserLLMConfig.objects.get(pk=embed['id']).is_default)

        self.client.delete(f'/api/system/llm-configs/{chat_b["id"]}/')
        self.assertTrue(UserLLMConfig.objects.get(pk=chat_a['id']).is_default)

    def test_list_ollama_models(self):
        from unittest.mock import patch

        mocked = [
            {'name': 'bge-m3:latest', 'size': 1024, 'modified_at': '2026-01-01'},
            {'name': 'qwen2.5:latest', 'size': 2048, 'modified_at': '2026-01-02'},
        ]
        with patch('system.views.llm_views.fetch_ollama_models', return_value=mocked):
            resp = self.client.get('/api/system/ollama/models/', {'base_url': 'http://127.0.0.1:11434/v1'})
        self.assertEqual(resp.status_code, 200)
        names = [item['name'] for item in resp.json()['data']['models']]
        self.assertEqual(names, ['bge-m3:latest', 'qwen2.5:latest'])

    def test_embedding_test_connection_without_pk(self):
        from unittest.mock import patch

        with patch('system.llm.build_embedding_client') as mock_builder:
            mock_builder.return_value.embed_batch.return_value = [[0.1] * 1024]
            resp = self.client.post(
                '/api/system/llm-configs/test/',
                {
                    'model_type': 'embedding',
                    'source': 'ollama',
                    'provider': 'ollama',
                    'model': 'bge-m3:latest',
                    'base_url': 'http://127.0.0.1:11434/v1',
                },
                format='json',
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['data']['dimension'], 1024)
        self.assertEqual(UserLLMConfig.objects.count(), 0)
