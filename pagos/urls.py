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