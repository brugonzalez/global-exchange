# signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Transaccion
import logging

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Transaccion)
def verificar_expiracion_transaccion(sender, instance, **kwargs):
    """
    Verifica y marca como expirada una transacción antes de guardarla.
    
    Este signal se ejecuta antes de guardar una transacción y verifica
    si ha expirado según el tiempo configurado.
    """
    # Solo procesar si la instancia ya existe en la BD (no es nueva)
    if instance.pk:
        try:
            # Obtener la versión actual de la BD
            transaccion_actual = Transaccion.objects.get(pk=instance.pk)
            
            # Si el estado era PENDIENTE y ahora ha expirado
            if (transaccion_actual.estado == 'PENDIENTE' and 
                instance.ha_expirado and 
                instance.estado == 'PENDIENTE'):
                
                instance.estado = 'CANCELADA'
                instance.fecha_cancelacion = timezone.now()
                instance.motivo_cancelacion = f"Expirada automáticamente después de {instance.tiempo_expiracion_minutos} minutos"
                
                logger.info(f"Transacción {instance.id} marcada como expirada")
                
        except Transaccion.DoesNotExist:
            # Si no existe, es una nueva instancia, no hacer nada
            pass
        
        
@receiver(post_save, sender=Transaccion)
def notificar_expiracion_transaccion(sender, instance, created, **kwargs):
    """
    Envía notificación cuando una transacción es marcada como expirada.
    
    Este signal se ejecuta después de guardar una transacción y verifica
    si fue marcada como cancelada por expiración.
    """
    # No procesar si es creación nueva
    if created:
        return
    
    try:
        # Obtener versión anterior de la transacción
        transaccion_anterior = Transaccion.objects.get(pk=instance.pk)
        
        # Verificar si cambió de PENDIENTE a CANCELADA por expiración
        if (transaccion_anterior.estado == 'PENDIENTE' and 
            instance.estado == 'CANCELADA' and 
            'Expirada automáticamente' in instance.motivo_cancelacion):
            
            # Enviar notificación
            from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
            
            llamar_tarea_con_fallback(
                enviar_notificacion_transaccion, 
                instance.id, 
                'TRANSACCION_EXPIRADA'
            )
            
            logger.info(f"Notificación enviada por expiración de transacción {instance.id}")
            
    except Transaccion.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error al enviar notificación de expiración: {e}")