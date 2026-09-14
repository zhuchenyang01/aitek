from django.apps import AppConfig


class FunctionalTestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'functional_test'
    verbose_name = '功能测试'
