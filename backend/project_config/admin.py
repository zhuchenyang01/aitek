from django.contrib import admin
from .models import ProjectConfig


@admin.register(ProjectConfig)
class ProjectConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'value', 'remark', 'create_time')
    search_fields = ('key', 'value', 'remark')
    list_filter = ('create_time',)
