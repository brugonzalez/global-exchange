from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario, Rol


@receiver(post_save, sender=Usuario)
def asignar_rol_usuario_por_defecto(sender, instance, created, **kwargs):
    """
    Asigna automáticamente el rol 'Usuario' a los nuevos usuarios creados.
    
    Este signal escucha el evento :func:`django.db.models.signals.post_save` 
    del modelo :class:`Usuario` y, cuando se crea un nuevo usuario, intenta
    asignarle el rol básico de la aplicación.

    Args:
        sender (Model): Modelo que dispara la señal (:class:`Usuario`).
        instance (Usuario): Instancia de usuario recién guardada.
        created (bool): ``True`` si el usuario fue creado, ``False`` si se actualizó.
        **kwargs: Argumentos adicionales provistos por la señal.

    Notas:
        - Si el rol ``Usuario`` no existe (p. ej., durante migraciones iniciales),
          no se realiza ninguna acción.
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