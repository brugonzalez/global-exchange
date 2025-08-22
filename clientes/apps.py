from django.apps import AppConfig


class ConfiguracionClientes(AppConfig):
    """Configuración de la aplicación **clientes**.

    Esta clase define los metadatos y la configuración por defecto
    para la app de clientes. Django la utiliza para registrar la app
    en el proyecto.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clientes'