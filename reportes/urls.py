from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    # Gestión de reportes
    path('', views.VistaListaReportes.as_view(), name='lista_reportes'),
    path('crear/', views.VistaCrearReporte.as_view(), name='crear_reporte'),
    path('<int:pk>/', views.VistaDetalleReporte.as_view(), name='detalle_reporte'),
    path('<int:id_reporte>/descargar/', views.VistaDescargarReporte.as_view(), name='descargar_reporte'),
    
    # Panel de control y analíticas
    path('panel-analiticas/', views.VistaPanelAnaliticas.as_view(), name='panel_analiticas'),
    path('ganancias/', views.VistaAnalisisGanancias.as_view(), name='analisis_ganancias'),
    
    # Endpoints de API
    path('api/metricas/', views.APIVistaMetricasPanel.as_view(), name='api_metricas'),
    path('api/generar/', views.APIVistaGenerarReporte.as_view(), name='api_generar_reporte'),
]