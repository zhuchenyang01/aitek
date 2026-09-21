import json

from rest_framework import serializers

from functional_test.models import FunctionalProject
from functional_test.serializers import format_local_datetime, user_display_name

from .models import ApiInterface, ApiInterfaceData, ApiTestCase

METHODS = {item[0] for item in ApiInterface.METHOD_CHOICES}


class ApiInterfaceListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = ApiInterface
        fields = (
            'id',
            'uid',
            'name',
            'method',
            'url',
            'path',
            'version',
            'project_id',
            'project_name',
            'source_type',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_created_at(self, obj):
        return format_local_datetime(obj.created_at)

    def get_updated_at(self, obj):
        return format_local_datetime(obj.updated_at)


class ApiInterfaceDetailSerializer(ApiInterfaceListSerializer):
    creator_name = serializers.SerializerMethodField()

    class Meta(ApiInterfaceListSerializer.Meta):
        fields = ApiInterfaceListSerializer.Meta.fields + (
            'host',
            'protocol',
            'description',
            'headers',
            'query_params',
            'path_params',
            'body_mode',
            'body_raw',
            'body_form',
            'auth_type',
            'auth_config',
            'content_type',
            'timeout_ms',
            'request_example',
            'response_status',
            'response_headers',
            'response_body',
            'cookies',
            'setup_script',
            'teardown_script',
            'source_filename',
            'creator_name',
        )

    def get_creator_name(self, obj):
        return user_display_name(getattr(obj, 'user', None))


class ApiInterfaceWriteSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    method = serializers.CharField(max_length=16)
    url = serializers.CharField(required=False, allow_blank=True, max_length=2048)
    path = serializers.CharField(required=False, allow_blank=True, max_length=1024)
    host = serializers.CharField(required=False, allow_blank=True, max_length=255)
    protocol = serializers.CharField(required=False, allow_blank=True, max_length=16)
    version = serializers.CharField(required=False, allow_blank=True, max_length=64)
    description = serializers.CharField(required=False, allow_blank=True)
    headers = serializers.JSONField(required=False)
    query_params = serializers.JSONField(required=False)
    path_params = serializers.JSONField(required=False)
    body_mode = serializers.CharField(required=False, allow_blank=True, max_length=32)
    body_raw = serializers.CharField(required=False, allow_blank=True)
    body_form = serializers.JSONField(required=False)
    auth_type = serializers.CharField(required=False, allow_blank=True, max_length=32)
    auth_config = serializers.JSONField(required=False)
    content_type = serializers.CharField(required=False, allow_blank=True, max_length=128)
    timeout_ms = serializers.IntegerField(required=False, min_value=1)
    request_example = serializers.CharField(required=False, allow_blank=True)
    response_status = serializers.CharField(required=False, allow_blank=True, max_length=16)
    response_headers = serializers.JSONField(required=False)
    response_body = serializers.CharField(required=False, allow_blank=True)
    cookies = serializers.JSONField(required=False)
    setup_script = serializers.CharField(required=False, allow_blank=True)
    teardown_script = serializers.CharField(required=False, allow_blank=True)

    def validate_method(self, value):
        method = (value or '').upper().strip()
        if method not in METHODS:
            raise serializers.ValidationError('不支持的请求方法')
        return method

    def validate_project_id(self, value):
        user = self.context['request'].user
        project = FunctionalProject.objects.filter(pk=value, user=user).first()
        if project is None:
            raise serializers.ValidationError('项目不存在')
        return value

    def validate_body_mode(self, value):
        mode = (value or 'none').strip() or 'none'
        allowed = {item[0] for item in ApiInterface.BODY_MODE_CHOICES}
        if mode not in allowed:
            raise serializers.ValidationError('不支持的请求体类型')
        return mode

    def validate_auth_type(self, value):
        auth = (value or 'none').strip() or 'none'
        allowed = {item[0] for item in ApiInterface.AUTH_CHOICES}
        if auth not in allowed:
            raise serializers.ValidationError('不支持的鉴权类型')
        return auth


class ApiDocImportSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    version = serializers.CharField(required=False, allow_blank=True, max_length=64)
    file = serializers.FileField()

    def validate_project_id(self, value):
        user = self.context['request'].user
        if not FunctionalProject.objects.filter(pk=value, user=user).exists():
            raise serializers.ValidationError('项目不存在')
        return value

    def validate_file(self, uploaded):
        filename = (getattr(uploaded, 'name', None) or '').strip()
        if not filename.lower().endswith(('.json', '.txt', '.docx')):
            raise serializers.ValidationError('请上传 JSON 或 Word（.docx）接口文档')
        if filename.lower().endswith('.doc'):
            raise serializers.ValidationError('暂仅支持 .docx，请先转换为 docx')
        return uploaded


class ApiInterfaceDataSerializer(serializers.ModelSerializer):
    interface_id = serializers.IntegerField()
    payload = serializers.JSONField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = ApiInterfaceData
        fields = (
            'id',
            'interface_id',
            'description',
            'payload',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_created_at(self, obj):
        return format_local_datetime(obj.created_at)

    def get_updated_at(self, obj):
        return format_local_datetime(obj.updated_at)

    def validate_description(self, value):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('请填写数据描述')
        return text

    def validate_payload(self, value):
        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise serializers.ValidationError('请填写 JSON 数据')
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                raise serializers.ValidationError('数据必须是合法 JSON')
        if not isinstance(value, (dict, list)):
            raise serializers.ValidationError('数据必须是 JSON 对象或数组')
        return value

    def validate_interface_id(self, value):
        user = self.context['request'].user
        if not ApiInterface.objects.filter(pk=value, user=user).exists():
            raise serializers.ValidationError('关联接口不存在')
        return value


PRIORITIES = {item[0] for item in ApiTestCase.PRIORITY_CHOICES}


class ApiTestCaseSerializer(serializers.ModelSerializer):
    interface_id = serializers.IntegerField()
    interface_name = serializers.CharField(source='interface.name', read_only=True)
    interface_method = serializers.CharField(source='interface.method', read_only=True)
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = ApiTestCase
        fields = (
            'id',
            'interface_id',
            'interface_name',
            'interface_method',
            'name',
            'priority',
            'case_type',
            'description',
            'preconditions',
            'request_headers',
            'request_query',
            'request_body',
            'expected_status',
            'expected_body',
            'assertions',
            'source_type',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'interface_name', 'interface_method', 'source_type', 'created_at', 'updated_at')

    def get_created_at(self, obj):
        return format_local_datetime(obj.created_at)

    def get_updated_at(self, obj):
        return format_local_datetime(obj.updated_at)

    def validate_name(self, value):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('请填写用例名称')
        return text

    def validate_priority(self, value):
        priority = (value or 'P2').upper().strip()
        if priority not in PRIORITIES:
            raise serializers.ValidationError('优先级无效')
        return priority

    def validate_interface_id(self, value):
        user = self.context['request'].user
        if not ApiInterface.objects.filter(pk=value, user=user).exists():
            raise serializers.ValidationError('关联接口不存在')
        return value
