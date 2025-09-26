def expirar_automaticamente(self):
        """Marca la transacción como expirada automáticamente"""
        if self.ha_expirado and self.estado == 'PENDIENTE':
            self.estado = 'CANCELADA'
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = f"Expirada automáticamente después de {self.tiempo_expiracion_minutos} minutos"
            self.save()
            
            # Enviar notificación de expiración
            try:
                from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
                llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_EXPIRADA')
            except Exception as e:
                logger.error(f"Error al enviar notificación de expiración: {e}")
            
            return True
        return False

podrias hacer que esta funcion se ejecute cada minuto dentro de django?
Sí, hay varias formas de ejecutar esta función cada minuto en Django. Te muestro las opciones más comunes:

Opción 1: Usando Celery (Recomendado)
1. Instalar Celery
bash
pip install celery redis
2. Configurar Celery en settings.py
python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TIMEZONE = 'America/Mexico_City'  # Ajusta a tu zona horaria
3. Crear celery.py en tu proyecto
python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tu_proyecto.settings')

app = Celery('tu_proyecto')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configurar la tarea periódica
app.conf.beat_schedule = {
    'expirar-transacciones-cada-minuto': {
        'task': 'tu_app.tasks.expirar_transacciones_automaticamente',
        'schedule': crontab(minute='*/1'),  # Cada minuto
    },
}
4. Crear la tarea en tu_app/tasks.py
python
from celery import shared_task
from django.utils import timezone
from .models import TuModeloTransaccion  # Ajusta según tu modelo
import logging

logger = logging.getLogger(__name__)

@shared_task
def expirar_transacciones_automaticamente():
    """Tarea que expira transacciones pendientes cada minuto"""
    try:
        transacciones_pendientes = TuModeloTransaccion.objects.filter(
            estado='PENDIENTE'
        )
        
        expiradas_count = 0
        for transaccion in transacciones_pendientes:
            if transaccion.expirar_automaticamente():
                expiradas_count += 1
        
        logger.info(f"Proceso de expiración completado. Transacciones expiradas: {expiradas_count}")
        return f"Expiradas: {expiradas_count}"
        
    except Exception as e:
        logger.error(f"Error en expirar_transacciones_automaticamente: {e}")
        return f"Error: {e}"
Opción 2: Usando Django-Q (Alternativa más simple)
1. Instalar Django-Q
bash
pip install django-q
2. Agregar a INSTALLED_APPS
python
INSTALLED_APPS = [
    # ...
    'django_q',
]
3. Configurar en settings.py
python
Q_CLUSTER = {
    'name': 'DjangoQ',
    'workers': 4,
    'recycle': 500,
    'timeout': 60,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'redis': {
        'host': '127.0.0.1',
        'port': 6379,
        'db': 0,
    }
}
4. Crear el schedule en tu_app/management/commands/setup_schedules.py
python
from django.core.management.base import BaseCommand
from django_q.models import Schedule
from django.utils import timezone

class Command(BaseCommand):
    help = 'Configura las tareas programadas'
    
    def handle(self, *args, **options):
        Schedule.objects.update_or_create(
            name='Expirar Transacciones',
            defaults={
                'func': 'tu_app.tasks.expirar_transacciones_automaticamente',
                'schedule_type': Schedule.MINUTES,
                'minutes': 1,
                'repeats': -1,  # Se repite indefinidamente
                'next_run': timezone.now(),
            }
        )
        self.stdout.write('Tarea programada configurada correctamente')
Opción 3: Usando APScheduler (Ligero)
1. Instalar APScheduler
bash
pip install apscheduler
2. Crear scheduler.py en tu app
python
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
import logging

logger = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Agregar la tarea
    scheduler.add_job(
        expirar_transacciones_automaticamente,
        trigger='interval',
        minutes=1,
        id='expirar_transacciones',
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Scheduler iniciado correctamente")
3. Agregar en apps.py de tu app
python
from django.apps import AppConfig

class TuAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tu_app'
    
    def ready(self):
        if not os.environ.get('RUN_MAIN'):
            return
        from . import scheduler
        scheduler.start_scheduler()
Modificación de tu función original
Te recomiendo modificar ligeramente tu función para que sea más eficiente:

python
def expirar_automaticamente(self):
    """Marca la transacción como expirada automáticamente"""
    # Verificar si ya está cancelada para evitar procesamiento innecesario
    if self.estado == 'CANCELADA':
        return False
        
    if self.ha_expirado and self.estado == 'PENDIENTE':
        self.estado = 'CANCELADA'
        self.fecha_cancelacion = timezone.now()
        self.motivo_cancelacion = f"Expirada automáticamente después de {self.tiempo_expiracion_minutos} minutos"
        self.save()
        
        # Enviar notificación de expiración
        try:
            from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
            llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_EXPIRADA')
        except Exception as e:
            logger.error(f"Error al enviar notificación de expiración: {e}")
        
        return True
    return False
Recomendación
Celery es la opción más robusta y utilizada en producción. Django-Q es buena si quieres algo más simple. APScheduler es ligero pero requiere más configuración manual.

¿Te gustaría que profundice en alguna de estas opciones o necesitas ayuda con la implementación específica?

expirar_transacciones_automaticamente
no quiero que tengas en cuenta esta funcion para el scheduler solo la que te pase
Entiendo. Quieres ejecutar la función expirar_automaticamente que ya tienes en tu modelo, pero a nivel de todas las transacciones pendientes. Te muestro cómo adaptar el scheduler:

Opción 1: Celery (Recomendado)
En tu_app/tasks.py:
python
from celery import shared_task
from django.utils import timezone
from .models import TuModeloTransaccion  # Ajusta según tu modelo
import logging

logger = logging.getLogger(__name__)

@shared_task
def expirar_transacciones_pendientes():
    """Ejecuta expirar_automaticamente() en todas las transacciones pendientes"""
    try:
        # Obtener solo transacciones pendientes para optimizar
        transacciones_pendientes = TuModeloTransaccion.objects.filter(
            estado='PENDIENTE'
        )
        
        expiradas_count = 0
        for transaccion in transacciones_pendientes:
            # Aquí llamas a tu función original del modelo
            if transaccion.expirar_automaticamente():
                expiradas_count += 1
        
        logger.info(f"Proceso de expiración completado. Transacciones expiradas: {expiradas_count}")
        return f"Expiradas: {expiradas_count}"
        
    except Exception as e:
        logger.error(f"Error en expirar_transacciones_pendientes: {e}")
        return f"Error: {e}"
En celery.py (configuración del beat):
python
app.conf.beat_schedule = {
    'expirar-transacciones-cada-minuto': {
        'task': 'tu_app.tasks.expirar_transacciones_pendientes',
        'schedule': crontab(minute='*/1'),  # Cada minuto
    },
}
Opción 2: Django-Q
En tu_app/tasks.py:
python
def expirar_transacciones_pendientes():
    """Ejecuta expirar_automaticamente() en todas las transacciones pendientes"""
    from .models import TuModeloTransaccion  # Import dentro de la función para evitar circular imports
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        transacciones_pendientes = TuModeloTransaccion.objects.filter(
            estado='PENDIENTE'
        )
        
        expiradas_count = 0
        for transaccion in transacciones_pendientes:
            if transaccion.expirar_automaticamente():
                expiradas_count += 1
        
        logger.info(f"Transacciones expiradas: {expiradas_count}")
        return expiradas_count
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 0
Comando para configurar el schedule:
python
# management/commands/setup_schedules.py
from django.core.management.base import BaseCommand
from django_q.models import Schedule

class Command(BaseCommand):
    def handle(self, *args, **options):
        Schedule.objects.update_or_create(
            name='Expirar Transacciones Pendientes',
            defaults={
                'func': 'tu_app.tasks.expirar_transacciones_pendientes',
                'schedule_type': Schedule.MINUTES,
                'minutes': 1,
                'repeats': -1,
            }
        )
Opción 3: APScheduler
En tu_app/scheduler.py:
python
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
import logging

logger = logging.getLogger(__name__)

def expirar_transacciones_pendientes():
    """Función que se ejecutará cada minuto"""
    from .models import TuModeloTransaccion
    
    try:
        transacciones_pendientes = TuModeloTransaccion.objects.filter(
            estado='PENDIENTE'
        )
        
        expiradas_count = 0
        for transaccion in transacciones_pendientes:
            if transaccion.expirar_automaticamente():
                expiradas_count += 1
        
        logger.info(f"Transacciones expiradas: {expiradas_count}")
        
    except Exception as e:
        logger.error(f"Error en expirar_transacciones_pendientes: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    scheduler.add_job(
        expirar_transacciones_pendientes,
        trigger='interval',
        minutes=1,
        id='expirar_transacciones_pendientes',
        replace_existing=True,
    )
    
    scheduler.start()
Punto importante sobre optimización
Si tienes muchas transacciones, considera optimizar la consulta para evitar cargar todas en memoria:

python
@shared_task
def expirar_transacciones_pendientes():
    """Versión optimizada para muchos registros"""
    try:
        from django.db import transaction
        
        with transaction.atomic():
            # Seleccionar solo IDs para evitar cargar objetos completos
            transacciones_ids = TuModeloTransaccion.objects.filter(
                estado='PENDIENTE'
            ).values_list('id', flat=True)
            
            expiradas_count = 0
            for trans_id in transacciones_ids:
                try:
                    transaccion = TuModeloTransaccion.objects.get(id=trans_id)
                    if transaccion.expirar_automaticamente():
                        expiradas_count += 1
                except TuModeloTransaccion.DoesNotExist:
                    continue
            
        logger.info(f"Transacciones expiradas: {expiradas_count}")
        return expiradas_count
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 0
¿Cuál de estas opciones prefieres o necesitas que te ayude a implementar alguna en específico?

Hazme para celery
Te ayudo a implementar la solución con Celery. Aquí está la configuración completa:

1. Instalación de dependencias
bash
pip install celery redis
2. Configuración de Celery
Crear celery.py en la raíz de tu proyecto (al mismo nivel que settings.py)
python
# tu_proyecto/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Establecer la configuración de Django por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tu_proyecto.settings')

app = Celery('tu_proyecto')

# Configurar Celery usando la configuración de Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en todas las apps instaladas
app.autodiscover_tasks()

# Configurar la tarea periódica para expirar transacciones
app.conf.beat_schedule = {
    'expirar-transacciones-cada-minuto': {
        'task': 'tu_app.tasks.expirar_transacciones_pendientes',
        'schedule': crontab(minute='*/1'),  # Ejecutar cada minuto
        'options': {'queue': 'periodic_tasks'},  # Opcional: especificar cola
    },
}

# Configuración adicional
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Mexico_City',  # Ajusta a tu zona horaria
    enable_utc=True,
)
Modificar __init__.py en la raíz del proyecto
python
# tu_proyecto/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)
3. Configuración en settings.py
python
# settings.py
# Configuración de Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # O 'redis://redis:6379/0' si usas Docker
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Mexico_City'  # Ajusta a tu zona horaria

