from django.contrib import admin
from .models import (
    Reporte, MetricaPanel, PlantillaReporte, ReporteProgramado
)


@admin.register(Reporte)
class AdminReporte(admin.ModelAdmin):
    list_display = ['nombre_reporte', 'tipo_reporte', 'formato', 'estado', 
                   'solicitado_por', 'fecha_creacion', 'conteo_descargas']
    list_filter = ['tipo_reporte', 'formato', 'estado', 'fecha_creacion']
    search_fields = ['nombre_reporte', 'solicitado_por__username']
    readonly_fields = ['fecha_creacion', 'fecha_inicio', 'fecha_finalizacion', 'tamano_archivo']
    ordering = ['-fecha_creacion']


@admin.register(MetricaPanel)
class AdminMetricaPanel(admin.ModelAdmin):
    list_display = ['nombre_metrica', 'tipo_metrica', 'valor', 'moneda', 
                   'inicio_periodo', 'fin_periodo', 'fecha_calculo']
    list_filter = ['tipo_metrica', 'moneda', 'fecha_calculo']
    search_fields = ['nombre_metrica']
    ordering = ['-fecha_calculo']


@admin.register(PlantillaReporte)
class AdminPlantillaReporte(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_reporte', 'formato_defecto', 'es_publica', 'creado_por']
    list_filter = ['tipo_reporte', 'formato_defecto', 'es_publica']
    search_fields = ['nombre', 'descripcion']


@admin.register(ReporteProgramado)
class AdminReporteProgramado(admin.ModelAdmin):
    list_display = ['nombre', 'plantilla', 'frecuencia', 'esta_activo', 'proxima_ejecucion', 'conteo_ejecuciones']
    list_filter = ['frecuencia', 'esta_activo']
    search_fields = ['nombre']