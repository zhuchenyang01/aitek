from rest_framework import serializers
from django.utils.timezone import localtime

from .models import AgentProject, AgentProjectProfile, AgentTestCase, AgentTestRun
from .runner import build_dialogue_turns


def format_local_datetime(value):
    if not value:
        return ''
    return localtime(value).strftime('%Y-%m-%d %H:%M:%S')


class LocalDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        return format_local_datetime(value)


class AgentProjectWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    path = serializers.CharField(max_length=1024)
    agent_url = serializers.CharField(max_length=512, required=False, allow_blank=True)
    buried_point_url = serializers.CharField(max_length=512, required=False, allow_blank=True)

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('请输入项目名称')
        return name

    def validate_path(self, value):
        path = (value or '').strip()
        if not path:
            raise serializers.ValidationError('请输入项目路径')
        return path

    def validate_agent_url(self, value):
        return (value or '').strip() or 'http://127.0.0.1:3001'

    def validate_buried_point_url(self, value):
        return (value or '').strip() or 'http://127.0.0.1:5000'


class AgentProjectProfileSerializer(serializers.ModelSerializer):
    source_label = serializers.CharField(source='get_source_display', read_only=True)
    created_at = LocalDateTimeField(read_only=True)
    updated_at = LocalDateTimeField(read_only=True)

    class Meta:
        model = AgentProjectProfile
        fields = (
            'id',
            'project_id',
            'content',
            'source',
            'source_label',
            'llm_model',
            'llm_config_id',
            'error_message',
            'content_version',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AgentProjectProfileUpdateSerializer(serializers.Serializer):
    content = serializers.CharField(allow_blank=False, trim_whitespace=False)

    def validate_content(self, value):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('请填写项目理解文案')
        if len(text) > 100000:
            raise serializers.ValidationError('理解文案过长')
        return text


class AgentProjectSerializer(serializers.ModelSerializer):
    understand_status_label = serializers.CharField(source='get_understand_status_display', read_only=True)
    profile = serializers.SerializerMethodField()
    case_count = serializers.SerializerMethodField()
    created_at = LocalDateTimeField(read_only=True)
    updated_at = LocalDateTimeField(read_only=True)

    class Meta:
        model = AgentProject
        fields = (
            'id',
            'name',
            'path',
            'agent_url',
            'buried_point_url',
            'understand_status',
            'understand_status_label',
            'profile',
            'case_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_profile(self, obj):
        try:
            profile = obj.profile
        except AgentProjectProfile.DoesNotExist:
            return None
        return AgentProjectProfileSerializer(profile).data

    def get_case_count(self, obj):
        value = getattr(obj, 'case_count', None)
        if value is not None:
            return value
        return obj.test_cases.count()


class AgentTestCaseSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    verify_status_label = serializers.CharField(source='get_verify_status_display', read_only=True)
    created_at = LocalDateTimeField(read_only=True)
    updated_at = LocalDateTimeField(read_only=True)
    last_run_at = LocalDateTimeField(read_only=True)
    # 列表轻量字段：最终 Agent 输出（不返回完整 last_run_detail）
    last_run_output = serializers.SerializerMethodField()
    # 多轮：每一轮用户输入与对应输出
    dialogue_turns = serializers.SerializerMethodField()
    # 列表默认不带巨大 detail；详情接口再返回
    include_detail = False

    class Meta:
        model = AgentTestCase
        fields = (
            'id',
            'project_id',
            'project_name',
            'task_name',
            'session_id',
            'tool_chain',
            'knowledge_base',
            'expected_result',
            'verify_status',
            'verify_status_label',
            'score',
            'level',
            'test_reason',
            'dimensions',
            'user_input',
            'dialogue_turns',
            'last_run_output',
            'last_run_result',
            'last_run_detail',
            'last_run_at',
            'source_type',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_last_run_output(self, obj):
        detail = obj.last_run_detail or {}
        if isinstance(detail, dict):
            text = detail.get('actual_answer') or ''
            if text:
                return str(text)
            turns = detail.get('turns') or []
            if isinstance(turns, list) and turns:
                answers = [str(t.get('answer') or '') for t in turns if isinstance(t, dict) and t.get('answer')]
                if answers:
                    return '\n\n'.join(answers)
            chat = detail.get('chat_result') or {}
            if isinstance(chat, dict):
                return str(chat.get('response') or chat.get('answer') or '')
        return ''

    def get_dialogue_turns(self, obj):
        return build_dialogue_turns(obj.user_input or '', obj.last_run_detail or {})

    def get_fields(self):
        fields = super().get_fields()
        include = self.context.get('include_detail', False)
        if not include:
            fields.pop('last_run_detail', None)
        return fields


class AgentTestRunListSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    case_id = serializers.IntegerField(read_only=True)
    task_name = serializers.CharField(source='case.task_name', read_only=True)
    verify_status_label = serializers.CharField(source='get_verify_status_display', read_only=True)
    created_at = LocalDateTimeField(read_only=True)

    class Meta:
        model = AgentTestRun
        fields = (
            'id',
            'project_id',
            'project_name',
            'case_id',
            'task_name',
            'request_id',
            'verify_status',
            'verify_status_label',
            'score',
            'elapsed_ms',
            'summary',
            'created_at',
        )
        read_only_fields = fields


class AgentTestRunDetailSerializer(AgentTestRunListSerializer):
    class Meta(AgentTestRunListSerializer.Meta):
        fields = AgentTestRunListSerializer.Meta.fields + ('detail',)
