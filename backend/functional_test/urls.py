from django.urls import path

from . import views

urlpatterns = [
    path('projects/', views.project_list_create, name='functional-project-list-create'),
    path('projects/<int:pk>/', views.project_detail, name='functional-project-detail'),
    path('projects/<int:pk>/requirements/', views.project_requirements, name='functional-project-requirements'),
    path(
        'projects/<int:pk>/requirements/<int:doc_id>/',
        views.project_requirement_detail,
        name='functional-project-requirement-detail',
    ),
    path(
        'projects/<int:pk>/requirements/<int:doc_id>/generate/',
        views.requirement_generate,
        name='functional-project-requirement-generate',
    ),
    path('testcases/', views.testcase_list, name='functional-testcase-list'),
    path('testcases/export/', views.testcase_export, name='functional-testcase-export'),
    path('testcases/batch-delete/', views.testcase_batch_delete, name='functional-testcase-batch-delete'),
    path('testcases/<int:pk>/', views.testcase_detail, name='functional-testcase-detail'),
]