# Opcional: Configurar colas específicas
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_CREATE_MISSING_QUEUES = True
4. Crear la tarea en tu aplicación
python
# tu_app/tasks.py
from celery import shared_task
from django.utils import timezone
import logging
from .models import TuModeloTransaccion  # Ajusta al nombre real de tu modelo

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def expirar_transacciones_pendientes(self):
    """
    Tarea que ejecuta expirar_automaticamente() en todas las transacciones pendientes
    Se ejecuta cada minuto via Celery Beat
    """
    try:
        logger.info("Iniciando proceso de expiración automática de transacciones...")
        
        # Obtener transacciones pendientes
        transacciones_pendientes = TuModeloTransaccion.objects.filter(
            estado='PENDIENTE'
        )
        
        total_transacciones = transacciones_pendientes.count()
        expiradas_count = 0
        errores_count = 0
        
        logger.info(f"Procesando {total_transacciones} transacciones pendientes")
        
        for transaccion in transacciones_pendientes:
            try:
                # Llamar a tu función original del modelo
                if transaccion.expirar_automaticamente():
                    expiradas_count += 1
                    
            except Exception as e:
                errores_count += 1
                logger.error(f"Error al procesar transacción {transaccion.id}: {e}")
                continue
        
        logger.info(
            f"Proceso completado. "
            f"Transacciones expiradas: {expiradas_count}, "
            f"Errores: {errores_count}, "
            f"Total procesadas: {total_transacciones}"
        )
        
        return {
            'expiradas_count': expiradas_count,
            'errores_count': errores_count,
            'total_procesadas': total_transacciones,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error crítico en expirar_transacciones_pendientes: {e}")
        
        # Reintentar después de 60 segundos (max_retries=3)
        raise self.retry(countdown=60, exc=e)
5. Versión optimizada para muchos registros
Si tienes muchas transacciones, usa esta versión optimizada:

python
# tu_app/tasks.py (versión optimizada)
@shared_task(bind=True, max_retries=3)
def expirar_transacciones_pendientes_optimizada(self, batch_size=100):
    """
    Versión optimizada para muchos registros, procesa por lotes
    """
    try:
        from django.db import transaction
        from django.db.models import Q
        
        logger.info("Iniciando proceso de expiración optimizada...")
        
        total_expiradas = 0
        offset = 0
        
        while True:
            # Obtener IDs en lotes para evitar cargar muchos objetos en memoria
            transaccion_ids = TuModeloTransaccion.objects.filter(
                estado='PENDIENTE'
            ).values_list('id', flat=True)[offset:offset + batch_size]
            
            if not transaccion_ids:
                break
                
            batch_expiradas = 0
            for trans_id in transaccion_ids:
                try:
                    with transaction.atomic():
                        transaccion = TuModeloTransaccion.objects.select_for_update().get(
                            id=trans_id, 
                            estado='PENDIENTE'  # Doble verificación para evitar condiciones de carrera
                        )
                        if transaccion.expirar_automaticamente():
                            batch_expiradas += 1
                            
                except TuModeloTransaccion.DoesNotExist:
                    continue
                except Exception as e:
                    logger.warning(f"Error con transacción {trans_id}: {e}")
                    continue
            
            total_expiradas += batch_expiradas
            offset += batch_size
            
            logger.info(f"Procesado lote: {batch_expiradas} expiradas (total: {total_expiradas})")
        
        logger.info(f"Proceso optimizado completado. Total expiradas: {total_expiradas}")
        return {'expiradas_count': total_expiradas}
        
    except Exception as e:
        logger.error(f"Error en versión optimizada: {e}")
        raise self.retry(countdown=60, exc=e)
6. Iniciar los servicios
Terminal 1 - Redis (requiere Redis instalado)
bash
redis-server
Terminal 2 - Celery Worker
bash
celery -A tu_proyecto worker --loglevel=info -Q default,periodic_tasks
Terminal 3 - Celery Beat (el scheduler)
bash
celery -A tu_proyecto beat --loglevel=info
7. Comandos útiles para monitoreo
bash
# Ver estado de Celery
celery -A tu_proyecto status

# Monitorear tareas en tiempo real
celery -A tu_proyecto events

# Ver tareas programadas
celery -A tu_proyecto beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
8. Docker Compose (opcional)
Si usas Docker, crea un docker-compose.yml:

yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - redis
  
  celery_worker:
    build: .
    command: celery -A tu_proyecto worker --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - redis
  
  celery_beat:
    build: .
    command: celery -A tu_proyecto beat --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - redis
      - celery_worker
¿Necesitas ayuda con alguna parte específica de la implementación?

redis-server
274022:C 26 Sep 2025 02:50:00.602 # WARNING Memory overcommit must be enabled! Without it, a background save or replication may fail under low memory condition. Being disabled, it can also cause failures without low memory condition, see https://github.com/jemalloc/jemalloc/issues/1328. To fix this issue add 'vm.overcommit_memory = 1' to /etc/sysctl.conf and then reboot or run the command 'sysctl vm.overcommit_memory=1' for this to take effect.
274022:C 26 Sep 2025 02:50:00.602 * oO0OoO0OoO0Oo Valkey is starting oO0OoO0OoO0Oo
274022:C 26 Sep 2025 02:50:00.602 * Valkey version=8.0.4, bits=64, commit=00000000, modified=0, pid=274022, just started
274022:C 26 Sep 2025 02:50:00.602 # Warning: no config file specified, using the default config. In order to specify a config file use redis-server /path/to/valkey.conf
274022:M 26 Sep 2025 02:50:00.602 * monotonic clock: POSIX clock_gettime
                .+^+.                                                
            .+#########+.                                            
        .+########+########+.           Valkey 8.0.4 (00000000/0) 64 bit
    .+########+'     '+########+.                                    
 .########+'     .+.     '+########.    Running in standalone mode
 |####+'     .+#######+.     '+####|    Port: 6379
 |###|   .+###############+.   |###|    PID: 274022                     
 |###|   |#####*'' ''*#####|   |###|                                 
 |###|   |####'  .-.  '####|   |###|                                 
 |###|   |###(  (@@@)  )###|   |###|          https://valkey.io      
 |###|   |####.  '-'  .####|   |###|                                 
 |###|   |#####*.   .*#####|   |###|                                 
 |###|   '+#####|   |#####+'   |###|                                 
 |####+.     +##|   |#+'     .+####|                                 
 '#######+   |##|        .+########'                                 
    '+###|   |##|    .+########+'                                    
        '|   |####+########+'                                        
             +#########+'                                            
                '+v+'                                                

274022:M 26 Sep 2025 02:50:00.603 * Server initialized
274022:M 26 Sep 2025 02:50:00.603 * Loading RDB produced by Valkey version 8.0.4
274022:M 26 Sep 2025 02:50:00.603 * RDB age 79 seconds
274022:M 26 Sep 2025 02:50:00.603 * RDB memory usage when created 0.87 Mb
274022:M 26 Sep 2025 02:50:00.603 * Done loading RDB, keys loaded: 0, keys expired: 0.
274022:M 26 Sep 2025 02:50:00.603 * DB loaded from disk: 0.000 seconds
274022:M 26 Sep 2025 02:50:00.603 * Ready to accept connections tcp

ya tengo corriendo redis-server
¡Perfecto! Ya tienes Redis corriendo. Ahora vamos a iniciar Celery. Necesitas abrir dos terminales adicionales:

Terminal 2 - Celery Worker
bash
# En una nueva terminal, desde la raíz de tu proyecto Django
celery -A tu_proyecto worker --loglevel=info
Terminal 3 - Celery Beat (el scheduler)
bash
# En otra terminal, desde la raíz de tu proyecto Django
celery -A tu_proyecto beat --loglevel=info
Si encuentras algún error, aquí están las soluciones comunes:
Error 1: No encuentra el módulo
bash
# Si tu proyecto se llama diferente, ajusta el nombre:
celery -A mi_proyecto worker --loglevel=info
Error 2: Problemas con la configuración
Si hay errores de importación, verifica que tu estructura de archivos sea correcta:

text
tu_proyecto/
├── __init__.py
├── celery.py          # El archivo que creamos
├── settings.py
├── urls.py
└── wsgi.py
Error 3: Permisos o dependencias
Asegúrate de tener Celery instalado correctamente:

bash
pip list | grep celery
Para verificar que todo funciona:
1. Prueba el worker ejecutando una tarea manualmente
Abre un shell de Django:

bash
python manage.py shell
Y ejecuta:

python
from tu_app.tasks import expirar_transacciones_pendientes

# Probar la tarea manualmente
result = expirar_transacciones_pendientes.delay()
print(result.id)  # Deberías ver un ID de tarea
2. Verifica que Beat esté programando las tareas
En los logs de Celery Beat deberías ver algo como:

text
DatabaseScheduler: Schedule changed.
3. Monitorea los logs del worker
Deberías ver las tareas ejecutándose cada minuto:

text
[2025-09-26 02:51:00,123: INFO/MainProcess] Task tu_app.tasks.expirar_transacciones_pendientes[12345] received
[2025-09-26 02:51:00,456: INFO/ForkPoolWorker-1] Iniciando proceso de expiración automática de transacciones...
Comando alternativo para desarrollo (todo en uno)
Si prefieres probar todo en una sola terminal:

bash
celery -A tu_proyecto worker --beat --loglevel=info
Si usas Windows
Para Windows necesitas instalar un paquete adicional:

bash
pip install eventlet
Y ejecutar con:

bash
celery -A tu_proyecto worker --loglevel=info -P eventlet
Verificación final
Cuando todo esté funcionando, deberías ver en tus logs algo como esto cada minuto:

text
[2025-09-26 02:52:00,123: INFO/ForkPoolWorker-1] Proceso completado. Transacciones expiradas: 2, Errores: 0, Total procesadas: 15
¿Qué ves en tus terminales cuando ejecutas los comandos? ¿Hay algún error específico que necesites ayuda para resolver?

Usage: celery [OPTIONS] COMMAND [ARGS]...
Try 'celery --help' for help.

Error: 
Unable to load celery application.
Module 'global_exchange' has no attribute 'celery'
El error indica que Celery no puede encontrar la aplicación. Esto suele pasar porque la configuración no está correctamente enlazada. Vamos a solucionarlo:

1. Verifica la estructura de archivos
Asegúrate de que tienes esta estructura:

text
global_exchange/          # Tu carpeta del proyecto
├── __init__.py
├── celery.py            # El archivo que creamos
├── settings.py
├── urls.py
└── wsgi.py
2. Corrige el __init__.py
Asegúrate de que global_exchange/__init__.py tenga exactamente esto:

python
# global_exchange/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)
3. Verifica el contenido de celery.py
python
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
        'task': 'tu_app.tasks.expirar_transacciones_pendientes',  # Cambia 'tu_app' por el nombre real de tu app
        'schedule': crontab(minute='*/1'),
    },
}

