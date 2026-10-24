from django.urls import path

from . import views

urlpatterns = [
    path('projects/', views.project_list_create, name='agent-project-list-create'),
    path('projects/<int:pk>/', views.project_detail, name='agent-project-detail'),
    path('projects/<int:pk>/understand/', views.project_understand, name='agent-project-understand'),
    path('projects/<int:pk>/profile/', views.project_profile_update, name='agent-project-profile-update'),
    path('projects/<int:pk>/generate-cases/', views.project_generate_cases, name='agent-project-generate-cases'),
    path('cases/', views.case_list, name='agent-case-list'),
    path('cases/<int:pk>/run/', views.case_run, name='agent-case-run'),
    path('cases/<int:pk>/last-run/', views.case_last_run_detail, name='agent-case-last-run'),
    path('reports/', views.report_list, name='agent-report-list'),
    path('reports/<int:pk>/', views.report_detail, name='agent-report-detail'),
]
