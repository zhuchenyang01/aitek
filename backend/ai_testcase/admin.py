from django.contrib import admin

from .models import KnowledgeBase, KnowledgeDocument, TestCaseQA, TestCaseSession


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'kb_type', 'created_at')
    search_fields = ('name',)
    list_filter = ('kb_type', 'created_at')


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'knowledge_base', 'title', 'created_at')
    search_fields = ('title',)


@admin.register(TestCaseSession)
class TestCaseSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at')
    search_fields = ('title',)
    list_filter = ('created_at',)


@admin.register(TestCaseQA)
class TestCaseQAAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session', 'requirement_kb', 'testcase_kb', 'created_at')
    list_filter = ('created_at',)