app.conf.timezone = 'America/Mexico_City'  # Ajusta tu zona horaria
4. Solución alternativa inmediata
Si sigue sin funcionar, prueba crear un archivo celery_app.py en lugar de celery.py:

python
# global_exchange/celery_app.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_exchange.settings')

celery_app = Celery('global_exchange')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()

celery_app.conf.beat_schedule = {
    'expirar-transacciones-cada-minuto': {
        'task': 'tu_app.tasks.expirar_transacciones_pendientes',
        'schedule': crontab(minute='*/1'),
    },
}
celery_app.conf.timezone = 'America/Mexico_City'
Y en __init__.py:

python
# global_exchange/__init__.py
from .celery_app import celery_app

__all__ = ('celery_app',)
5. Comando corregido
Ejecuta los comandos desde la raíz de tu proyecto (donde está manage.py), no desde la carpeta global_exchange:

bash
# Asegúrate de estar en la carpeta correcta
pwd  # Debería mostrar la carpeta que contiene manage.py

# Luego ejecuta:
celery -A global_exchange worker --loglevel=info
6. Si aún hay problemas, prueba esto:
Crea un archivo celery_config.py en la raíz de tu proyecto:

python
# celery_config.py (junto a manage.py)
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_exchange.settings')

app = Celery('global_exchange')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
Y ejecuta:

bash
celery -A celery_config worker --loglevel=info
7. Verificación de la configuración
Para diagnosticar el problema, ejecuta:

bash
python manage.py shell
Y en el shell:

python
# Verifica que Django pueda importar la configuración
from global_exchange import celery
print(celery.app)

# O prueba esto:
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_exchange.settings')
import django
django.setup()

from celery import current_app
print(current_app)
¿Cuál es el nombre exacto de tu aplicación Django donde están los modelos? (para ajustar el nombre en la tarea: 'tu_app.tasks.expirar_transacciones_pendientes')

¿Podrías mostrarme el contenido de tu archivo celery.py y la estructura de carpetas?

File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/home/user/Downloads/global-exchange/global_exchange/__init__.py", line 2, in <module>
    from .celery import app as celery_app
  File "/home/user/Downloads/global-exchange/global_exchange/celery.py", line 3, in <module>
    from celery import Celery
ModuleNotFoundError: No module named 'celery'
El error indica que Celery no está instalado en tu entorno virtual. Vamos a solucionarlo:

1. Instalar Celery y Redis
bash
# Asegúrate de estar en tu entorno virtual
pip install celery redis

# Verifica la instalación
pip list | grep -E "(celery|redis)"
2. Si usas un entorno virtual, actívalo:
bash
# Si usas venv
source venv/bin/activate

# Si usas conda
conda activate tu_entorno

# Si usas pipenv
pipenv shell
3. Verifica la instalación:
bash
python -c "import celery; print('Celery instalado correctamente')"
python -c "import redis; print('Redis instalado correctamente')"
4. Si estás usando requirements.txt, asegúrate de tener:
txt
# requirements.txt
Django>=4.0,<5.0
celery>=5.3
redis>=4.5
Y luego:

bash
pip install -r requirements.txt
5. Solución rápida - reinstalar:
bash
# Desinstalar y reinstalar
pip uninstall celery redis -y
pip install celery redis
6. Si el problema persiste, verifica tu Python path:
bash
# Verifica qué Python estás usando
which python
which pip

# Verifica las rutas de Python
python -c "import sys; print('\n'.join(sys.path))"
7. Para desarrollo, también puedes instalar:
bash
pip install celery[redis]  # Incluye dependencias para Redis
8. Verificación completa:
Después de instalar, prueba esto:

bash
# En una terminal
python manage.py shell
python
# En el shell de Django
try:
    from celery import Celery
    print("✅ Celery importa correctamente")
    
    import redis
    print("✅ Redis importa correctamente")
    
    # Prueba la configuración de Celery
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_exchange.settings')
    from global_exchange.celery import app
    print("✅ Configuración de Celery carga correctamente")
    
except Exception as e:
    print(f"❌ Error: {e}")
9. Si usas Windows, necesitas:
bash
pip install celery[redis] eventlet
10. Comandos para probar después de la instalación:
bash
# Terminal 1 - Redis (debería estar corriendo)
redis-server

# Terminal 2 - Celery Worker
celery -A global_exchange worker --loglevel=info

# Terminal 3 - Celery Beat
celery -A global_exchange beat --loglevel=info
¿Qué muestra cuando ejecutas pip list | grep celery?

Si después de instalar sigue sin funcionar, podríamos tener un problema de entorno virtual o de paths. ¿Podrías confirmarme:

¿Estás usando un entorno virtual?

¿Qué muestra which python y which pip?

¿El comando python -c "import celery" funciona sin errores?

[2025-09-26 04:36:11,827: WARNING/ForkPoolWorker-3] HOLA
[2025-09-26 04:36:11,827: WARNING/ForkPoolWorker-3] Error con transacción 12: 'expirar_transacciones_pendientes_optimizada' object has no attribute 'estado'
[2025-09-26 04:36:11,829: WARNING/ForkPoolWorker-3] HOLA
[2025-09-26 04:36:11,829: WARNING/ForkPoolWorker-3] Error con transacción 10: 'expirar_transacciones_pendientes_optimizada' object has no attribute 'estado'
[2025-09-26 04:36:11,830: WARNING/ForkPoolWorker-3] HOLA
[2025-09-26 04:36:11,831: WARNING/ForkPoolWorker-3] Error con transacción 9: 'expirar_transacciones_pendientes_optimizada' object has no attribute 'estado'
[2025-09-26 04:36:11,832: WARNING/ForkPoolWorker-3] HOLA
[2025-09-26 04:36:11,832: WARNING/ForkPoolWorker-3] Error con transacción 8: 'expirar_transacciones_pendientes_optimizada' object has no attribute 'estado'
[2025-09-26 04:36:11,833: WARNING/ForkPoolWorker-3] HOLA
[2025-09-26 04:36:11,834: WARNING/ForkPoolWorker-3] Error con transacción 7: 'expirar_transacciones_pendientes_optimizada' object has no attribute 'estado'
[2025-09-26 04:36:11,835: WARNING/ForkPoolWorker-3] HOLA
[2025-09-26 04:36:11,835: WARNING/ForkPoolWorker-3] Error con transacción 6: 'expirar_transacciones_pendientes_optimizada' object has no attribute 'estado'
[2025-09-26 04:36:11,836: WARNING/ForkPoolWorker-3] HOLA
[2025-09-26 04:36:11,837: WARNING/ForkPoolWorker-3] Error con transacción 1: 'expirar_transacciones_pendientes_optimizada' object has no attribute 'estado'

mira esto
El error indica que hay una confusión en el código. Parece que estás llamando a la función de tarea como si fuera un modelo. Vamos a corregir la tarea:

Problema
La tarea expirar_transacciones_pendientes_optimizada es una función de Celery, pero el código está tratando de acceder a .estado como si fuera un objeto del modelo.

