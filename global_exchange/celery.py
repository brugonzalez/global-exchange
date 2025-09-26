# global_exchange/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Establecer la configuración de Django por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_exchange.settings')

app = Celery('global_exchange')

# Configurar Celery usando la configuración de Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en todas las apps instaladas
app.autodiscover_tasks()

# Configurar la tarea periódica
app.conf.beat_schedule = {
    'expirar-transacciones-cada-minuto': {
        'task': 'transacciones.tasks.expirar_transacciones_pendientes',
        'schedule': crontab(minute='*/1'),
    },
}

app.conf.timezone = 'America/Mexico_City'  # Ajusta tu zona horaria