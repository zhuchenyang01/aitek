from pathlib import Path

from rest_framework import serializers
from django.utils.timezone import localtime

from .models import FunctionalProject, FunctionalTestCase, RequirementDocument, TestCaseGeneration

ALLOWED_EXTENSIONS = {'.pdf', '.docx'}


def format_local_datetime(value):
    if not value:
        return ''
    return localtime(value).strftime('%Y-%m-%d %H:%M:%S')


class LocalDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        return format_local_datetime(value)


def user_display_name(user):
    if user is None:
        return ''
    full = f'{(user.first_name or "").strip()} {(user.last_name or "").strip()}'.strip()
    return full or (user.username or '')


class RequirementDocumentSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()
    created_at = LocalDateTimeField(read_only=True)

    class Meta:
        model = RequirementDocument
        fields = (
            'id',
            'project_id',
            'title',
            'source_filename',
            'file',
            'creator_name',
            'created_at',
        )
        read_only_fields = fields

    def get_creator_name(self, obj):
        return user_display_name(getattr(obj, 'user', None))


class CreateRequirementDocumentSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    file = serializers.FileField()

    def validate_file(self, uploaded):
        filename = (getattr(uploaded, 'name', None) or '').strip()
        suffix = Path(filename).suffix.lower()
        if suffix == '.doc':
            raise serializers.ValidationError('暂仅支持 .docx，请先转换为 docx')
        if suffix not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError('仅支持 pdf 或 docx 文件')
        return uploaded


class CreateFunctionalProjectSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)


class UpdateFunctionalProjectSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)


class UpdateRequirementDocumentSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)

    def validate_title(self, value):
        title = (value or '').strip()
        if not title:
            raise serializers.ValidationError('请输入文档名称')
        return title


class GenerateRequirementSerializer(serializers.Serializer):
    query = serializers.CharField(required=False, allow_blank=True)
    llm_config_id = serializers.IntegerField(required=False, allow_null=True)
    stream = serializers.BooleanField(required=False, default=False)

    def validate_query(self, value):
        return (value or '').strip()


class FunctionalProjectSerializer(serializers.ModelSerializer):
    requirement_count = serializers.IntegerField(read_only=True)
    requirements = RequirementDocumentSerializer(many=True, read_only=True)
    creator_name = serializers.SerializerMethodField()
    created_at = LocalDateTimeField(read_only=True)
    updated_at = LocalDateTimeField(read_only=True)

    class Meta:
        model = FunctionalProject
        fields = (
            'id',
            'name',
            'description',
            'requirement_count',
            'requirements',
            'creator_name',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_creator_name(self, obj):
        return user_display_name(getattr(obj, 'user', None))


class FunctionalTestCaseSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    requirement_id = serializers.IntegerField(read_only=True)
    requirement_title = serializers.SerializerMethodField()
    generation_id = serializers.IntegerField(read_only=True)
    creator_name = serializers.SerializerMethodField()
    created_at = LocalDateTimeField(read_only=True)

    class Meta:
        model = FunctionalTestCase
        fields = (
            'id',
            'generation_id',
            'project_id',
            'project_name',
            'requirement_id',
            'requirement_title',
            'case_no',
            'module',
            'title',
            'precondition',
            'steps',
            'expected_result',
            'priority',
            'sort_order',
            'creator_name',
            'created_at',
        )
        read_only_fields = fields

    def get_requirement_title(self, obj):
        requirement = obj.requirement
        return (requirement.title or requirement.source_filename or '').strip()

    def get_creator_name(self, obj):
        return user_display_name(getattr(obj, 'user', None))


class FunctionalTestCaseListSerializer(FunctionalTestCaseSerializer):
    precondition = serializers.SerializerMethodField()
    steps = serializers.SerializerMethodField()
    expected_result = serializers.SerializerMethodField()

    def _clip(self, value):
        text = value or ''
        if len(text) > 240:
            return text[:240] + '…'
        return text

    def get_precondition(self, obj):
        return self._clip(getattr(obj, '_precondition_preview', None))

    def get_steps(self, obj):
        return self._clip(getattr(obj, '_steps_preview', None))

    def get_expected_result(self, obj):
        return self._clip(getattr(obj, '_expected_preview', None))
