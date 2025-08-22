from django.apps import AppConfig


class TauserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tauser'

    def ready(self):
        """Importar signals cuando la aplicación esté lista."""
        import cuentas.signals