from django.contrib import admin
from .models import (
    Moneda, TasaCambio, HistorialTasaCambio, 
    MetodoPago, AlertaTasa
)


@admin.register(Moneda)
class AdminMoneda(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'esta_activa', 
                   'es_moneda_base']
    list_filter = [ 'esta_activa', 'es_moneda_base']
    search_fields = ['codigo', 'nombre']
    ordering = ['codigo']


@admin.register(TasaCambio)
class AdminTasaCambio(admin.ModelAdmin):
    list_display = ['moneda', 'moneda_base', 'tasa_compra', 'tasa_venta' 
                   , 'esta_activa', 'fecha_actualizacion']
    list_filter = [ 'esta_activa', 'fecha_actualizacion']
    search_fields = ['moneda__codigo', 'moneda_base__codigo']
    ordering = ['-fecha_actualizacion']


@admin.register(HistorialTasaCambio)
class AdminHistorialTasaCambio(admin.ModelAdmin):
    list_display = ['moneda', 'moneda_base', 'tasa_compra', 'tasa_venta', 'marca_de_tiempo']
    list_filter = ['moneda', 'marca_de_tiempo']
    search_fields = ['moneda__codigo', 'moneda_base__codigo']
    ordering = ['-marca_de_tiempo']
    date_hierarchy = 'marca_de_tiempo'


@admin.register(MetodoPago)
class AdminMetodoPago(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_metodo', 'esta_activo', 'soporta_compra', 
                   'soporta_venta', 'monto_minimo', 'monto_maximo']
    list_filter = ['tipo_metodo', 'esta_activo', 'soporta_compra', 'soporta_venta']
    search_fields = ['nombre']


@admin.register(AlertaTasa)
class AdminAlertaTasa(admin.ModelAdmin):
    list_display = ['usuario', 'moneda', 'tipo_alerta', 'tasa_objetivo', 
                   'esta_activa', 'ultima_activacion', 'conteo_activaciones']
    list_filter = ['tipo_alerta', 'esta_activa', 'moneda']
    search_fields = ['usuario__username', 'moneda__codigo']