Solución - Corrige la tarea:
python
# tu_app/tasks.py
from celery import shared_task
from django.utils import timezone
import logging
from .models import TuModeloTransaccion  # Ajusta al nombre real de tu modelo

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def expirar_transacciones_pendientes(self):
    """
    Tarea CORREGIDA que ejecuta expirar_automaticamente() en transacciones pendientes
    """
    try:
        logger.info("Iniciando proceso de expiración automática de transacciones...")
        
        # Obtener transacciones pendientes - ESTO ES CORRECTO
        transacciones_pendientes = TuModeloTransaccion.objects.filter(
            estado='PENDIENTE'
        )
        
        total_transacciones = transacciones_pendientes.count()
        expiradas_count = 0
        
        logger.info(f"Procesando {total_transacciones} transacciones pendientes")
        
        for transaccion in transacciones_pendientes:
            try:
                # CORRECTO: transaccion es un objeto del modelo, tiene .estado y .expirar_automaticamente()
                if transaccion.expirar_automaticamente():
                    expiradas_count += 1
                    logger.info(f"Transacción {transaccion.id} expirada correctamente")
                    
            except Exception as e:
                logger.error(f"Error al procesar transacción {transaccion.id}: {e}")
                continue
        
        logger.info(f"Proceso completado. Transacciones expiradas: {expiradas_count}")
        
        return {
            'expiradas_count': expiradas_count,
            'total_procesadas': total_transacciones,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error crítico en expirar_transacciones_pendientes: {e}")
        raise self.retry(countdown=60, exc=e)

# ELIMINA la función con error o corrígela así:
@shared_task(bind=True, max_retries=3)
def expirar_transacciones_pendientes_optimizada(self, batch_size=100):
    """
    Versión CORREGIDA y optimizada
    """
    try:
        from django.db import transaction
        
        logger.info("Iniciando proceso de expiración optimizada...")
        
        total_expiradas = 0
        offset = 0
        
        while True:
            # Obtener IDs en lotes
            transaccion_ids = TuModeloTransaccion.objects.filter(
                estado='PENDIENTE'
            ).values_list('id', flat=True)[offset:offset + batch_size]
            
            if not transaccion_ids:
                break
                
            batch_expiradas = 0
            for trans_id in transaccion_ids:
                try:
                    # CORRECTO: Obtener el objeto del modelo
                    transaccion = TuModeloTransaccion.objects.get(id=trans_id)
                    
                    # CORRECTO: Llamar al método del modelo
                    if transaccion.expirar_automaticamente():
                        batch_expiradas += 1
                        
                except TuModeloTransaccion.DoesNotExist:
                    continue
                except Exception as e:
                    logger.error(f"Error con transacción {trans_id}: {e}")  # QUITA el 'HOLA'
                    continue
            
            total_expiradas += batch_expiradas
            offset += batch_size
            
            logger.info(f"Procesado lote: {batch_expiradas} expiradas")
        
        logger.info(f"Proceso optimizado completado. Total expiradas: {total_expiradas}")
        return {'expiradas_count': total_expiradas}
        
    except Exception as e:
        logger.error(f"Error en versión optimizada: {e}")
        raise self.retry(countdown=60, exc=e)
2. Actualiza la configuración de Celery Beat
En global_exchange/celery.py, asegúrate de que apunte a la tarea correcta:

python
app.conf.beat_schedule = {
    'expirar-transacciones-cada-minuto': {
        'task': 'tu_app.tasks.expirar_transacciones_pendientes',  # Usa la función simple
        'schedule': crontab(minute='*/1'),
    },
}
3. Verifica tu modelo
Asegúrate de que tu modelo tenga los campos y métodos correctos:

python
# tu_app/models.py
from django.db import models
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class TuModeloTransaccion(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    tiempo_expiracion_minutos = models.IntegerField(default=30)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.TextField(blank=True)
    
    @property
    def ha_expirado(self):
        """Verifica si la transacción ha expirado"""
        if self.estado != 'PENDIENTE':
            return False
        tiempo_transcurrido = timezone.now() - self.fecha_creacion
        return tiempo_transcurrido.total_seconds() > (self.tiempo_expiracion_minutos * 60)
    
    def expirar_automaticamente(self):
        """TU FUNCIÓN ORIGINAL - debe estar en el modelo"""
        if self.ha_expirado and self.estado == 'PENDIENTE':
            self.estado = 'CANCELADA'
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = f"Expirada automáticamente después de {self.tiempo_expiracion_minutos} minutos"
            self.save()
            
            # Enviar notificación de expiración
            try:
                from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
                llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_EXPIRADA')
            except Exception as e:
                logger.error(f"Error al enviar notificación de expiración: {e}")
            
            return True
        return False
    
    def __str__(self):
        return f"Transacción {self.id} - {self.estado}"
4. Reinicia Celery
Después de hacer los cambios:

bash
# Detén Celery (Ctrl+C)
# Y reinicia:
celery -A global_exchange worker --loglevel=info
celery -A global_exchange beat --loglevel=info
¿Podrías mostrarme el código actual de tu archivo tasks.py? Así puedo ver exactamente dónde está el error y corregirlo específicamente.

[2025-09-26 04:51:00,097: ERROR/ForkPoolWorker-3] Error al procesar transacción 12: Transaccion.expirar_automaticamente() missing 1 required positional argument: 'self'
[2025-09-26 04:51:00,097: ERROR/ForkPoolWorker-3] Error al procesar transacción 10: Transaccion.expirar_automaticamente() missing 1 required positional argument: 'self'
[2025-09-26 04:51:00,097: ERROR/ForkPoolWorker-3] Error al procesar transacción 9: Transaccion.expirar_automaticamente() missing 1 required positional argument: 'self'
[2025-09-26 04:51:00,097: ERROR/ForkPoolWorker-3] Error al procesar transacción 8: Transaccion.expirar_automaticamente() missing 1 required positional argument: 'self'
[2025-09-26 04:51:00,097: ERROR/ForkPoolWorker-3] Error al procesar transacción 7: Transaccion.expirar_automaticamente() missing 1 required positional argument: 'self'
[2025-09-26 04:51:00,098: ERROR/ForkPoolWorker-3] Error al procesar transacción 6: Transaccion.expirar_automaticamente() missing 1 required positional argument: 'self'
[2025-09-26 04:51:00,098: ERROR/ForkPoolWorker-3] Error al procesar transacción 1: Transaccion.expirar_automaticamente() missing 1 required positional argument: 'self'
El error indica que estás llamando al método expirar_automaticamente como si fuera una función de clase, no como un método de instancia. Esto pasa cuando usas Transaccion.expirar_automaticamente() en lugar de transaccion.expirar_automaticamente().

Corrección del código en tasks.py:
python
# tu_app/tasks.py
from celery import shared_task
from django.utils import timezone
import logging
from .models import Transaccion  # Ajusta al nombre real de tu modelo

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def expirar_transacciones_pendientes(self):
    """
    Tarea CORREGIDA - llama correctamente al método de instancia
    """
    try:
        logger.info("Iniciando proceso de expiración automática de transacciones...")
        
        # Obtener transacciones pendientes
        transacciones_pendientes = Transaccion.objects.filter(
            estado='PENDIENTE'
        )
        
        total_transacciones = transacciones_pendientes.count()
        expiradas_count = 0
        
        logger.info(f"Procesando {total_transacciones} transacciones pendientes")
        
        for transaccion in transacciones_pendientes:
            try:
                # CORRECTO: transaccion es una instancia, llama al método sin argumentos
                if transaccion.expirar_automaticamente():  # ← SIN paréntesis después del nombre del método
                    expiradas_count += 1
                    logger.info(f"Transacción {transaccion.id} expirada correctamente")
                    
            except Exception as e:
                logger.error(f"Error al procesar transacción {transaccion.id}: {e}")
                continue
        
        logger.info(f"Proceso completado. Transacciones expiradas: {expiradas_count}")
        
        return {
            'expiradas_count': expiradas_count,
            'total_procesadas': total_transacciones,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error crítico en expirar_transacciones_pendientes: {e}")
        raise self.retry(countdown=60, exc=e)
El error común es hacer esto:
❌ INCORRECTO - llamar al método de clase sin instancia:

python
# Esto está MAL
if Transaccion.expirar_automaticamente():  # Faltaría el 'self'
✅ CORRECTO - llamar al método de instancia:

python
# Esto está BIEN
if transaccion.expirar_automaticamente():  # 'transaccion' es la instancia
Si tu método actual está definido como método de clase:
Si por alguna razón expirar_automaticamente está definido como @classmethod, entonces deberías cambiar el modelo o la llamada:

Opción A: Cambiar la llamada (si es classmethod)
python
# tasks.py (si el método es classmethod)
for transaccion in transacciones_pendientes:
    if Transaccion.expirar_automaticamente(transaccion):  # Pasar la instancia
        expiradas_count += 1
Opción B: Mejor - cambiar el modelo para que sea método de instancia
python
# models.py - DEBE ser así
class Transaccion(models.Model):
    # ... campos ...
    
    def expirar_automaticamente(self):  # ← 'self' como primer parámetro
        """Método de instancia"""
        if self.ha_expirado and self.estado == 'PENDIENTE':
            self.estado = 'CANCELADA'
            # ... resto del código ...
            return True
        return False
Verifica tu modelo:
Asegúrate de que en models.py esté definido como método de instancia:

python
class Transaccion(models.Model):
    # ... tus campos ...
    
    def expirar_automaticamente(self):  # ← CON 'self'
        """Tu función original - debe tener 'self' como primer parámetro"""
        if self.ha_expirado and self.estado == 'PENDIENTE':
            self.estado = 'CANCELADA'
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = f"Expirada automáticamente después de {self.tiempo_expiracion_minutos} minutos"
            self.save()
            
            # Enviar notificación
            try:
                from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
                llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_EXPIRADA')
            except Exception as e:
                logger.error(f"Error al enviar notificación de expiración: {e}")
            
            return True
        return False
Reinicia Celery después de los cambios:
bash
# Detén y reinicia
celery -A global_exchange worker --loglevel=info
celery -A global_exchange beat --loglevel=info
¿Podrías mostrarme cómo tienes definido el método expirar_automaticamente en tu modelo Transaccion? Así puedo ver exactamente cuál es el problema.

# tu_app/tasks.py
from celery import shared_task
from django.utils import timezone
import logging
from .models import Transaccion  # Ajusta al nombre real de tu modelo

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def expirar_transacciones_pendientes(self):
    """
    Tarea que ejecuta expirar_automaticamente() en todas las transacciones pendientes
    Se ejecuta cada minuto via Celery Beat
    """
    try:
        logger.info("Iniciando proceso de expiración automática de transacciones...")
        
        # Obtener transacciones pendientes
        transacciones_pendientes = Transaccion.objects.filter(
            estado='PENDIENTE'
        )
        
        total_transacciones = transacciones_pendientes.count()
        expiradas_count = 0
        errores_count = 0
        
        logger.info(f"Procesando {total_transacciones} transacciones pendientes")
        
        for transaccion in transacciones_pendientes:
            try:
                # Llamar a tu función original del modelo
                if transaccion.expirar_automaticamente():
                    expiradas_count += 1
                    
            except Exception as e:
                errores_count += 1
                logger.error(f"Error al procesar transacción {transaccion.id}: {e}")
                continue
        
        logger.info(
            f"Proceso completado. "
            f"Transacciones expiradas: {expiradas_count}, "
            f"Errores: {errores_count}, "
            f"Total procesadas: {total_transacciones}"
        )
        
        return {
            'expiradas_count': expiradas_count,
            'errores_count': errores_count,
            'total_procesadas': total_transacciones,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error crítico en expirar_transacciones_pendientes: {e}")
        
        # Reintentar después de 60 segundos (max_retries=3)
        raise self.retry(countdown=60, exc=e)

Este es el codigo
El código de tu tasks.py está correcto. El problema debe estar en la definición del método expirar_automaticamente en tu modelo Transaccion.

Por favor muéstrame cómo tienes definido el método expirar_automaticamente en tu archivo models.py.

El error missing 1 required positional argument: 'self' indica que probablemente tienes uno de estos problemas:

Posibles problemas en models.py:
1. Falta el parámetro self:
python
# ❌ INCORRECTO - falta self
def expirar_automaticamente():
    # código...

# ✅ CORRECTO
def expirar_automaticamente(self):
    # código...
2. Está definido como @staticmethod sin self:
python
# ❌ INCORRECTO
@staticmethod
def expirar_automaticamente():
    # código...

# ✅ CORRECTO - quitar @staticmethod o agregar parámetro
def expirar_automaticamente(self):
    # código...
3. Está definido como @classmethod pero se usa mal:
python
# ❌ Si es classmethod pero se usa como instancia
@classmethod
def expirar_automaticamente(cls):
    # código...
Mientras tanto, aquí está la versión CORRECTA que debería tener tu modelo:
python
# models.py - VERSIÓN CORRECTA
from django.db import models
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Transaccion(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('COMPLETADA', 'Completada'), 
        ('CANCELADA', 'Cancelada'),
    ]
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    tiempo_expiracion_minutos = models.IntegerField(default=30)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.TextField(blank=True)
    
    @property
    def ha_expirado(self):
        """Verifica si la transacción ha expirado"""
        if self.estado != 'PENDIENTE':
            return False
        tiempo_transcurrido = timezone.now() - self.fecha_creacion
        return tiempo_transcurrido.total_seconds() > (self.tiempo_expiracion_minutos * 60)
    
    def expirar_automaticamente(self):  # ← ¡DEBE tener self!
        """Marca la transacción como expirada automáticamente"""
        if self.ha_expirado and self.estado == 'PENDIENTE':
            self.estado = 'CANCELADA'
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = f"Expirada automáticamente después de {self.tiempo_expiracion_minutos} minutos"
            self.save()
            
            # Enviar notificación de expiración
            try:
                from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
                llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_EXPIRADA')
            except Exception as e:
                logger.error(f"Error al enviar notificación de expiración: {e}")
            
            return True
        return False
Solución temporal - Versión alternativa en tasks.py:
Si no puedes modificar el modelo inmediatamente, usa esta versión temporal:

python
# tasks.py - SOLUCIÓN TEMPORAL
@shared_task(bind=True, max_retries=3)
def expirar_transacciones_pendientes(self):
    try:
        logger.info("Iniciando proceso de expiración automática de transacciones...")
        
        transacciones_pendientes = Transaccion.objects.filter(estado='PENDIENTE')
        expiradas_count = 0
        
        for transaccion in transacciones_pendientes:
            try:
                # SOLUCIÓN TEMPORAL: Replicar la lógica aquí si el método del modelo tiene problemas
                if transaccion.ha_expirado and transaccion.estado == 'PENDIENTE':
                    transaccion.estado = 'CANCELADA'
                    transaccion.fecha_cancelacion = timezone.now()
                    transaccion.motivo_cancelacion = f"Expirada automáticamente después de {transaccion.tiempo_expiracion_minutos} minutos"
                    transaccion.save()
                    
                    # Enviar notificación
                    try:
                        from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
                        llamar_tarea_con_fallback(enviar_notificacion_transaccion, transaccion.id, 'TRANSACCION_EXPIRADA')
                    except Exception as e:
                        logger.error(f"Error al enviar notificación: {e}")
                    
                    expiradas_count += 1
                    
            except Exception as e:
                logger.error(f"Error al procesar transacción {transaccion.id}: {e}")
                continue
        
        logger.info(f"Proceso completado. Transacciones expiradas: {expiradas_count}")
        return {'expiradas_count': expiradas_count}
        
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        raise self.retry(countdown=60, exc=e)
Por favor, comparte el código de tu método expirar_automaticamente en models.py para poder darte la solución exacta.

@shared_task
    def expirar_automaticamente(self):
        """Marca la transacción como expirada automáticamente"""
        print("HOLA")
        print(self.estado)
        if self.ha_expirado and self.estado == 'PENDIENTE':
            self.estado = 'CANCELADA'
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = f"Expirada automáticamente después de {self.tiempo_expiracion_minutos} minutos"
            self.save()
            
            # Enviar notificación de expiración
            try:
                from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
                llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_EXPIRADA')
            except Exception as e:
                logger.error(f"Error al enviar notificación de expiración: {e}")
            
            return True
        return False
¡Ahí está el problema! Tienes el decorador @shared_task en el método del modelo. @shared_task es solo para funciones de Celery, no para métodos de modelos Django.

Problema:
El decorador @shared_task está convirtiendo tu método de modelo en una tarea de Celery, lo que cambia su comportamiento y causa el error.

Solución:
Elimina @shared_task del método en tu modelo:

python
# models.py - CORREGIDO
class Transaccion(models.Model):
    # ... tus campos ...
    
    def expirar_automaticamente(self):  # ← QUITA @shared_task
        """Marca la transacción como expirada automáticamente"""
        print("HOLA")
        print(self.estado)
        if self.ha_expirado and self.estado == 'PENDIENTE':
            self.estado = 'CANCELADA'
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = f"Expirada automáticamente después de {self.tiempo_expiracion_minutos} minutos"
            self.save()
            
            # Enviar notificación de expiración
            try:
                from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
                llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_EXPIRADA')
            except Exception as e:
                logger.error(f"Error al enviar notificación de expiración: {e}")
            
            return True
        return False
Estructura correcta:
✅ En models.py - Métodos de modelo SIN decoradores de Celery:
python
class Transaccion(models.Model):
    def expirar_automaticamente(self):  # Sin @shared_task
        # Lógica del modelo
        pass
✅ En tasks.py - Tareas de Celery CON @shared_task:
python
@shared_task
def expirar_transacciones_pendientes():
    # Lógica que llama a los métodos del modelo
    transacciones = Transaccion.objects.filter(estado='PENDIENTE')
    for transaccion in transacciones:
        transaccion.expirar_automaticamente()  # Llama al método normal del modelo
Después de corregir:
Elimina @shared_task de tu método expirar_automaticamente en models.py

Reinicia Celery:

bash
# Detén Celery (Ctrl+C) y reinicia:
celery -A global_exchange worker --loglevel=info
celery -A global_exchange beat --loglevel=info
Tu código final debería verse así:
models.py
python
class Transaccion(models.Model):
    # ... campos del modelo ...
    
    def expirar_automaticamente(self):  # ← SIN @shared_task
        """Método normal del modelo"""
        if self.ha_expirado and self.estado == 'PENDIENTE':
            # ... tu lógica ...
            return True
        return False
tasks.py (ya está correcto)
python
@shared_task  # ← Este SÍ debe tener @shared_task
def expirar_transacciones_pendientes():
    transacciones = Transaccion.objects.filter(estado='PENDIENTE')
    for transaccion in transacciones:
        transaccion.expirar_automaticamente()  # ← Llama al método normal
¿Puedes eliminar el @shared_task de tu método expirar_automaticamente en el modelo y probar de nuevo?

File "/usr/lib64/python3.13/threading.py", line 1043, in _bootstrap_inner
    self.run()
    ~~~~~~~~^^
  File "/usr/lib64/python3.13/threading.py", line 994, in run
    self._target(*self._args, **self._kwargs)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/utils/autoreload.py", line 64, in wrapper
    fn(*args, **kwargs)
    ~~^^^^^^^^^^^^^^^^^
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/core/management/commands/runserver.py", line 124, in inner_run
    autoreload.raise_last_exception()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/utils/autoreload.py", line 86, in raise_last_exception
    raise _exception[1]
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/core/management/__init__.py", line 394, in execute
    autoreload.check_errors(django.setup)()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/utils/autoreload.py", line 64, in wrapper
    fn(*args, **kwargs)
    ~~^^^^^^^^^^^^^^^^^
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/__init__.py", line 24, in setup
    apps.populate(settings.INSTALLED_APPS)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/apps/registry.py", line 91, in populate
    app_config = AppConfig.create(entry)
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/apps/config.py", line 123, in create
    mod = import_module(mod_path)
  File "/usr/lib64/python3.13/importlib/__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 1026, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/contrib/auth/apps.py", line 8, in <module>
    from .checks import check_middleware, check_models_permissions, check_user_model
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/contrib/auth/checks.py", line 9, in <module>
    from .management import _get_builtin_permissions
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/contrib/auth/management/__init__.py", line 10, in <module>
    from django.contrib.contenttypes.management import create_contenttypes
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/contrib/contenttypes/management/__init__.py", line 2, in <module>
    from django.db import DEFAULT_DB_ALIAS, IntegrityError, migrations, router, transaction
  File "/home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/db/migrations/__init__.py", line 1, in <module>
    from .migration import Migration, swappable_dependency  # NOQA
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'django.db.migrations.migration'

que opinas de este error, falta algo en installed_apps?
Este error no está relacionado con APScheduler ni con tu código. Es un problema más grave de instalación de Django o compatibilidad de versiones.

Análisis del Error:
El error ModuleNotFoundError: No module named 'django.db.migrations.migration' indica que:

Django está corrupto o incompleto

Hay conflicto de versiones

El entorno virtual está dañado

Posibles Causas:
1. Django instalado incorrectamente:
bash
# Verificar la instalación actual
pip show django

# Verificar archivos de migrations
ls /home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/db/migrations/
2. Conflicto con Python 3.13:
Python 3.13 es muy nuevo y puede tener incompatibilidades con algunas versiones de Django.

Soluciones:
Solución 1: Reinstalar Django completamente
bash
# Eliminar Django actual
pip uninstall django -y

# Instalar versión compatible con Python 3.13
pip install "Django>=4.2,<5.0"

# O instalar la última versión estable
pip install Django==5.0.2
Solución 2: Verificar compatibilidad de versiones
bash
# Crear requirements.txt con versiones compatibles
cat > requirements.txt << EOF
Django==5.0.2
apscheduler==3.10.0
django-apscheduler==0.6.2
psycopg2-binary==2.9.6
EOF

# Reinstalar todo
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
Solución 3: Usar Python 3.11 o 3.12 (recomendado)
Python 3.13 es muy nuevo. Te recomiendo usar:

bash
# Instalar Python 3.11 o 3.12
sudo dnf install python3.11 python3.11-venv

# Crear nuevo entorno virtual
python3.11 -m venv venv
source venv/bin/activate
pip install django apscheduler django-apscheduler
Solución 4: Verificar instalación manualmente
bash
# Verificar que los archivos de migrations existen
python -c "
import django
print('Django version:', django.__version__)
from django.db.migrations import migration
print('Migrations module loaded successfully')
"
INSTALLED_APPS correcto (una vez solucionado Django):
python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Tus apps
    'cuentas',
    'transacciones',
    
    # APScheduler (DEBE ir después de tus apps)
    'django_apscheduler',
]
Para probar si Django funciona:
bash
# Verificar instalación básica
python manage.py check

# Si funciona, probar migraciones
python manage.py makemigrations
python manage.py migrate
Recomendación inmediata:
Ejecuta esto primero:

bash
pip install --upgrade Django==5.0.2
Si sigue fallando, usa Python 3.11/3.12

Solo después de que Django funcione, agrega APScheduler a INSTALLED_APPS

¿Qué versión de Django tienes actualmente? (pip show django)

Name: Django
Version: 5.2.4
Summary: A high-level Python web framework that encourages rapid development and clean, pragmatic design.
Home-page: https://www.djangoproject.com/
Author: 
Author-email: Django Software Foundation <foundation@djangoproject.com>
License: BSD-3-Clause
Location: /home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages
Requires: asgiref, sqlparse
Required-by: crispy-bootstrap4, django-apscheduler, django-crispy-forms, django-extensions, django-filter, django-otp
El problema es que Django 5.2.4 es incompatible con Python 3.13. Django 5.2.x no soporta oficialmente Python 3.13 todavía.

Soluciones inmediatas:
Opción 1: Downgrade a Django 5.1.x (Recomendado)
bash
pip install "Django<5.2" --upgrade
# Esto instalará Django 5.1.6 (compatible con Python 3.13)
Opción 2: Usar Django 5.0.x
bash
pip install "Django==5.0.6" --upgrade
Opción 3: Instalar versión de desarrollo de Django (si necesitas 5.2)
bash
pip install --pre Django
Verificar compatibilidad:
bash
# Después del downgrade
python -c "import django; print(f'Django {django.__version__}')"
python manage.py check
Estado de compatibilidad Django + Python 3.13:
Django 5.0.x: ✅ Compatible

Django 5.1.x: ✅ Compatible

Django 5.2.x: ❌ No compatible todavía

Si el downgrade no funciona, prueba esto:
1. Limpiar instalación completamente:
bash
pip uninstall django -y
pip install "Django==5.1.6"
2. Verificar estructura de archivos:
bash
# Verificar que existe el módulo migration
ls /home/user/Downloads/global-exchange/venv/lib64/python3.13/site-packages/django/db/migrations/

# Deberías ver: migration.py, operations, etc.
3. Si sigue fallando, reinstalar todo:
bash
# Recrear entorno virtual (opción nuclear)
cd /home/user/Downloads/global-exchange/
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install "Django==5.1.6" django-apscheduler apscheduler
INSTALLED_APPS después del fix:
python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth', 
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Tus apps
    'cuentas',
    'transacciones',
    
    # APScheduler (AL FINAL)
    'django_apscheduler',
]
¿Qué resultado obtienes con el downgrade a Django 5.1.6?

Me aparecio ese error al instalar APScheduler
El error no es de APScheduler, sino que se activó cuando APScheduler intentó cargarse en las INSTALLED_APPS. El problema real es la incompatibilidad Django 5.2.4 + Python 3.13.

Solución paso a paso:
1. Primero arreglar Django (SIN APScheduler en INSTALLED_APPS)
python
# settings.py - REMOVER django_apscheduler temporalmente
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes', 
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Tus apps
    'cuentas',
    'transacciones',
    
    # NO agregar django_apscheduler todavía
    # 'django_apscheduler',
]
2. Downgrade Django a versión compatible
bash
pip install "Django==5.1.6" --upgrade
3. Verificar que Django funciona
bash
python manage.py check
python manage.py migrate
4. Solo si Django funciona, instalar APScheduler manualmente
bash
# Instalar solo el paquete base (sin django-apscheduler)
pip install apscheduler==3.10.0
5. Implementación SIN django-apscheduler (más simple)
Crea transacciones/scheduler.py:

python
import threading
import time
import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)

class SchedulerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = False
        
    def run(self):
        self.running = True
        logger.info("Scheduler de transacciones iniciado")
        
        while self.running:
            try:
                self.expirar_transacciones()
            except Exception as e:
                logger.error(f"Error en scheduler: {e}")
            
            # Esperar 5 minutos entre ejecuciones
            time.sleep(300)
    
    def expirar_transacciones(self):
        """Expira transacciones pendientes"""
        try:
            from django.utils import timezone
            from datetime import timedelta
            from transacciones.models import Transaccion
            
            limite_tiempo = timezone.now() - timedelta(minutes=30)
            transacciones_expiradas = Transaccion.objects.filter(
                estado='PENDIENTE',
                fecha_creacion__lt=limite_tiempo
            )
            
            for transaccion in transacciones_expiradas:
                if transaccion.expirar_automaticamente():
                    logger.info(f"Transacción {transaccion.id} expirada")
                    
        except Exception as e:
            logger.error(f"Error expirando transacciones: {e}")
    
    def stop(self):
        self.running = False

# Instancia global
scheduler_thread = None

def start_scheduler():
    """Inicia el scheduler en un hilo separado"""
    global scheduler_thread
    if scheduler_thread and scheduler_thread.running:
        return
    
    scheduler_thread = SchedulerThread()
    scheduler_thread.start()

