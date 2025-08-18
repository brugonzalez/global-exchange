"""
Configuración ASGI para el proyecto global_exchange.

Expone el llamable ASGI como una variable a nivel de módulo llamada ``application``.

Para más información sobre este archivo, ver
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_exchange.settings')

application = get_asgi_application()