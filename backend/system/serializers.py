from django.contrib.auth.models import User
from rest_framework import serializers

from system.llm import apply_provider_defaults, is_local_source, mask_api_key
from system.models import UserLLMConfig


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(min_length=6, write_only=True)

    def validate_username(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('用户名不能为空')
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': '两次输入的密码不一致'})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserLLMConfigSerializer(serializers.ModelSerializer):
    api_key_masked = serializers.SerializerMethodField()
    has_api_key = serializers.SerializerMethodField()
    provider_label = serializers.CharField(source='get_provider_display', read_only=True)
    model_type_label = serializers.CharField(source='get_model_type_display', read_only=True)
    source_label = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model = UserLLMConfig
        fields = (
            'id',
            'model_type',
            'model_type_label',
            'source',
            'source_label',
            'name',
            'provider',
            'provider_label',
            'model',
            'base_url',
            'api_key_masked',
            'has_api_key',
            'dimension',
            'is_default',
            'created_at',
            'updated_at',
        )

    def get_api_key_masked(self, obj):
        return mask_api_key(obj.api_key)

    def get_has_api_key(self, obj):
        return bool((obj.api_key or '').strip()) or is_local_source(obj)


class LLMConfigWriteSerializer(serializers.Serializer):
    model_type = serializers.ChoiceField(choices=UserLLMConfig.TYPE_CHOICES, required=False)
    source = serializers.ChoiceField(choices=UserLLMConfig.SOURCE_CHOICES, required=False)
    name = serializers.CharField(required=False, allow_blank=True, max_length=128)
    provider = serializers.ChoiceField(choices=UserLLMConfig.PROVIDER_CHOICES, required=False)
    model = serializers.CharField(required=False, allow_blank=True, max_length=128)
    base_url = serializers.CharField(required=False, allow_blank=True, max_length=512)
    api_key = serializers.CharField(required=False, allow_blank=True, max_length=512)
    dimension = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    is_default = serializers.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        partial = bool(self.instance)
        if partial:
            merged = {
                'model_type': self.instance.model_type,
                'source': self.instance.source,
                'provider': self.instance.provider,
                'model': self.instance.model,
                'base_url': self.instance.base_url,
                'api_key': self.instance.api_key,
                'name': self.instance.name,
            }
            merged.update(attrs)
        else:
            merged = dict(attrs)
            merged.setdefault('model_type', UserLLMConfig.TYPE_CHAT)
            merged.setdefault('source', UserLLMConfig.SOURCE_API)
            merged.setdefault('provider', UserLLMConfig.PROVIDER_CUSTOM)

        apply_provider_defaults(merged)
        model = (merged.get('model') or '').strip()
        base_url = (merged.get('base_url') or '').strip()
        api_key = (merged.get('api_key') or '').strip()
        provider = merged['provider']
        source = merged['source']
        model_type = merged['model_type']

        if not model:
            raise serializers.ValidationError({'model': '请填写模型名'})
        if not base_url:
            raise serializers.ValidationError({'base_url': '请填写接口地址'})

        local = source == UserLLMConfig.SOURCE_OLLAMA or provider == UserLLMConfig.PROVIDER_OLLAMA
        if not local and not api_key and not partial:
            raise serializers.ValidationError({'api_key': '请填写 API Key'})
        if not local and not api_key and partial and not (self.instance.api_key or '').strip():
            raise serializers.ValidationError({'api_key': '请填写 API Key'})

        name = (merged.get('name') or '').strip()
        if not name:
            type_label = dict(UserLLMConfig.TYPE_CHOICES).get(model_type, model_type)
            name = f'{type_label} / {model}'
        attrs['name'] = name
        attrs['model_type'] = model_type
        attrs['source'] = source
        attrs['provider'] = provider
        attrs['model'] = model
        attrs['base_url'] = base_url.rstrip('/')
        if 'api_key' in attrs:
            if api_key:
                attrs['api_key'] = api_key
            else:
                attrs.pop('api_key')
        elif not partial:
            attrs['api_key'] = api_key
        return attrs


class LLMConfigTestSerializer(LLMConfigWriteSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
