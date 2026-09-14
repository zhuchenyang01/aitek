from django.urls import path
from .views.login_views import login, register, logout
from .views.llm_views import (
    llm_config_detail,
    llm_config_list_create,
    llm_config_set_default,
    llm_config_test,
    ollama_models,
)

urlpatterns = [
    path('login/', login, name='system-login'),
    path('register/', register, name='system-register'),
    path('logout/', logout, name='system-logout'),
    path('llm-configs/', llm_config_list_create, name='system-llm-configs'),
    path('llm-configs/test/', llm_config_test, name='system-llm-config-test'),
    path('ollama/models/', ollama_models, name='system-ollama-models'),
    path('llm-configs/<int:pk>/', llm_config_detail, name='system-llm-config-detail'),
    path('llm-configs/<int:pk>/default/', llm_config_set_default, name='system-llm-config-default'),
]
