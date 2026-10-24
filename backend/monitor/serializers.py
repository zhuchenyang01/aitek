from django.utils.timezone import localtime
from rest_framework import serializers

from .crypto_util import encrypt_password
from .models import MetricSample, MonitorServer


def format_local_datetime(value):
    if not value:
        return None
    return localtime(value).strftime('%Y-%m-%d %H:%M:%S')


class MonitorServerSerializer(serializers.ModelSerializer):
    create_time = serializers.SerializerMethodField()
    update_time = serializers.SerializerMethodField()
    last_collect_at = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = MonitorServer
        fields = (
            'id',
            'name',
            'host',
            'port',
            'username',
            'auth_type',
            'enabled',
            'collect_interval',
            'last_status',
            'last_error',
            'last_collect_at',
            'has_password',
            'create_time',
            'update_time',
        )
        read_only_fields = fields

    def get_create_time(self, obj):
        return format_local_datetime(obj.create_time)

    def get_update_time(self, obj):
        return format_local_datetime(obj.update_time)

    def get_last_collect_at(self, obj):
        return format_local_datetime(obj.last_collect_at)

    def get_has_password(self, obj):
        return bool(obj.password_enc)


class MonitorServerWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    host = serializers.CharField(max_length=255)
    port = serializers.IntegerField(min_value=1, max_value=65535, default=22)
    username = serializers.CharField(max_length=128)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    enabled = serializers.BooleanField(required=False, default=False)
    collect_interval = serializers.IntegerField(min_value=3, max_value=3600, required=False, default=5)

    def validate_host(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('主机不能为空')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', '') or ''
        if not password:
            raise serializers.ValidationError({'password': '请输入 SSH 密码'})
        user = self.context['request'].user
        return MonitorServer.objects.create(
            user=user,
            name=validated_data['name'].strip(),
            host=validated_data['host'],
            port=validated_data.get('port') or 22,
            username=validated_data['username'].strip(),
            auth_type=MonitorServer.AUTH_PASSWORD,
            password_enc=encrypt_password(password),
            enabled=validated_data.get('enabled', False),
            collect_interval=validated_data.get('collect_interval') or 5,
        )

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name).strip()
        instance.host = validated_data.get('host', instance.host)
        instance.port = validated_data.get('port', instance.port) or 22
        instance.username = validated_data.get('username', instance.username).strip()
        if 'enabled' in validated_data:
            instance.enabled = validated_data['enabled']
        if 'collect_interval' in validated_data and validated_data['collect_interval']:
            instance.collect_interval = validated_data['collect_interval']
        password = validated_data.get('password')
        if password:
            instance.password_enc = encrypt_password(password)
        instance.save()
        return instance


class MetricSampleSerializer(serializers.ModelSerializer):
    collected_at = serializers.SerializerMethodField()

    class Meta:
        model = MetricSample
        fields = (
            'id',
            'collected_at',
            'cpu_percent',
            'load1',
            'load5',
            'load15',
            'mem_total',
            'mem_used',
            'mem_percent',
            'swap_percent',
            'disk_percent',
            'disk_read_bps',
            'disk_write_bps',
            'net_rx_bps',
            'net_tx_bps',
        )

    def get_collected_at(self, obj):
        return format_local_datetime(obj.collected_at)
