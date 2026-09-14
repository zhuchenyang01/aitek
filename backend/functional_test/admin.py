from django.contrib import admin

from .models import FunctionalProject, RequirementDocument


@admin.register(FunctionalProject)
class FunctionalProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')


@admin.register(RequirementDocument)
class RequirementDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'title', 'source_filename', 'created_at')
