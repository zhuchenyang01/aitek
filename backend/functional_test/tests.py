from io import BytesIO
from unittest.mock import patch
from urllib.parse import quote

from django.contrib.auth.models import User
from docx import Document
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from django.test import TestCase, override_settings

from functional_test.ai_service_client import AIServiceError
from functional_test.models import FunctionalProject, FunctionalTestCase, RequirementDocument, TestCaseGeneration


def make_docx_upload(text, filename='req.docx'):
    buf = BytesIO()
    doc = Document()
    doc.add_paragraph(text)
    doc.save(buf)
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(
        filename,
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )


@override_settings(MEDIA_ROOT='/tmp/aitek-functional-test-media')
class FunctionalTestApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='func_user', password='pass12345')
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.key}')

    def test_project_and_requirement_flow(self):
        created = self.client.post(
            '/api/functional-test/projects/',
            {'name': '登录项目', 'description': '登录相关需求'},
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        project_id = created.data['data']['id']

        uploaded = self.client.post(
            f'/api/functional-test/projects/{project_id}/requirements/',
            {'file': make_docx_upload('用户可通过用户名密码登录。'), 'title': '登录需求'},
            format='multipart',
        )
        self.assertEqual(uploaded.status_code, 201)
        self.assertEqual(uploaded.data['data']['title'], '登录需求')

        listed = self.client.get('/api/functional-test/projects/')
        self.assertEqual(listed.status_code, 200)
        projects = listed.data['data']
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]['name'], '登录项目')
        self.assertEqual(projects[0]['requirement_count'], 1)
        self.assertEqual(projects[0]['creator_name'], 'func_user')
        self.assertEqual(projects[0]['requirements'][0]['creator_name'], 'func_user')
        self.assertEqual(len(projects[0]['requirements']), 1)

        doc_id = projects[0]['requirements'][0]['id']
        deleted = self.client.delete(f'/api/functional-test/projects/{project_id}/requirements/{doc_id}/')
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(RequirementDocument.objects.filter(pk=doc_id).exists())

    def test_upload_rejects_invalid_extension(self):
        project = FunctionalProject.objects.create(user=self.user, name='P1')
        from django.core.files.uploadedfile import SimpleUploadedFile

        bad = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/',
            {'file': SimpleUploadedFile('a.txt', b'hello', content_type='text/plain')},
            format='multipart',
        )
        self.assertEqual(bad.status_code, 400)

    @patch('functional_test.views.ai_ingest_document')
    @patch('functional_test.views.iter_generate_stream')
    def test_requirement_generate(self, mock_stream, mock_ingest):
        mock_ingest.return_value = {'document_id': 1, 'chunk_count': 1}

        def fake_stream(*args, **kwargs):
            yield {'response_type': 'thinking', 'content': '检索完成', 'done': False}
            yield {'response_type': 'references', 'content': '', 'knowledge_references': [], 'done': False}
            yield {'response_type': 'answer', 'content': 'TC-001 登录成功', 'done': False}
            yield {'response_type': 'answer', 'content': '', 'done': True}

        mock_stream.side_effect = fake_stream
        project = FunctionalProject.objects.create(user=self.user, name='登录项目')
        uploaded = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/',
            {'file': make_docx_upload('用户可通过用户名密码登录。'), 'title': '登录需求'},
            format='multipart',
        )
        doc_id = uploaded.data['data']['id']
        res = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/{doc_id}/generate/',
            {'stream': False},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['answer'], 'TC-001 登录成功')
        self.assertEqual(res.data['data']['case_count'], 1)
        self.assertTrue(FunctionalTestCase.objects.filter(project=project).exists())
        mock_ingest.assert_called_once()
        mock_stream.assert_called_once()

    @patch('functional_test.views.ai_ingest_document')
    @patch('functional_test.views.iter_generate_stream')
    def test_requirement_generate_stream(self, mock_stream, mock_ingest):
        mock_ingest.return_value = {'document_id': 1, 'chunk_count': 1}

        def fake_stream(*args, **kwargs):
            yield {'response_type': 'thinking', 'content': '正在检索…', 'done': False}
            yield {
                'response_type': 'references',
                'content': '',
                'done': False,
                'knowledge_references': [],
            }
            yield {'response_type': 'answer', 'content': 'TC-001 登录成功', 'done': False}
            yield {'response_type': 'answer', 'content': '', 'done': True}

        mock_stream.side_effect = fake_stream
        project = FunctionalProject.objects.create(user=self.user, name='登录项目')
        uploaded = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/',
            {'file': make_docx_upload('用户可通过用户名密码登录。'), 'title': '登录需求'},
            format='multipart',
        )
        doc_id = uploaded.data['data']['id']
        res = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/{doc_id}/generate/',
            {'stream': True},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        body = b''.join(res.streaming_content).decode('utf-8')
        self.assertIn('thinking', body)
        self.assertIn('saved', body)
        self.assertIn('TC-001', body)
        self.assertTrue(FunctionalTestCase.objects.filter(project=project, requirement_id=doc_id).exists())
        mock_stream.assert_called_once()

    @patch('functional_test.views.ai_ingest_document')
    @patch('functional_test.views.iter_generate_stream')
    def test_requirement_generate_stream_error_event(self, mock_stream, mock_ingest):
        mock_ingest.return_value = {'document_id': 1, 'chunk_count': 1}

        def fake_stream(*args, **kwargs):
            yield {
                'response_type': 'pipeline',
                'step': 'kb_match',
                'step_label': '需求关联',
                'status': 'running',
                'content': '正在关联项目知识库...',
                'done': False,
            }
            raise AIServiceError('AI 服务连接中断，未完成生成流程', status_code=502)

        mock_stream.side_effect = fake_stream
        project = FunctionalProject.objects.create(user=self.user, name='登录项目')
        uploaded = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/',
            {'file': make_docx_upload('用户可通过用户名密码登录。'), 'title': '登录需求'},
            format='multipart',
        )
        doc_id = uploaded.data['data']['id']
        res = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/{doc_id}/generate/',
            {'stream': True},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        body = b''.join(res.streaming_content).decode('utf-8')
        self.assertIn('error', body)
        self.assertIn('AI 服务连接中断', body)

    @patch('functional_test.views.ai_ingest_document')
    @patch('functional_test.views.iter_generate_stream')
    def test_requirement_generate_stream_pipeline_events(self, mock_stream, mock_ingest):
        mock_ingest.return_value = {'document_id': 1, 'chunk_count': 1}

        def fake_stream(*args, **kwargs):
            yield {
                'response_type': 'llm_chunk',
                'step': 'feature_extract',
                'step_label': '功能点提取',
                'content': '[{"模块":"登录","功能点":"账号登录"}]',
                'done': False,
            }
            yield {
                'response_type': 'feature_points',
                'count': 1,
                'items': [{'模块': '登录', '功能点': '账号登录'}],
                'done': False,
            }
            yield {
                'response_type': 'llm_chunk',
                'step': 'direction_split',
                'step_label': '测试方向拆分',
                'content': '[{"方向":"功能测试"}]',
                'done': False,
            }
            yield {'response_type': 'references', 'content': '', 'knowledge_references': [], 'done': False}
            yield {'response_type': 'answer', 'content': 'TC-001 登录成功', 'done': False}
            yield {'response_type': 'answer', 'content': '', 'done': True}

        mock_stream.side_effect = fake_stream
        project = FunctionalProject.objects.create(user=self.user, name='登录项目')
        uploaded = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/',
            {'file': make_docx_upload('用户可通过用户名密码登录。'), 'title': '登录需求'},
            format='multipart',
        )
        doc_id = uploaded.data['data']['id']
        res = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/{doc_id}/generate/',
            {'stream': True},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        body = b''.join(res.streaming_content).decode('utf-8')
        self.assertIn('llm_chunk', body)
        self.assertIn('feature_points', body)
        self.assertIn('saved', body)
        self.assertTrue(FunctionalTestCase.objects.filter(project=project, requirement_id=doc_id).exists())
        _, kwargs = mock_stream.call_args
        self.assertTrue(kwargs.get('pipeline'))
        self.assertIn('vision_config', kwargs)

    @patch('functional_test.views.ai_ingest_document')
    @patch('functional_test.views.iter_generate_stream')
    def test_testcase_list_and_export(self, mock_stream, mock_ingest):
        mock_ingest.return_value = {'document_id': 1, 'chunk_count': 1}

        def fake_stream(*args, **kwargs):
            answer = '### TC-001 登录\n**标题：** 登录\n**测试步骤：** 输入账号\n**预期结果：** 成功\n**优先级：** P0'
            yield {'response_type': 'thinking', 'content': '检索完成', 'done': False}
            yield {'response_type': 'references', 'content': '', 'knowledge_references': [], 'done': False}
            yield {'response_type': 'answer', 'content': answer, 'done': False}
            yield {'response_type': 'answer', 'content': '', 'done': True}

        mock_stream.side_effect = fake_stream
        project = FunctionalProject.objects.create(user=self.user, name='登录项目')
        uploaded = self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/',
            {'file': make_docx_upload('用户可通过用户名密码登录。'), 'title': '登录需求'},
            format='multipart',
        )
        doc_id = uploaded.data['data']['id']
        self.client.post(
            f'/api/functional-test/projects/{project.id}/requirements/{doc_id}/generate/',
            {'stream': False},
            format='json',
        )

        listed = self.client.get('/api/functional-test/testcases/', {'project_id': project.id})
        self.assertEqual(listed.status_code, 200)
        payload = listed.data['data']
        self.assertGreaterEqual(payload['total'], 1)
        self.assertEqual(payload['page'], 1)
        self.assertEqual(payload['page_size'], 20)
        self.assertGreaterEqual(len(payload['items']), 1)
        self.assertEqual(payload['items'][0]['project_name'], '登录项目')

        exported = self.client.get('/api/functional-test/testcases/export/', {'project_id': project.id})
        self.assertEqual(exported.status_code, 200)
        self.assertIn(
            exported['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertTrue(exported.content)
        self.assertIn('filename*=UTF-8\'\'', exported['Content-Disposition'])
        self.assertIn(quote('登录需求.xlsx'), exported['Content-Disposition'])

    def test_delete_testcases(self):
        project = FunctionalProject.objects.create(user=self.user, name='删除项目')
        requirement = RequirementDocument.objects.create(
            user=self.user,
            project=project,
            title='删除需求',
            file=make_docx_upload('内容'),
        )
        generation = TestCaseGeneration.objects.create(
            user=self.user,
            project=project,
            requirement=requirement,
            query='生成',
            answer_raw='',
        )
        cases = [
            FunctionalTestCase.objects.create(
                generation=generation,
                project=project,
                requirement=requirement,
                user=self.user,
                case_no=f'TC-{index:03d}',
                title=f'用例{index}',
                sort_order=index,
            )
            for index in range(1, 4)
        ]
        other = User.objects.create_user(username='other_del', password='pass12345')
        other_project = FunctionalProject.objects.create(user=other, name='他人项目')
        other_req = RequirementDocument.objects.create(
            user=other,
            project=other_project,
            title='他人需求',
            file=make_docx_upload('内容'),
        )
        other_gen = TestCaseGeneration.objects.create(
            user=other,
            project=other_project,
            requirement=other_req,
            query='生成',
            answer_raw='',
        )
        other_case = FunctionalTestCase.objects.create(
            generation=other_gen,
            project=other_project,
            requirement=other_req,
            user=other,
            case_no='TC-OTHER',
            title='他人用例',
        )

        deleted = self.client.delete(f'/api/functional-test/testcases/{cases[0].id}/')
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(FunctionalTestCase.objects.filter(pk=cases[0].id).exists())

        batched = self.client.post(
            '/api/functional-test/testcases/batch-delete/',
            {'ids': [cases[1].id, cases[2].id, other_case.id, 999999]},
            format='json',
        )
        self.assertEqual(batched.status_code, 200)
        self.assertEqual(batched.data['data']['deleted'], 2)
        self.assertFalse(FunctionalTestCase.objects.filter(pk__in=[cases[1].id, cases[2].id]).exists())
        self.assertTrue(FunctionalTestCase.objects.filter(pk=other_case.id).exists())


    def test_update_project_and_requirement(self):
        created = self.client.post(
            '/api/functional-test/projects/',
            {'name': '原项目名', 'description': '原描述'},
            format='json',
        )
        project_id = created.data['data']['id']

        updated = self.client.put(
            f'/api/functional-test/projects/{project_id}/',
            {'name': '新项目名称', 'description': '新描述'},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['data']['name'], '新项目名称')

        uploaded = self.client.post(
            f'/api/functional-test/projects/{project_id}/requirements/',
            {'file': make_docx_upload('需求内容'), 'title': '旧名称'},
            format='multipart',
        )
        doc_id = uploaded.data['data']['id']

        renamed = self.client.put(
            f'/api/functional-test/projects/{project_id}/requirements/{doc_id}/',
            {'title': '新文档名称'},
            format='json',
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.data['data']['title'], '新文档名称')
