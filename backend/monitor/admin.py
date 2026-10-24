from django.contrib import admin

from .models import MetricSample, MonitorServer


@admin.register(MonitorServer)
class MonitorServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'host', 'port', 'username', 'enabled', 'last_status', 'user')
    list_filter = ('enabled', 'last_status')
    search_fields = ('name', 'host', 'username')


@admin.register(MetricSample)
class MetricSampleAdmin(admin.ModelAdmin):
    list_display = ('id', 'server', 'collected_at', 'cpu_percent', 'mem_percent', 'disk_percent')
    list_filter = ('server',)
