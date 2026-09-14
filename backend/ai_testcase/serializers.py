from rest_framework import serializers

from .models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument, TestCaseMessage, TestCaseQA, TestCaseSession


class CreateSessionSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')


class CreateKnowledgeBaseSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    kb_type = serializers.ChoiceField(choices=KnowledgeBase.TYPE_CHOICES)

    def validate_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('知识库名称不能为空')
        return value


class CreateQASerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    requirement_kb_id = serializers.IntegerField()
    testcase_kb_id = serializers.IntegerField()

    def validate(self, attrs):
        if attrs['requirement_kb_id'] == attrs['testcase_kb_id']:
            raise serializers.ValidationError('需求文档知识库与测试用例知识库不能相同')
        return attrs


class AskSerializer(serializers.Serializer):
    query = serializers.CharField()
    stream = serializers.BooleanField(required=False, default=False)
    llm_config_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_query(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('提问内容不能为空')
        return value


class EvalQuerySerializer(serializers.Serializer):
    query = serializers.CharField()
    relevant_chunk_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        default=list,
    )
    relevant_doc_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        default=list,
    )
    note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_query(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('提问内容不能为空')
        return value


class EvalRunSerializer(serializers.Serializer):
    knowledge_base_id = serializers.IntegerField()
    queries = EvalQuerySerializer(many=True)
    ks = serializers.ListField(child=serializers.IntegerField(), required=False)
    rerank = serializers.BooleanField(required=False, default=True)

    def validate_queries(self, value):
        if not value:
            raise serializers.ValidationError('评测问题不能为空')
        return value

    def validate_ks(self, value):
        if value is None:
            return [3, 5]
        ks = [int(item) for item in value if int(item) > 0]
        if not ks:
            raise serializers.ValidationError('ks 不能为空')
        return ks


class TestCaseSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseSession
        fields = ('id', 'title', 'description', 'created_at', 'updated_at')


class TestCaseMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseMessage
        fields = ('id', 'role', 'content', 'thinking', 'references', 'created_at')


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    knowledge_count = serializers.IntegerField(read_only=True)
    chunk_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = KnowledgeBase
        fields = (
            'id',
            'name',
            'description',
            'kb_type',
            'knowledge_count',
            'chunk_count',
            'created_at',
            'updated_at',
        )


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    chunk_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = KnowledgeDocument
        fields = ('id', 'title', 'source_filename', 'chunk_count', 'created_at')


class KnowledgeDocumentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeDocument
        fields = ('id', 'title', 'source_filename', 'content', 'created_at')


class KnowledgeChunkSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)

    class Meta:
        model = KnowledgeChunk
        fields = ('id', 'document_id', 'document_title', 'chunk_index', 'content')


class TestCaseQASerializer(serializers.ModelSerializer):
    session_id = serializers.IntegerField(source='session.id', read_only=True)
    requirement_kb_id = serializers.IntegerField(source='requirement_kb.id', read_only=True)
    requirement_kb_name = serializers.CharField(source='requirement_kb.name', read_only=True)
    testcase_kb_id = serializers.IntegerField(source='testcase_kb.id', read_only=True)
    testcase_kb_name = serializers.CharField(source='testcase_kb.name', read_only=True)

    class Meta:
        model = TestCaseQA
        fields = (
            'id',
            'session_id',
            'requirement_kb_id',
            'requirement_kb_name',
            'testcase_kb_id',
            'testcase_kb_name',
            'created_at',
            'updated_at',
        )
