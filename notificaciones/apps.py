from django.apps import AppConfig


class ConfiguracionNotificaciones(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notificaciones'
    
    def ready(self):
        import notificaciones.signals