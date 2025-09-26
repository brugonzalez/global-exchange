from django.urls import path
from . import views

app_name = 'transacciones'

urlpatterns = [
    # Operaciones de transacción
    path('', views.VistaHistorialTransacciones.as_view(), name='lista_transacciones'),
    path('comprar/', views.VistaTransaccionCompra.as_view(), name='comprar'),
    path('vender/', views.VistaTransaccionVenta.as_view(), name='vender'),
    
    # Gestión de facturas
    path('facturas/', views.VistaListaFacturas.as_view(), name='lista_facturas'),
    path('facturas/<str:numero_factura>/', views.VistaDetalleFactura.as_view(), name='detalle_factura'),
    path('facturas/<str:numero_factura>/pdf/', views.VistaPDFFactura.as_view(), name='factura_pdf'),
    
    # Funcionalidad de exportación (movida desde la ruta de historial)
    path('exportar/', views.VistaExportarHistorial.as_view(), name='exportar_historial'),
    
    # Endpoints de API
    path('api/crear/', views.APIVistaCrearTransaccion.as_view(), name='api_crear_transaccion'),
    path('api/stripe/confirmar/', views.VistaConfirmarPagoStripe.as_view(), name='api_stripe_confirmar'),
    path('api/<uuid:id_transaccion>/estado/', views.APIVistaEstadoTransaccion.as_view(), name='api_estado_transaccion'),
    
    # Patrones genéricos (deben ir al final)
    path('<uuid:id_transaccion>/', views.VistaDetalleTransaccion.as_view(), name='detalle_transaccion'),
    path('<uuid:id_transaccion>/cancelar/', views.VistaCancelarTransaccion.as_view(), name='cancelar_transaccion'),
    
    path('configurar/', views.VistaConfiguracionTransaccion.as_view(), name='configurar_transaccion'),
    
]