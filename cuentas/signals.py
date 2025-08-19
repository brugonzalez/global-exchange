from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario, Rol


@receiver(post_save, sender=Usuario)
def asignar_rol_usuario_por_defecto(sender, instance, created, **kwargs):
    """
    Asigna automáticamente el rol 'Usuario' a los nuevos usuarios creados.
    """
    if created:
        try:
            # Obtener el rol 'Usuario'
            rol_usuario = Rol.objects.get(nombre_rol='Usuario')
            # Asignar el rol al usuario recién creado
            instance.roles.add(rol_usuario)
        except Rol.DoesNotExist:
            # Si el rol 'Usuario' no existe, no hacer nada
            # Esto puede suceder durante las migraciones iniciales
            pass