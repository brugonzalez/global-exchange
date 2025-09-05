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

    Parameters
    ----------
    sender : Model
        Modelo que disparó la señal (:class:`Usuario`).
    instance : Usuario
        Instancia del usuario recién guardado.
    created : bool
        ``True`` si se acaba de crear el usuario, ``False`` si fue una actualización.

    Notes
    -----
    - Si el rol "Usuario" no existe en la base de datos (ejemplo: migraciones iniciales),
      no se hace nada para evitar errores.
    - El rol se agrega usando ``instance.roles.add()`` inmediatamente después de la creación.
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