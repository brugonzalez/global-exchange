from django.apps import AppConfig


class ConfiguracionDivisas(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'divisas'

    def ready(self):
        import divisas.signals