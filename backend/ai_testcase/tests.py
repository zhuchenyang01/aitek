import json
import os
import tempfile
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from docx import Document
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from ai_testcase.eval_excel import build_eval_template, parse_eval_excel
from ai_testcase.evaluation import evaluate_queries, load_eval_dataset, mrr, precision_at_k, recall_at_k
from ai_testcase.ingest import ingest_document
from ai_testcase.models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument, TestCaseMessage, TestCaseSession
from system.models import UserLLMConfig


def make_docx_upload(text, filename='req.docx'):
    buf = BytesIO()
    doc = Document()
    doc.add_paragraph(text)
    doc.save(buf)
    return SimpleUploadedFile(
        filename,
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )


def make_pdf_upload(text, filename='req.pdf'):
    payload = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    stream = f'BT /F1 12 Tf 50 750 Td ({payload}) Tj ET\n'.encode('latin-1', 'replace')
    objects = [
        b'1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n',
        b'2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n',
        b'3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n',
        b'4 0 obj<< /Length %d >>stream\n' % len(stream) + stream + b'endstream\nendobj\n',
        b'5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n',
    ]
    body = b'%PDF-1.4\n'
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body += obj
    xref = b'xref\n0 6\n0000000000 65535 f \n'
    for offset in offsets[1:]:
        xref += f'{offset:010d} 00000 n \n'.encode()
    trailer = f'trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n{len(body)}\n%%EOF\n'.encode()
    return SimpleUploadedFile(filename, body + xref + trailer, content_type='application/pdf')


