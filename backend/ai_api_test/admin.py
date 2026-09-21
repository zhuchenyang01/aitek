from django.contrib import admin

from .models import (
    ApiInterface,
    ApiInterfaceData,
    ApiTestCase,
    ApiTestRun,
    ApiTestRunLog,
    ApiTestSuite,
)


@admin.register(ApiInterface)
class ApiInterfaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'method', 'url', 'project', 'version', 'user', 'created_at')
    list_filter = ('method', 'source_type')
    search_fields = ('name', 'url', 'uid')


@admin.register(ApiInterfaceData)
class ApiInterfaceDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'interface', 'description', 'user', 'created_at')
    search_fields = ('description',)


@admin.register(ApiTestCase)
class ApiTestCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'interface', 'priority', 'source_type', 'user', 'created_at')
    list_filter = ('priority', 'source_type')
    search_fields = ('name', 'description')


@admin.register(ApiTestRunLog)
class ApiTestRunLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'run_id', 'event', 'outcome', 'case', 'user', 'created_at')
    list_filter = ('outcome', 'event')
    search_fields = ('run_id', 'message', 'test_name')


@admin.register(ApiTestSuite)
class ApiTestSuiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'project', 'user', 'created_at')
    search_fields = ('name',)


@admin.register(ApiTestRun)
class ApiTestRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status', 'total', 'passed', 'failed', 'user', 'started_at')
    list_filter = ('status',)
