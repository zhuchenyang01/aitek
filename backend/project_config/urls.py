from django.urls import path
from .views import config_list_create, config_detail

urlpatterns = [
    path('', config_list_create, name='project-config-list-create'),
    path('<int:pk>/', config_detail, name='project-config-detail'),
]