def stop_scheduler():
    """Detiene el scheduler"""
    global scheduler_thread
    if scheduler_thread:
        scheduler_thread.stop()
6. Modificar transacciones/apps.py
python
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class TransaccionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transacciones'
    
    def ready(self):
        """Inicia el scheduler cuando Django esté listo"""
        if settings.DEBUG:
            logger.info("Iniciando scheduler de transacciones...")
        
        # Solo iniciar en producción o cuando no esté en testing
        if not getattr(settings, 'TESTING', False):
            from .scheduler import start_scheduler
            start_scheduler()
7. NO agregar django-apscheduler a INSTALLED_APPS
Esta solución es mejor porque:

✅ No depende de django-apscheduler

✅ Más simple y confiable

✅ No requiere migraciones adicionales

✅ Funciona con Django 5.1.6 + Python 3.13

Resumen de comandos:
bash
# 1. Remover django-apscheduler de INSTALLED_APPS
# 2. Downgrade Django
pip install "Django==5.1.6" --upgrade

# 3. Instalar solo APScheduler base
pip install apscheduler==3.10.0

# 4. Probar
python manage.py check
python manage.py runserver
¿Prefieres esta solución más simple o quieres intentar hacer funcionar django-apscheduler?

"""Utilidades para límites de transacción de clientes.

Se exponen dos funciones independientes para obtener cada límite por separado:

	obtener_limite_diario(cliente)  -> Decimal
	obtener_limite_mensual(cliente) -> Decimal

Reglas:
	- Si `cliente.usa_limites_default` es True se usan los valores de su categoría.
	- Si es False se intenta usar el registro OneToOne `cliente.limites`.
	- Si no existe el registro personalizado (caso anómalo) se hace fallback
	  a la categoría.

Estas funciones NO realizan consultas agregadas de transacciones; solo devuelven
el número máximo configurado.
"""

