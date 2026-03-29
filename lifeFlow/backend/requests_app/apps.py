from django.apps import AppConfig


class RequestsAppConfig(AppConfig):
    name = 'requests_app'

    def ready(self):
        import requests_app.signals  # noqa: F401
