from utils.user_errors import user_facing_error
from django.db.models import Count
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .eval_excel import build_eval_template, parse_eval_excel
from .evaluation import evaluate_queries
from .exceptions import RagError
from .generator import TestCaseGenerator, sse_bytes
from system.llm import resolve_llm_client

from system.llm import resolve_embedding_client, resolve_rerank_client

from .ingest import ingest_uploaded_file
from .models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument, TestCaseMessage, TestCaseQA, TestCaseSession
from .serializers import (
    AskSerializer,
    CreateKnowledgeBaseSerializer,
    CreateQASerializer,
    CreateSessionSerializer,
    EvalRunSerializer,
    KnowledgeBaseSerializer,
    KnowledgeChunkSerializer,
    KnowledgeDocumentDetailSerializer,
    KnowledgeDocumentSerializer,
    TestCaseMessageSerializer,
    TestCaseQASerializer,
    TestCaseSessionSerializer,
)


def ok(data=None, msg='ok', http_status=status.HTTP_200_OK):
    return Response({'code': 0, 'msg': msg, 'data': data}, status=http_status)


def fail(msg='操作失败', data=None, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({'code': 1, 'msg': msg, 'data': data}, status=http_status)


def first_error_msg(errors):
    if isinstance(errors, dict):
        for value in errors.values():
            return first_error_msg(value)
    if isinstance(errors, list) and errors:
        return first_error_msg(errors[0])
    return str(errors)


def kb_queryset(user):
    return KnowledgeBase.objects.filter(user=user).annotate(
        knowledge_count=Count('documents', distinct=True),
        chunk_count=Count('chunks', distinct=True),
    )


def owned_kb(user, pk):
    return KnowledgeBase.objects.filter(pk=pk, user=user).first()


@api_view(['GET'])
def health(request):
    return ok({'msg': 'ok'})


@api_view(['GET', 'POST'])
def session_list_create(request):
    if request.method == 'GET':
        queryset = TestCaseSession.objects.filter(user=request.user)
        return ok(TestCaseSessionSerializer(queryset, many=True).data, msg='查询成功')

    serializer = CreateSessionSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    session = TestCaseSession.objects.create(
        user=request.user,
        title=serializer.validated_data.get('title') or '',
        description=serializer.validated_data.get('description') or '',
    )
    return ok(TestCaseSessionSerializer(session).data, msg='会话创建成功', http_status=status.HTTP_201_CREATED)


@api_view(['GET'])
def session_detail(request, pk):
    session = TestCaseSession.objects.filter(pk=pk, user=request.user).first()
    if session is None:
        return fail('会话不存在', http_status=status.HTTP_404_NOT_FOUND)
    return ok(TestCaseSessionSerializer(session).data, msg='查询成功')


@api_view(['GET'])
def session_messages(request, pk):
    session = TestCaseSession.objects.filter(pk=pk, user=request.user).first()
    if session is None:
        return fail('会话不存在', http_status=status.HTTP_404_NOT_FOUND)
    queryset = TestCaseMessage.objects.filter(session=session)
    return ok(TestCaseMessageSerializer(queryset, many=True).data, msg='查询成功')


@api_view(['GET', 'POST'])
def knowledge_base_list_create(request):
    if request.method == 'GET':
        queryset = kb_queryset(request.user)
        kb_type = (request.query_params.get('kb_type') or '').strip()
        if kb_type:
            queryset = queryset.filter(kb_type=kb_type)
        return ok(KnowledgeBaseSerializer(queryset, many=True).data, msg='查询成功')

    serializer = CreateKnowledgeBaseSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    kb = KnowledgeBase.objects.create(user=request.user, **serializer.validated_data)
    kb.knowledge_count = 0
    kb.chunk_count = 0
    return ok(KnowledgeBaseSerializer(kb).data, msg='知识库创建成功', http_status=status.HTTP_201_CREATED)


@api_view(['GET'])
def knowledge_base_detail(request, pk):
    kb = kb_queryset(request.user).filter(pk=pk).first()
    if kb is None:
        return fail('知识库不存在', http_status=status.HTTP_404_NOT_FOUND)
    return ok(KnowledgeBaseSerializer(kb).data, msg='查询成功')


@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def knowledge_base_documents(request, pk):
    kb = owned_kb(request.user, pk)
    if kb is None:
        return fail('知识库不存在', http_status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        queryset = KnowledgeDocument.objects.filter(knowledge_base=kb).annotate(
            chunk_count=Count('chunks')
        )
        return ok(KnowledgeDocumentSerializer(queryset, many=True).data, msg='查询成功')

    uploaded = request.FILES.get('file')
    if uploaded is None:
        return fail('请上传 pdf 或 docx 文件')
    title = (request.data.get('title') or '').strip()
    try:
        document = ingest_uploaded_file(kb, uploaded, title=title)
    except ValueError as exc:
        return fail(user_facing_error(exc))
    document.chunk_count = document.chunks.count()
    return ok(KnowledgeDocumentSerializer(document).data, msg='文档已入库', http_status=status.HTTP_201_CREATED)


@api_view(['GET', 'DELETE'])
def knowledge_base_document_detail(request, pk, doc_id):
    kb = owned_kb(request.user, pk)
    if kb is None:
        return fail('知识库不存在', http_status=status.HTTP_404_NOT_FOUND)
    document = KnowledgeDocument.objects.filter(pk=doc_id, knowledge_base=kb).first()
    if document is None:
        return fail('文档不存在', http_status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        document.delete()
        return ok(None, msg='文档已删除')

    chunks = KnowledgeChunk.objects.filter(document=document).select_related('document').order_by(
        'chunk_index', 'id'
    )
    data = KnowledgeDocumentDetailSerializer(document).data
    data['chunks'] = KnowledgeChunkSerializer(chunks, many=True).data
    return ok(data, msg='查询成功')


@api_view(['GET'])
def knowledge_base_chunks(request, pk):
    kb = owned_kb(request.user, pk)
    if kb is None:
        return fail('知识库不存在', http_status=status.HTTP_404_NOT_FOUND)
    chunks = (
        KnowledgeChunk.objects.filter(knowledge_base=kb)
        .select_related('document')
        .order_by('document_id', 'chunk_index', 'id')
    )
    return ok(KnowledgeChunkSerializer(chunks, many=True).data, msg='查询成功')


@api_view(['GET'])
def eval_template(request):
    content = build_eval_template()
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="retrieval_eval_template.xlsx"'
    return response


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def eval_parse(request):
    uploaded = request.FILES.get('file')
    if uploaded is None:
        return fail('请上传 Excel 文件')
    name = (uploaded.name or '').lower()
    if not name.endswith('.xlsx'):
        return fail('仅支持 .xlsx 模板文件')
    try:
        queries = parse_eval_excel(uploaded)
    except ValueError as exc:
        return fail(user_facing_error(exc))
    return ok({'queries': queries}, msg='解析成功')


@api_view(['POST'])
def eval_run(request):
    serializer = EvalRunSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    kb = owned_kb(request.user, serializer.validated_data['knowledge_base_id'])
    if kb is None:
        return fail('知识库不存在', http_status=status.HTTP_404_NOT_FOUND)

    ks = serializer.validated_data.get('ks') or [3, 5]
    rerank = serializer.validated_data.get('rerank', True)
    max_k = max(ks)
    generator = TestCaseGenerator(top_k=max_k, rerank_top_k=max_k)

    def retrieve_fn(query):
        return generator.retrieve(kb, query, rerank=rerank)

    try:
        result = evaluate_queries(serializer.validated_data['queries'], retrieve_fn, ks=ks)
    except ValueError as exc:
        return fail(user_facing_error(exc))
    result['knowledge_base_id'] = kb.id
    result['knowledge_base_name'] = kb.name
    result['kb_type'] = kb.kb_type
    result['rerank'] = rerank
    return ok(result, msg='评测完成')


@api_view(['GET', 'POST'])
def qa_list_create(request):
    if request.method == 'GET':
        queryset = TestCaseQA.objects.filter(user=request.user).select_related(
            'session', 'requirement_kb', 'testcase_kb'
        )
        session_id = (request.query_params.get('session_id') or '').strip()
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        return ok(TestCaseQASerializer(queryset, many=True).data, msg='查询成功')

    serializer = CreateQASerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))

    session = TestCaseSession.objects.filter(
        pk=serializer.validated_data['session_id'],
        user=request.user,
    ).first()
    if session is None:
        return fail('会话不存在', http_status=status.HTTP_404_NOT_FOUND)

    requirement_kb = KnowledgeBase.objects.filter(
        pk=serializer.validated_data['requirement_kb_id'],
        user=request.user,
    ).first()
    testcase_kb = KnowledgeBase.objects.filter(
        pk=serializer.validated_data['testcase_kb_id'],
        user=request.user,
    ).first()
    if requirement_kb is None or testcase_kb is None:
        return fail('知识库不存在', http_status=status.HTTP_404_NOT_FOUND)
    if requirement_kb.kb_type != KnowledgeBase.TYPE_REQUIREMENT:
        return fail('requirement_kb_id 必须是需求文档知识库')
    if testcase_kb.kb_type != KnowledgeBase.TYPE_TESTCASE:
        return fail('testcase_kb_id 必须是测试用例知识库')

    qa = TestCaseQA.objects.create(
        user=request.user,
        session=session,
        requirement_kb=requirement_kb,
        testcase_kb=testcase_kb,
    )
    return ok(TestCaseQASerializer(qa).data, msg='智能推理问答创建成功', http_status=status.HTTP_201_CREATED)


@api_view(['GET'])
def qa_detail(request, pk):
    qa = (
        TestCaseQA.objects.filter(pk=pk, user=request.user)
        .select_related('session', 'requirement_kb', 'testcase_kb')
        .first()
    )
    if qa is None:
        return fail('智能推理问答不存在', http_status=status.HTTP_404_NOT_FOUND)
    return ok(TestCaseQASerializer(qa).data, msg='查询成功')


@api_view(['POST'])
def qa_ask(request, pk):
    qa = (
        TestCaseQA.objects.filter(pk=pk, user=request.user)
        .select_related('session', 'requirement_kb', 'testcase_kb')
        .first()
    )
    if qa is None:
        return fail('智能推理问答不存在', http_status=status.HTTP_404_NOT_FOUND)
    serializer = AskSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))

    query = serializer.validated_data['query']
    try:
        llm = resolve_llm_client(request.user, serializer.validated_data.get('llm_config_id'))
    except LookupError:
        return fail('模型配置不存在', http_status=status.HTTP_404_NOT_FOUND)
    generator = TestCaseGenerator(llm=llm, user=request.user, use_env_llm=False)
    TestCaseMessage.objects.create(session=qa.session, role=TestCaseMessage.ROLE_USER, content=query)
    if not (qa.session.title or '').strip():
        qa.session.title = query[:80]
        qa.session.save(update_fields=['title', 'updated_at'])

    if serializer.validated_data.get('stream'):
        def event_stream():
            answer_parts = []
            thinking = ''
            references = []
            try:
                for event in generator.generate_stream(query, qa.requirement_kb, qa.testcase_kb):
                    kind = event.get('response_type')
                    if kind == 'thinking':
                        thinking = event.get('content') or thinking
                    elif kind == 'references':
                        references = event.get('knowledge_references') or []
                    elif kind == 'answer':
                        answer_parts.append(event.get('content') or '')
                    yield sse_bytes(event)
            finally:
                TestCaseMessage.objects.create(
                    session=qa.session,
                    role=TestCaseMessage.ROLE_ASSISTANT,
                    content=''.join(answer_parts),
                    thinking=thinking,
                    references=references,
                )

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    try:
        result = generator.generate(query, qa.requirement_kb, qa.testcase_kb)
    except RagError as exc:
        http_status = exc.status_code if exc.status_code in (400, 502, 503) else 502
        return fail(exc.message, http_status=http_status)

    TestCaseMessage.objects.create(
        session=qa.session,
        role=TestCaseMessage.ROLE_ASSISTANT,
        content=result.get('answer') or '',
        thinking=result.get('thinking') or '',
        references=result.get('references') or [],
    )
    result['query'] = query
    result['qa_id'] = qa.id
    result['session_id'] = qa.session_id
    return ok(result, msg='生成成功')