from decimal import Decimal
from django.db.models import Sum
from cuentas.models import Configuracion
from transacciones.models import Transaccion
from django.utils import timezone
from django.db.models import Case, When, DecimalField, Value, Q




def _config_decimal(clave: str, fallback: any) -> Decimal:
	"""Obtiene un valor desde Configuracion y lo convierte a Decimal.

	NOTA: El tipo 'MONTO' actualmente no se convierte en el modelo Configuracion,
	por lo que aquí forzamos la conversión segura. Si la clave no existe o
	el valor no es convertible, se devuelve el fallback.
	"""
	valor = Configuracion.obtener_valor(clave, valor_por_defecto=None)
	if valor is None:
		return fallback
	try:
		return Decimal(str(valor))
	except Exception:
		return fallback


def obtener_limite_diario(cliente) -> Decimal:
	"""Devuelve el límite diario efectivo para el cliente.

	Parámetros
	----------
	cliente : Cliente
		Instancia del modelo Cliente.

	Returns
	-------
	Decimal
		Valor del límite diario.
	"""
	if getattr(cliente, "usa_limites_default", True):
		return _config_decimal('LIMITE_TRANSACCION_DIARIO_DEFAULT', None)
	limites = getattr(cliente, "limites", None)
	if limites is not None:
		return limites.monto_limite_diario
	return _config_decimal('LIMITE_TRANSACCION_DIARIO_DEFAULT', None)


def obtener_limite_mensual(cliente) -> Decimal:
	"""Devuelve el límite mensual efectivo para el cliente.

	Parámetros
	----------
	cliente : Cliente
		Instancia del modelo Cliente.

	Returns
	-------
	Decimal
		Valor del límite mensual.
	"""
	if getattr(cliente, "usa_limites_default", True):
		return _config_decimal('LIMITE_TRANSACCION_MENSUAL_DEFAULT', None)
	limites = getattr(cliente, "limites", None)
	if limites is not None:
		return limites.monto_limite_mensual
	# Fallback si no existe registro personalizado aún
	return _config_decimal('LIMITE_TRANSACCION_MENSUAL_DEFAULT', None)

def obtener_monto_transacciones_hoy(cliente) -> Decimal:
    """Devuelve el monto total (en PYG) de las transacciones del cliente para hoy.

    Criterio (alineado con la función mensual):
    - Para transacciones de tipo COMPRA se suma `monto_origen` SOLO si `moneda_origen.codigo == 'PYG'`.
    - Para transacciones de tipo VENTA  se suma `monto_destino` SOLO si `moneda_destino.codigo == 'PYG'`.
    - Estados considerados: COMPLETADA, PAGADA, PENDIENTE (ajustar si negocio requiere solo confirmadas).

    Se usa un solo aggregate con Case/When para evitar dos consultas y asegurar consistencia.
    Si no existen transacciones válidas devuelve Decimal('0.00').
    """

    hoy = timezone.localdate()
    estados_validos = ['COMPLETADA', 'PAGADA', 'PENDIENTE']

    qs = Transaccion.objects.filter(
        cliente=cliente,
		fecha_creacion__date=hoy,
        estado__in=estados_validos
    ).filter(
        Q(tipo_transaccion='COMPRA') |
        Q(tipo_transaccion='VENTA')
    ) # DEBUG: Ver la consulta generada
    total = qs.aggregate(
        total=Sum(
            Case(
                When(
                    tipo_transaccion='COMPRA',
                    then='monto_origen'
                ),
                When(
                    tipo_transaccion='VENTA',
                    then='monto_destino'
                ),
                default=Value(0),
                output_field=DecimalField(max_digits=20, decimal_places=8)
            )
        )
    )['total'] or Decimal('0.00')

    # Normalizar a 2 decimales si quieres consistencia con límites (que suelen ser enteros/2 dec)
    try:
        return Decimal(total).quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0.00')

def obtener_monto_transacciones_mes(cliente) -> Decimal:
    """Devuelve el monto total (indistinto de moneda) de las transacciones del cliente en el mes actual.

    Alineado con la lógica de `obtener_monto_transacciones_hoy`:
    - Si es COMPRA suma `monto_origen`.
    - Si es VENTA  suma `monto_destino`.
    - Estados considerados: COMPLETADA, PAGADA, PENDIENTE.

    Si quieres limitar solo a PYG, agrega filtros similares a:
        .filter(Q(tipo_transaccion='COMPRA', moneda_origen__codigo='PYG') | Q(tipo_transaccion='VENTA', moneda_destino__codigo='PYG'))
    antes del aggregate.
    """

    ahora = timezone.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Primer día del mes siguiente
    if inicio_mes.month == 12:
        inicio_mes_siguiente = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
    else:
        inicio_mes_siguiente = inicio_mes.replace(month=inicio_mes.month + 1)

    estados_validos = ['COMPLETADA', 'PAGADA', 'PENDIENTE']

    qs = (Transaccion.objects
          .filter(
              cliente=cliente,
              fecha_creacion__gte=inicio_mes,
              fecha_creacion__lt=inicio_mes_siguiente,
              estado__in=estados_validos
          )
          .filter(Q(tipo_transaccion='COMPRA') | Q(tipo_transaccion='VENTA')))

    total = qs.aggregate(
        total=Sum(
            Case(
                When(tipo_transaccion='COMPRA', then='monto_origen'),
                When(tipo_transaccion='VENTA', then='monto_destino'),
                default=Value(0),
                output_field=DecimalField(max_digits=20, decimal_places=8)
            )
        )
    )['total'] or Decimal('0.00')

    try:
        return Decimal(total).quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0.00')

def verificar_limites(cliente, monto_propuesto: Decimal):
    """Devuelve un dict con el estado de límites para un monto propuesto.

    Estructura retornada:
        {
          'limite_diario': Decimal|None,
          'limite_mensual': Decimal|None,
          'usado_diario': Decimal,
          'usado_mensual': Decimal,
          'restante_diario': Decimal|None,
          'restante_mensual': Decimal|None,
          'excede_diario': bool,
          'excede_mensual': bool,
        }
    Si un límite es None o 0 se interpreta como "ilimitado" y no bloquea.
    """
    from . import utils as _u  # por si se importa indirectamente
    # Para evitar recursión si renombrado, usamos funciones locales ya definidas
    limite_d = obtener_limite_diario(cliente)
    limite_m = obtener_limite_mensual(cliente)
    usado_d = obtener_monto_transacciones_hoy(cliente)
    usado_m = obtener_monto_transacciones_mes(cliente)

    # Tratar None como 0 (sin límite => None => no se bloquea)
    ilimitado_d = (limite_d is None or limite_d == 0)
    ilimitado_m = (limite_m is None or limite_m == 0)

    excede_diario = False
    excede_mensual = False
    restante_d = None
    restante_m = None

    if not ilimitado_d:
        restante_d = limite_d - usado_d
        excede_diario = (usado_d + monto_propuesto) > limite_d
    if not ilimitado_m:
        restante_m = limite_m - usado_m
        excede_mensual = (usado_m + monto_propuesto) > limite_m

    return {
        'limite_diario': limite_d,
        'limite_mensual': limite_m,
        'usado_diario': usado_d,
        'usado_mensual': usado_m,
        'restante_diario': restante_d,
        'restante_mensual': restante_m,
        'excede_diario': excede_diario,
        'excede_mensual': excede_mensual,
    }

Como funciona esto? es un archivo llamado utils.py se utiliza para limitar al usuario la cantidad de dinero que puede manejar en la casa de cambio
Este código es un módulo de utilidades para implementar límites de transacción en una casa de cambio. Te explico cómo funciona:

Propósito Principal
Controlar cuánto dinero puede operar un cliente en transacciones de compra/venta de moneda extranjera durante períodos específicos (diario y mensual).

Componentes Clave:
1. Límites Configurables
python
def obtener_limite_diario(cliente) -> Decimal
def obtener_limite_mensual(cliente) -> Decimal
Límite diario: Máximo que puede operar en un día

Límite mensual: Máximo que puede operar en un mes

2. Jerarquía de Límites
python
if cliente.usa_limites_default:  # Usa límites de categoría
    return límite_default
else:  # Usa límites personalizados
    return cliente.limites.monto_limite_xxx
Límites por defecto: Configuración general para todos los clientes

Límites personalizados: Límites específicos por cliente

3. Seguimiento de Transacciones
python
def obtener_monto_transacciones_hoy(cliente)
def obtener_monto_transacciones_mes(cliente)
Calcula cuánto ha operado el cliente:

Hoy: Suma transacciones del día actual

Este mes: Suma transacciones del mes en curso

4. Verificación en Tiempo Real
python
def verificar_limites(cliente, monto_propuesto)
Antes de una nueva transacción, verifica:

Si excedería el límite diario

Si excedería el límite mensual

Flujo de Uso Típico:
Cliente intenta una transacción de $1,000

El sistema verifica:

¿Cuánto ha operado hoy? (ej: $500)

¿Cuál es su límite diario? (ej: $2,000)

¿La nueva transacción ($1,000) + lo usado ($500) excede $2,000?

Resultado: Permite o bloquea la transacción

