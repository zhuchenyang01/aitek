from django.urls import path

from . import views

urlpatterns = [
    path('servers/', views.server_list_create, name='monitor-server-list-create'),
    path('servers/<int:pk>/', views.server_detail, name='monitor-server-detail'),
    path('servers/<int:pk>/test/', views.server_test, name='monitor-server-test'),
    path('servers/<int:pk>/collect/', views.server_collect, name='monitor-server-collect'),
    path('servers/<int:pk>/metrics/', views.server_metrics, name='monitor-server-metrics'),
    path('servers/<int:pk>/latest/', views.server_latest, name='monitor-server-latest'),
]
