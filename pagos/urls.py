"""
URLs de la aplicación de pagos.

Este módulo define las rutas principales relacionadas con:

- Gestión de métodos de pago (asociar, desvincular, activar/desactivar).
- Visualización de medios de pago asociados a un cliente.
- Administración de métodos de pago disponibles.

Cada ruta está asociada a una vista basada en clase (CBV) o función de la app ``pagos.views``.
"""
from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    # Gestión de pagos
    path('medios/<int:id_cliente>/', views.MediosPago.as_view(), name='medios_pago'),
    path('asociar_medio_pago/<int:id_cliente>/', views.VistaAsociarMedioPago.as_view(), name='asociar_medio_pago'),
    path('desvincular/<int:pk>/', views.desvincular_medio_pago, name='desvincular_medio_pago'),
    path('gestion-metodos-pago/', views.VistaGestionMetodosPago.as_view(), name='gestion_metodos_pago'),
    path('toggle-metodo-pago/<int:metodo_id>/', views.VistaToggleMetodoPago.as_view(), name='toggle_metodo_pago'),
]