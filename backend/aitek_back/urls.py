"""
URL configuration for aitek_back project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def test_api(request):
    return JsonResponse({"msg": "前后端连通成功！"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/test/', test_api),
    path('api/system/', include('system.urls')),
    path('api/ai-testcase/', include('ai_testcase.urls')),
    path('api/ai-api-test/', include('ai_api_test.urls')),
    path('api/ai-web-test/', include('ai_web_test.urls')),
    path('api/ai-app-test/', include('ai_app_test.urls')),
    path('api/ci/', include('ci.urls')),
    path('api/project-config/', include('project_config.urls')),
    path('api/functional-test/', include('functional_test.urls')),
]