@override_settings(
    DEEPSEEK_API_KEY='',
    EMBEDDING_API_KEY='',
    EMBEDDING_USE_LOCAL=True,
    RERANK_API_KEY='',
)
class AiTestcaseApiTests(TestCase):
    def setUp(self):
        os.environ['EMBEDDING_USE_LOCAL'] = '1'
        self.user = User.objects.create_user(username='tester', password='pass123')
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.key}')

    def test_auth_required(self):
        anonymous = APIClient()
        resp = anonymous.get('/api/ai-testcase/sessions/')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['code'], 401)

    def test_create_session(self):
        resp = self.client.post('/api/ai-testcase/sessions/', {'title': '生成登录用例'}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['data']['title'], '生成登录用例')
        self.assertTrue(TestCaseSession.objects.filter(user=self.user, title='生成登录用例').exists())

    def test_knowledge_base_and_ask(self):
        req_resp = self.client.post(
            '/api/ai-testcase/knowledge-bases/',
            {'name': '需求文档知识库', 'kb_type': 'requirement', 'description': '登录需求'},
            format='json',
        )
        case_resp = self.client.post(
            '/api/ai-testcase/knowledge-bases/',
            {'name': '测试用例知识库', 'kb_type': 'testcase'},
            format='json',
        )
        self.assertEqual(req_resp.status_code, 201)
        self.assertEqual(case_resp.status_code, 201)
        req_id = req_resp.json()['data']['id']
        case_id = case_resp.json()['data']['id']

        self.client.post(
            f'/api/ai-testcase/knowledge-bases/{req_id}/documents/',
            {'title': '登录需求', 'file': make_docx_upload('用户可通过用户名密码登录，密码不少于6位，登录成功后签发 Token。', 'login.docx')},
            format='multipart',
        )
        self.client.post(
            f'/api/ai-testcase/knowledge-bases/{case_id}/documents/',
            {'title': '历史用例', 'file': make_docx_upload('TC-01 登录成功：输入正确账号密码，预期跳转首页并返回 Token。', 'cases.docx')},
            format='multipart',
        )

        listed = self.client.get('/api/ai-testcase/knowledge-bases/')
        self.assertEqual(listed.status_code, 200)
        names = [item['name'] for item in listed.json()['data']]
        self.assertIn('需求文档知识库', names)
        self.assertIn('测试用例知识库', names)

        session_id = self.client.post(
            '/api/ai-testcase/sessions/',
            {'title': '生成用例'},
            format='json',
        ).json()['data']['id']
        qa_resp = self.client.post(
            '/api/ai-testcase/qa/',
            {
                'session_id': session_id,
                'requirement_kb_id': req_id,
                'testcase_kb_id': case_id,
            },
            format='json',
        )
        self.assertEqual(qa_resp.status_code, 201)
        qa_id = qa_resp.json()['data']['id']

        ask_resp = self.client.post(
            f'/api/ai-testcase/qa/{qa_id}/ask/',
            {'query': '根据登录需求生成测试用例', 'stream': False},
            format='json',
        )
        self.assertEqual(ask_resp.status_code, 200)
        answer = ask_resp.json()['data']['answer']
        self.assertIn('登录', answer)
        self.assertTrue(ask_resp.json()['data']['references'])

        stream_resp = self.client.post(
            f'/api/ai-testcase/qa/{qa_id}/ask/',
            {'query': '再生成一组用例', 'stream': True},
            format='json',
        )
        self.assertEqual(stream_resp.status_code, 200)
        self.assertIn('text/event-stream', stream_resp['Content-Type'])
        body = b''.join(stream_resp.streaming_content).decode()
        self.assertIn('response_type', body)
        self.assertIn('answer', body)

        messages = self.client.get(f'/api/ai-testcase/sessions/{session_id}/messages/')
        self.assertEqual(messages.status_code, 200)
        rows = messages.json()['data']
        self.assertEqual(TestCaseMessage.objects.filter(session_id=session_id).count(), 4)
        self.assertGreaterEqual(len(rows), 4)
        self.assertEqual(rows[0]['role'], 'user')
        self.assertEqual(rows[0]['content'], '根据登录需求生成测试用例')
        self.assertEqual(rows[1]['role'], 'assistant')
        self.assertTrue(rows[1]['content'])
        self.assertTrue(rows[1]['references'])

        listed_qa = self.client.get('/api/ai-testcase/qa/', {'session_id': session_id})
        self.assertEqual(listed_qa.status_code, 200)
        self.assertEqual(len(listed_qa.json()['data']), 1)
        self.assertEqual(listed_qa.json()['data'][0]['id'], qa_id)

    def test_ask_uses_user_llm_config(self):
        req = KnowledgeBase.objects.create(user=self.user, name='需求', kb_type=KnowledgeBase.TYPE_REQUIREMENT)
        case = KnowledgeBase.objects.create(user=self.user, name='用例', kb_type=KnowledgeBase.TYPE_TESTCASE)
        ingest_document(req, '登录需求', '用户可通过用户名密码登录。')
        ingest_document(case, '历史用例', 'TC-01 登录成功。')
        session = TestCaseSession.objects.create(user=self.user, title='会话')
        qa_id = self.client.post(
            '/api/ai-testcase/qa/',
            {'session_id': session.id, 'requirement_kb_id': req.id, 'testcase_kb_id': case.id},
            format='json',
        ).json()['data']['id']
        cfg = UserLLMConfig.objects.create(
            user=self.user,
            name='我的 DeepSeek',
            model_type=UserLLMConfig.TYPE_CHAT,
            provider=UserLLMConfig.PROVIDER_DEEPSEEK,
            model='deepseek-chat',
            base_url='https://api.deepseek.com/v1',
            api_key='sk-user-secret-key',
            is_default=True,
        )
        with patch('system.llm.LLMClient') as mock_llm:
            instance = mock_llm.return_value
            instance.api_key = 'sk-user-secret-key'
            instance.chat.return_value = '根据登录需求生成的用例正文'
            resp = self.client.post(
                f'/api/ai-testcase/qa/{qa_id}/ask/',
                {'query': '根据登录需求生成测试用例', 'stream': False, 'llm_config_id': cfg.id},
                format='json',
            )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('登录', resp.json()['data']['answer'])
        self.assertEqual(mock_llm.call_args.kwargs['api_key'], 'sk-user-secret-key')
        self.assertEqual(mock_llm.call_args.kwargs['model'], 'deepseek-chat')

        missing = self.client.post(
            f'/api/ai-testcase/qa/{qa_id}/ask/',
            {'query': '再问一次', 'stream': False, 'llm_config_id': 999999},
            format='json',
        )
        self.assertEqual(missing.status_code, 404)

    def test_create_qa_rejects_same_kb(self):
        kb = KnowledgeBase.objects.create(
            user=self.user,
            name='同一库',
            kb_type=KnowledgeBase.TYPE_REQUIREMENT,
        )
        session = TestCaseSession.objects.create(user=self.user, title='会话')
        resp = self.client.post(
            '/api/ai-testcase/qa/',
            {
                'session_id': session.id,
                'requirement_kb_id': kb.id,
                'testcase_kb_id': kb.id,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 1)

    def test_create_qa_rejects_wrong_type(self):
        req = KnowledgeBase.objects.create(user=self.user, name='需求', kb_type=KnowledgeBase.TYPE_REQUIREMENT)
        also_req = KnowledgeBase.objects.create(user=self.user, name='也是需求', kb_type=KnowledgeBase.TYPE_REQUIREMENT)
        session = TestCaseSession.objects.create(user=self.user, title='会话')
        resp = self.client.post(
            '/api/ai-testcase/qa/',
            {
                'session_id': session.id,
                'requirement_kb_id': req.id,
                'testcase_kb_id': also_req.id,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('测试用例知识库', resp.json()['msg'])

    def test_upload_docx_and_view_chunks(self):
        kb_id = self.client.post(
            '/api/ai-testcase/knowledge-bases/',
            {'name': '需求文档知识库', 'kb_type': 'requirement'},
            format='json',
        ).json()['data']['id']
        resp = self.client.post(
            f'/api/ai-testcase/knowledge-bases/{kb_id}/documents/',
            {'title': '登录需求', 'file': make_docx_upload('用户登录失败超过3次锁定账号。')},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 201)
        doc_id = resp.json()['data']['id']
        self.assertEqual(resp.json()['data']['source_filename'], 'req.docx')
        self.assertGreaterEqual(resp.json()['data']['chunk_count'], 1)
        self.assertTrue(KnowledgeDocument.objects.filter(pk=doc_id, source_filename='req.docx').exists())

        listed = self.client.get(f'/api/ai-testcase/knowledge-bases/{kb_id}/documents/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()['data'][0]['id'], doc_id)

        detail = self.client.get(f'/api/ai-testcase/knowledge-bases/{kb_id}/documents/{doc_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertIn('锁定账号', detail.json()['data']['content'])
        self.assertTrue(detail.json()['data']['chunks'])

        chunks = self.client.get(f'/api/ai-testcase/knowledge-bases/{kb_id}/chunks/')
        self.assertEqual(chunks.status_code, 200)
        self.assertEqual(chunks.json()['data'][0]['document_id'], doc_id)

        deleted = self.client.delete(f'/api/ai-testcase/knowledge-bases/{kb_id}/documents/{doc_id}/')
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(KnowledgeDocument.objects.filter(pk=doc_id).exists())
        self.assertFalse(KnowledgeChunk.objects.filter(document_id=doc_id).exists())
        listed_after = self.client.get(f'/api/ai-testcase/knowledge-bases/{kb_id}/documents/')
        self.assertEqual(listed_after.json()['data'], [])

    def test_upload_pdf(self):
        kb_id = self.client.post(
            '/api/ai-testcase/knowledge-bases/',
            {'name': '需求文档知识库', 'kb_type': 'requirement'},
            format='json',
        ).json()['data']['id']
        resp = self.client.post(
            f'/api/ai-testcase/knowledge-bases/{kb_id}/documents/',
            {'file': make_pdf_upload('Login success issues Token')},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 201)
        doc = KnowledgeDocument.objects.get(pk=resp.json()['data']['id'])
        self.assertIn('Token', doc.content)

    def test_reject_unsupported_file(self):
        kb_id = self.client.post(
            '/api/ai-testcase/knowledge-bases/',
            {'name': '需求文档知识库', 'kb_type': 'requirement'},
            format='json',
        ).json()['data']['id']
        resp = self.client.post(
            f'/api/ai-testcase/knowledge-bases/{kb_id}/documents/',
            {'file': SimpleUploadedFile('note.txt', b'hello', content_type='text/plain')},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('pdf', resp.json()['msg'])


class RetrievalEvalTests(TestCase):
    def test_precision_recall_mrr(self):
        retrieved = ['12', '99', '15']
        relevant = {'12', '15'}
        self.assertEqual(precision_at_k(retrieved, relevant, 3), 2 / 3)
        self.assertEqual(recall_at_k(retrieved, relevant, 3), 1.0)
        self.assertEqual(recall_at_k(retrieved, relevant, 1), 0.5)
        self.assertEqual(mrr(retrieved, relevant), 1.0)
        self.assertEqual(mrr(['99', '15'], relevant), 0.5)
        self.assertEqual(precision_at_k([], relevant, 3), 0.0)
        self.assertEqual(recall_at_k([], set(), 3), 1.0)

    def test_load_eval_dataset(self):
        kb_id, queries = load_eval_dataset(
            {'knowledge_base_id': 7, 'queries': [{'query': '登录失败是否锁号？', 'relevant_chunk_ids': [1]}]}
        )
        self.assertEqual(kb_id, 7)
        self.assertEqual(len(queries), 1)
        kb_id, queries = load_eval_dataset([{'query': 'a', 'relevant_chunk_ids': [1]}])
        self.assertIsNone(kb_id)
        self.assertEqual(queries[0]['query'], 'a')
        with self.assertRaises(ValueError):
            load_eval_dataset({'knowledge_base_id': 1})

    def test_evaluate_queries_averages(self):
        hits_by_query = {
            'q1': [{'id': '12', 'knowledge_id': '3'}, {'id': '15', 'knowledge_id': '3'}],
            'q2': [{'id': '15', 'knowledge_id': '3'}],
        }

        def retrieve_fn(query):
            return hits_by_query[query]

        result = evaluate_queries(
            [
                {'query': 'q1', 'relevant_chunk_ids': [12, 15], 'relevant_doc_ids': [3]},
                {'query': 'q2', 'relevant_chunk_ids': [15], 'relevant_doc_ids': [3]},
            ],
            retrieve_fn,
            ks=(1, 2),
        )
        self.assertEqual(result['query_count'], 2)
        self.assertEqual(result['chunk']['labeled'], 2)
        self.assertEqual(result['chunk']['precision@1'], 1.0)
        self.assertEqual(result['chunk']['recall@1'], 0.75)
        self.assertEqual(result['chunk']['recall@2'], 1.0)
        self.assertEqual(result['doc']['recall@1'], 1.0)
        self.assertEqual(result['chunk']['mrr'], 1.0)


@override_settings(
    DEEPSEEK_API_KEY='',
    EMBEDDING_API_KEY='',
    EMBEDDING_USE_LOCAL=True,
    RERANK_API_KEY='',
)
class RetrievalEvalCommandTests(TestCase):
    def setUp(self):
        os.environ['EMBEDDING_USE_LOCAL'] = '1'
        self.user = User.objects.create_user(username='evaler', password='pass123')
        self.kb = KnowledgeBase.objects.create(
            user=self.user,
            name='需求文档知识库',
            kb_type=KnowledgeBase.TYPE_REQUIREMENT,
        )
        login_text = '用户登录失败超过3次锁定账号，登录成功后签发 Token。'
        pay_text = '订单支付超时自动取消，超时时间由商户配置。'
        self.login_doc = ingest_document(self.kb, '登录需求', login_text)
        self.pay_doc = ingest_document(self.kb, '支付需求', pay_text)
        self.login_chunk = KnowledgeChunk.objects.get(document=self.login_doc)
        self.pay_chunk = KnowledgeChunk.objects.get(document=self.pay_doc)

    def test_dump_kb_chunks(self):
        stdout = StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'chunks.json'
            call_command('dump_kb_chunks', kb_id=self.kb.id, output=str(output), stdout=stdout)
            payload = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(payload['knowledge_base_id'], self.kb.id)
        self.assertEqual(payload['chunk_count'], 2)
        ids = {item['id'] for item in payload['chunks']}
        self.assertEqual(ids, {self.login_chunk.id, self.pay_chunk.id})
        self.assertIn('已写入', stdout.getvalue())

    def test_evaluate_retrieval_command(self):
        dataset = {
            'knowledge_base_id': self.kb.id,
            'queries': [
                {
                    'query': '用户登录失败超过3次锁定账号，登录成功后签发 Token。',
                    'relevant_chunk_ids': [self.login_chunk.id],
                    'relevant_doc_ids': [self.login_doc.id],
                }
            ],
        }
        stdout = StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / 'eval.json'
            result_path = Path(tmp) / 'result.json'
            dataset_path.write_text(json.dumps(dataset, ensure_ascii=False), encoding='utf-8')
            call_command(
                'evaluate_retrieval',
                dataset=str(dataset_path),
                no_rerank=True,
                ks='1,3',
                output=str(result_path),
                stdout=stdout,
            )
            result = json.loads(result_path.read_text(encoding='utf-8'))
        self.assertEqual(result['chunk']['recall@1'], 1.0)
        self.assertEqual(result['chunk']['precision@1'], 1.0)
        self.assertEqual(result['doc']['recall@1'], 1.0)
        self.assertFalse(result['rerank'])
        self.assertIn('P@1=', stdout.getvalue())

    def test_evaluate_retrieval_missing_kb(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / 'eval.json'
            dataset_path.write_text(
                json.dumps({'knowledge_base_id': 999999, 'queries': [{'query': 'x', 'relevant_chunk_ids': [1]}]}),
                encoding='utf-8',
            )
            with self.assertRaises(CommandError):
                call_command('evaluate_retrieval', dataset=str(dataset_path), stdout=StringIO())


@override_settings(
    DEEPSEEK_API_KEY='',
    EMBEDDING_API_KEY='',
    EMBEDDING_USE_LOCAL=True,
    RERANK_API_KEY='',
)
class RetrievalEvalApiTests(TestCase):
    def setUp(self):
        os.environ['EMBEDDING_USE_LOCAL'] = '1'
        self.user = User.objects.create_user(username='evalapi', password='pass123')
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.key}')
        self.kb = KnowledgeBase.objects.create(
            user=self.user,
            name='需求文档知识库',
            kb_type=KnowledgeBase.TYPE_REQUIREMENT,
        )
        text = '用户登录失败超过3次锁定账号，登录成功后签发 Token。'
        self.doc = ingest_document(self.kb, '登录需求', text)
        self.chunk = KnowledgeChunk.objects.get(document=self.doc)

    def test_download_template_and_parse(self):
        resp = self.client.get('/api/ai-testcase/eval/template.xlsx')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            resp['Content-Type'],
        )
        queries = parse_eval_excel(BytesIO(resp.content))
        self.assertGreaterEqual(len(queries), 1)
        self.assertTrue(queries[0]['query'])

        parsed = self.client.post(
            '/api/ai-testcase/eval/parse/',
            {'file': SimpleUploadedFile('eval.xlsx', resp.content, content_type=resp['Content-Type'])},
            format='multipart',
        )
        self.assertEqual(parsed.status_code, 200)
        self.assertTrue(parsed.json()['data']['queries'])

    def test_run_eval(self):
        resp = self.client.post(
            '/api/ai-testcase/eval/run/',
            {
                'knowledge_base_id': self.kb.id,
                'queries': [
                    {
                        'query': '用户登录失败超过3次锁定账号，登录成功后签发 Token。',
                        'relevant_chunk_ids': [self.chunk.id],
                        'relevant_doc_ids': [self.doc.id],
                    }
                ],
                'ks': [1, 3],
                'rerank': False,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()['data']
        self.assertEqual(data['chunk']['recall@1'], 1.0)
        self.assertEqual(data['chunk']['precision@1'], 1.0)
        self.assertFalse(data['rerank'])

    def test_parse_eval_excel_ids(self):
        raw = build_eval_template()
        queries = parse_eval_excel(BytesIO(raw))
        self.assertEqual(queries[0]['relevant_chunk_ids'], [12, 15])
        self.assertEqual(queries[0]['relevant_doc_ids'], [3])
