from django.urls import path
from . import views

app_name = 'divisas'

urlpatterns = [
    # Vistas públicas (no requieren autenticación)
    path('', views.VistaPanelControl.as_view(), name='panel_de_control'),
    path('tasas/', views.VistaTasasCambio.as_view(), name='tasas'),
    path('tasas/historial/<str:codigo_moneda>/', views.VistaHistorialTasa.as_view(), name='historial_tasa'),
    path('simular/', views.VistaSimularTransaccion.as_view(), name='simular'),
    
    # Endpoints de API para datos en tiempo real
    path('api/tasas/', views.APIVistaTasasActuales.as_view(), name='api_tasas'),
    path('api/tasas/actualizar/', views.APIVistaActualizarTasas.as_view(), name='api_actualizar_tasas'),
    path('api/simular/', views.APIVistaSimulacion.as_view(), name='api_simular'),
    
    # Vistas de administración (solo usuarios autenticados)
    path('admin/tasas/', views.VistaGestionarTasas.as_view(), name='gestionar_tasas'),
    path('admin/precio-base/actualizar/', views.VistaGestionarTasas.as_view(), name='actualizar_precio_base'),
    path('admin/tasas/actualizar/', views.VistaGestionarTasas.as_view(), name='actualizar_tasa'),
    path('admin/comisiones/actualizar/', views.actualizar_comisiones, name='actualizar_comisiones'),
    
    # Gestión de monedas (CRUD)
    path('admin/monedas/', views.VistaGestionarMonedas.as_view(), name='gestionar_monedas'),
    path('admin/monedas/crear/', views.VistaCrearMoneda.as_view(), name='crear_moneda'),
    path('admin/monedas/<int:moneda_id>/editar/', views.VistaEditarMoneda.as_view(), name='editar_moneda'),
    path('admin/monedas/<int:moneda_id>/eliminar/', views.VistaEliminarMoneda.as_view(), name='eliminar_moneda'),
    path('admin/monedas/<int:moneda_id>/toggle-estado/', views.VistaToggleEstadoMoneda.as_view(), name='toggle_estado_moneda'),
    
    path('admin/metodos-pago/', views.VistaGestionarMetodosPago.as_view(), name='gestionar_metodos_pago'),
    
    # Alertas de usuario
    path('alertas/', views.VistaGestionarAlertas.as_view(), name='gestionar_alertas'),
    path('alertas/crear/', views.VistaCrearAlerta.as_view(), name='crear_alerta'),
    path('alertas/eliminar/<int:id_alerta>/', views.VistaEliminarAlerta.as_view(), name='eliminar_alerta'),
    
    # Monedas favoritas
    path('favoritos/', views.VistaGestionarFavoritos.as_view(), name='gestionar_favoritos'),
    path('api/favoritos/alternar/', views.APIVistaAlternarFavorito.as_view(), name='api_alternar_favorito'),
    path('api/favoritos/reordenar/', views.APIVistaReordenarFavoritos.as_view(), name='api_reordenar_favoritos'),
]