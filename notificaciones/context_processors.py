"""
Context processors para la aplicación de notificaciones.
"""

from .models import Notificacion


def contador_notificaciones(request):
    """
    Proporciona el contador de notificaciones no leídas para el usuario autenticado.
    """
    if request.user.is_authenticated:
        # Contar notificaciones de tipo IN_APP que no han sido leídas
        notificaciones_no_leidas = Notificacion.objects.filter(
            usuario=request.user,
            tipo_notificacion='IN_APP',
            estado__in=['ENVIADO', 'ENTREGADO']
        ).count()
        
        return {
            'contador_notificaciones': notificaciones_no_leidas,
            'tiene_notificaciones': notificaciones_no_leidas > 0
        }
    
    return {
        'contador_notificaciones': 0,
        'tiene_notificaciones': False
    }