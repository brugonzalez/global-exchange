from django.apps import AppConfig


class ConfiguracionTransacciones(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transacciones'
    
# apps.py
from django.apps import AppConfig

class TuAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transacciones'  # Cambia por el nombre de tu app
    
    def ready(self):
        """
        Método que se ejecuta cuando la app está lista.
        Importa los signals aquí para asegurar que se registren.
        """
        import transacciones.signals  # Asegúrate de que los signals se importen