from rest_framework import serializers
from .models import ProjectConfig


class ProjectConfigSerializer(serializers.ModelSerializer):
    create_time = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProjectConfig
        fields = ('id', 'key', 'value', 'remark', 'create_time')
        extra_kwargs = {
            'key': {'validators': []},
        }

    def get_create_time(self, obj):
        if not obj.create_time:
            return ''
        return f'{obj.create_time.year}年{obj.create_time.month}月{obj.create_time.day}日'

    def validate_key(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('KEY 不能为空')
        qs = ProjectConfig.objects.filter(key=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('KEY 已存在')
        return value

    def validate_value(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('VALUE 不能为空')
        return value
