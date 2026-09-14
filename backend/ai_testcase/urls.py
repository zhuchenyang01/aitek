from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health, name='ai_testcase-health'),
    path('sessions/', views.session_list_create, name='ai_testcase-sessions'),
    path('sessions/<int:pk>/', views.session_detail, name='ai_testcase-session-detail'),
    path('sessions/<int:pk>/messages/', views.session_messages, name='ai_testcase-session-messages'),
    path('knowledge-bases/', views.knowledge_base_list_create, name='ai_testcase-knowledge-bases'),
    path('knowledge-bases/<int:pk>/', views.knowledge_base_detail, name='ai_testcase-knowledge-base-detail'),
    path('knowledge-bases/<int:pk>/documents/', views.knowledge_base_documents, name='ai_testcase-knowledge-base-docs'),
    path(
        'knowledge-bases/<int:pk>/documents/<int:doc_id>/',
        views.knowledge_base_document_detail,
        name='ai_testcase-knowledge-base-doc-detail',
    ),
    path('knowledge-bases/<int:pk>/chunks/', views.knowledge_base_chunks, name='ai_testcase-knowledge-base-chunks'),
    path('eval/template.xlsx', views.eval_template, name='ai_testcase-eval-template'),
    path('eval/parse/', views.eval_parse, name='ai_testcase-eval-parse'),
    path('eval/run/', views.eval_run, name='ai_testcase-eval-run'),
    path('qa/', views.qa_list_create, name='ai_testcase-qa'),
    path('qa/<int:pk>/', views.qa_detail, name='ai_testcase-qa-detail'),
    path('qa/<int:pk>/ask/', views.qa_ask, name='ai_testcase-qa-ask'),
]
