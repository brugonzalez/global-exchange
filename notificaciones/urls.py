from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    # Gestión de notificaciones
    path('', views.VistaListaNotificaciones.as_view(), name='lista_notificaciones'),
    path('<int:id_notificacion>/leer/', views.VistaMarcarComoLeido.as_view(), name='marcar_como_leido'),
    
    # Preferencias de notificación
    path('preferencias/', views.VistaPreferenciasNotificacion.as_view(), name='preferencias'),
    path('preferencias/actualizar/', views.VistaActualizarPreferencias.as_view(), name='actualizar_preferencias'),
    
    # Sistema de soporte
    path('soporte/', views.VistaSoporte.as_view(), name='soporte'),
    path('soporte/crear/', views.VistaCrearTicket.as_view(), name='crear_ticket'),
    path('soporte/tickets/', views.VistaListaTickets.as_view(), name='lista_tickets'),
    path('soporte/tickets/<str:numero_ticket>/', views.VistaDetalleTicket.as_view(), name='detalle_ticket'),
    path('soporte/tickets/<str:numero_ticket>/responder/', views.VistaResponderTicket.as_view(), name='responder_ticket'),
    
    # Endpoints de API
    path('api/conteo-no-leidas/', views.APIVistaConteoNoLeidas.as_view(), name='api_conteo_no_leidas'),
]