Ejemplo Práctico:
python
# Antes de procesar una transacción:
resultado = verificar_limites(cliente, Decimal("1000"))

if resultado['excede_diario']:
    return "Error: Excede límite diario"
elif resultado['excede_mensual']:
    return "Error: Excede límite mensual"
else:
    # Proceder con la transacción
    procesar_transaccion(cliente, monto)
Beneficios para la Casa de Cambio:
Control de riesgo: Limita exposición por cliente

Cumplimiento regulatorio: Ayuda con límites legales

Flexibilidad: Límites generales o personalizados

Prevención de fraudes: Detecta patrones sospechosos

Es una herramienta esencial para la gestión de riesgo operacional en el negocio de cambio de monedas.

Se comunica con la base de datos?
Sí, este código se comunica con la base de datos en varias partes. Te muestro exactamente dónde:

1. Consulta a la tabla Configuracion
python
def _config_decimal(clave: str, fallback: any) -> Decimal:
    valor = Configuracion.obtener_valor(clave, valor_por_defecto=None)
Consulta: Configuracion.obtener_valor() busca en la tabla de configuración

Propósito: Obtener los límites por defecto desde la BD

2. Consultas pesadas a Transaccion
python
def obtener_monto_transacciones_hoy(cliente):
    qs = Transaccion.objects.filter(
        cliente=cliente,
        fecha_creacion__date=hoy,  # FILTRO POR FECHA
        estado__in=estados_validos
    ).aggregate(total=Sum(...))  # SUMA AGREGADA
python
def obtener_monto_transacciones_mes(cliente):
    qs = Transaccion.objects.filter(
        cliente=cliente,
        fecha_creacion__gte=inicio_mes,  # RANGO DE FECHAS
        fecha_creacion__lt=inicio_mes_siguiente
    ).aggregate(total=Sum(...))  # SUMA AGREGADA
Consultas SQL que se generan (aproximadamente):
sql
-- Para límites diarios
SELECT SUM(CASE 
    WHEN tipo_transaccion = 'COMPRA' THEN monto_origen 
    WHEN tipo_transaccion = 'VENTA' THEN monto_destino 
    ELSE 0 END) as total
FROM transacciones_transaccion
WHERE cliente_id = 123 
AND DATE(fecha_creacion) = '2024-01-15'
AND estado IN ('COMPLETADA', 'PAGADA', 'PENDIENTE');

-- Para límites mensuales  
SELECT SUM(...) 
FROM transacciones_transaccion
WHERE cliente_id = 123
AND fecha_creacion >= '2024-01-01'
AND fecha_creacion < '2024-02-01';
Impacto en Performance:
✅ Optimizaciones existentes:
Usa aggregate() con Sum() + Case/When (1 consulta en lugar de 2)

Filtros por índices: cliente_id, fecha_creacion

⚠️ Posibles problemas:
Consultas costosas: Sumar todas las transacciones de un mes puede ser lento

Sin caché: Siempre consulta la BD en tiempo real

Volumen alto: Si el cliente tiene miles de transacciones

Recomendaciones para producción:
python
# 1. Agregar índices en la BD
# CREATE INDEX idx_transacciones_cliente_fecha ON transacciones_transaccion(cliente_id, fecha_creacion);

# 2. Considerar caché para resultados frecuentes
from django.core.cache import cache

def obtener_monto_transacciones_hoy(cliente):
    cache_key = f"transacciones_hoy_{cliente.id}_{timezone.localdate()}"
    return cache.get_or_set(cache_key, _calcular_monto_hoy, timeout=300)  # 5 min
En resumen: Sí, hace varias consultas a la BD que pueden ser costosas según el volumen de transacciones.

Como soluciono esto? tiene que ver que las relaciones estan vacias?
Exactamente, este error confirma que el problema es que las relaciones están vacías o con datos incorrectos. Estás pasando un objeto User donde se espera un objeto Tauser.

Análisis del error
El error ocurre porque en algún lugar del código estás haciendo:

python
# INCORRECTO - Pasando un User donde se espera Tauser
transaccion.tauser = request.user  # ← request.user es User, no Tauser
Solución completa
1. Identificar dónde ocurre el error
Revisa estas partes de tu código:

En views.py - busca donde asignas tauser a una transacción:

python
# Esto está MAL
transaccion.tauser = request.user  # User no es Tauser

# Esto está BIEN
transaccion.tauser = tauser_object  # Objeto Tauser válido
2. Corregir la vista dashboard
python
# views.py
from django.utils import timezone
from transacciones.models import Transaccion
from tauser.models import Tauser

@login_required
def dashboard(request):
    """Dashboard principal del Tauser"""
    
    # OPCIÓN A: Si el usuario está asociado a un Tauser específico
    try:
        # Asumiendo que hay una relación User -> Tauser
        tauser_usuario = request.user.tauser  # Si existe esta relación
        transacciones_hoy = Transaccion.objects.filter(
            fecha_creacion__date=timezone.now().date(),
            tauser=tauser_usuario  # ← Usar el objeto Tauser, no el User
        ).count()
    except AttributeError:
        # OPCIÓN B: Si no hay relación directa, usar un Tauser por defecto
        tauser_por_defecto = Tauser.objects.first()  # O el que corresponda
        transacciones_hoy = Transaccion.objects.filter(
            fecha_creacion__date=timezone.now().date(),
            tauser=tauser_por_defecto
        ).count()
    
    context = {
        'transacciones_hoy': transacciones_hoy,
    }
    return render(request, 'tauser/dashboard.html', context)
3. Corregir las vistas de depósito y extracción
python
# views.py
@login_required
def depositar(request):
    """Vista para procesar depósitos"""
    if request.method == 'POST':
        form = FormDeposito(request.POST)
        if form.is_valid():
            try:
                # OBTENER el Tauser correcto (no el User)
                tauser = obtener_tauser_para_usuario(request.user)
                
                transaccion = Transaccion.objects.create(
                    tipo_transaccion='DEPOSITO',
                    usuario=request.user,
                    monto_origen=form.cleaned_data['monto'],
                    moneda_origen=form.cleaned_data['moneda'],
                    estado='pendiente',
                    tauser=tauser  # ← Pasar el objeto Tauser, no el User
                )
                messages.success(request, 'Depósito registrado exitosamente')
                return redirect('tauser_dashboard')
            except Exception as e:
                messages.error(request, f'Error al procesar el depósito: {str(e)}')
    else:
        form = FormDeposito()
    
    return render(request, 'tauser/depositar.html', {'form': form})

@login_required
def extraer(request):
    """Vista para procesar extracciones"""
    if request.method == 'POST':
        form = FormExtraccion(request.POST)
        if form.is_valid():
            try:
                # OBTENER el Tauser correcto
                tauser = obtener_tauser_para_usuario(request.user)
                
                transaccion = Transaccion.objects.create(
                    tipo_transaccion='EXTRACCION',
                    usuario=request.user,
                    monto_origen=form.cleaned_data['monto'],
                    moneda_origen=form.cleaned_data['moneda'],
                    estado='pendiente',
                    tauser=tauser  # ← Pasar el objeto Tauser correcto
                )
                messages.success(request, 'Solicitud de extracción registrada')
                return redirect('tauser_dashboard')
            except Exception as e:
                messages.error(request, f'Error al procesar la extracción: {str(e)}')
    else:
        form = FormExtraccion()
    
    return render(request, 'tauser/extraer.html', {'form': form})
4. Función auxiliar para obtener el Tauser
python
# services/tauser_utils.py
from tauser.models import Tauser

def obtener_tauser_para_usuario(usuario):
    """
    Obtiene el Tauser asociado a un usuario.
    Si no existe relación, devuelve un Tauser por defecto.
    """
    try:
        # Si existe relación directa User -> Tauser
        return usuario.tauser
    except AttributeError:
        # Si no existe relación, usar lógica de negocio
        # Por ejemplo: el primer Tauser activo
        return Tauser.objects.filter(estado='ACTIVO').first()
    
    # O si quieres crear una relación User-Tauser, agrega esto al modelo User:
    # tauser = models.ForeignKey(Tauser, on_delete=models.SET_NULL, null=True, blank=True)
5. Solución temporal rápida
Si quieres una solución inmediata para probar:

python
# views.py - solución temporal
@login_required
def dashboard(request):
    """Dashboard principal del Tauser - SOLUCIÓN TEMPORAL"""
    
    # TEMPORAL: Usar cualquier Tauser existente
    tauser_cualquiera = Tauser.objects.first()
    
    if tauser_cualquiera:
        transacciones_hoy = Transaccion.objects.filter(
            fecha_creacion__date=timezone.now().date(),
            tauser=tauser_cualquiera
        ).count()
    else:
        transacciones_hoy = 0
    
    context = {
        'transacciones_hoy': transacciones_hoy,
    }
    return render(request, 'tauser/dashboard.html', context)
6. Verificar que existan Tausers en la base de datos
Asegúrate de que haya al menos un Tauser creado:

python
# En el shell de Django
python manage.py shell

from tauser.models import Tauser
# Crear un Tauser si no existe
if not Tauser.objects.exists():
    Tauser.objects.create(
        nombre="Tauser Principal",
        direccion="Dirección principal",
        ciudad="Santiago",
        pais="Chile",
        estado="ACTIVO"
    )
¿Cuál es tu estructura actual?
Para darte la solución exacta, necesito saber:

¿Existe una relación entre User y Tauser en tus modelos?

¿Cómo se supone que un usuario debe estar asociado a un Tauser?

¿Tienes Tausers creados en la base de datos?

La solución más robusta sería agregar una relación ForeignKey desde User hacia Tauser en tu modelo de usuarios.

¿Prefieres que implementemos la solución temporal o la solución definitiva con la relación User-Tauser?