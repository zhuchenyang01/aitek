from django.urls import path

from . import suite_views, views

urlpatterns = [
    path('health/', views.health, name='ai_api_test-health'),
    path('interfaces/', views.interface_list_create, name='api-interface-list-create'),
    path('interfaces/import/', views.interface_import, name='api-interface-import'),
    path('interfaces/<int:pk>/', views.interface_detail, name='api-interface-detail'),
    path('interfaces/<int:pk>/generate-cases/stream/', views.interface_generate_cases_stream, name='api-interface-generate-cases-stream'),
    path('interfaces/<int:pk>/generate-cases/', views.interface_generate_cases, name='api-interface-generate-cases'),
    path('datasets/', views.dataset_list_create, name='api-dataset-list-create'),
    path('datasets/<int:pk>/', views.dataset_detail, name='api-dataset-detail'),
    path('cases/', views.case_list_create, name='api-case-list-create'),
    path('cases/<int:pk>/run/', views.case_run, name='api-case-run'),
    path('cases/<int:pk>/logs/', views.case_run_logs, name='api-case-run-logs'),
    path('cases/<int:pk>/', views.case_detail, name='api-case-detail'),
    path('suites/', suite_views.suite_list_create, name='api-suite-list-create'),
    path('suites/<int:pk>/run/', suite_views.suite_run, name='api-suite-run'),
    path('suites/<int:pk>/', suite_views.suite_detail, name='api-suite-detail'),
    path('runs/', suite_views.run_list, name='api-run-list'),
    path('runs/<int:pk>/', suite_views.run_detail, name='api-run-detail'),
]
