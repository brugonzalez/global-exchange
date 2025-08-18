"""
Configuración WSGI para el proyecto global_exchange.

Expone el llamable WSGI como una variable a nivel de módulo llamada ``application``.

Para más información sobre este archivo, ver
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_exchange.settings')

application = get_wsgi_application()