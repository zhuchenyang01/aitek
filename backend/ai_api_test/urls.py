from django.urls import path
from .views import health

urlpatterns = [
    path('health/', health, name='ai_api_test-health'),
]
