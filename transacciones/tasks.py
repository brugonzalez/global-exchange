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