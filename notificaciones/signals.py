from django.db.models.signals import post_save
from django.dispatch import receiver
from cuentas.models import Usuario
from .models import PreferenciaNotificacion


@receiver(post_save, sender=Usuario)
def crear_preferencias_notificacion(sender, instance, created, **kwargs):
    """
    Crea las preferencias de notificación predeterminadas cuando se crea un usuario.
    """
    if created:
        PreferenciaNotificacion.objects.get_or_create(
            usuario=instance,
            defaults={
                'email_actualizaciones_transaccion': True,
                'email_alertas_tasa': True,
                'email_alertas_seguridad': True,
                'email_marketing': False,
                'email_notificaciones_sistema': True,
            }
        )