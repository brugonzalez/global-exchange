from django.contrib import admin
from .models import (
    Transaccion, SimulacionTransaccion, Factura, ComisionTransaccion
)


@admin.register(Transaccion)
class AdminTransaccion(admin.ModelAdmin):
    list_display = ['numero_transaccion', 'tipo_transaccion', 'cliente', 'estado', 
                   'monto_origen', 'moneda_origen', 'moneda_destino', 'fecha_creacion']
    list_filter = ['tipo_transaccion', 'estado', 'moneda_origen', 'moneda_destino', 'fecha_creacion']
    search_fields = ['numero_transaccion', 'cliente__nombre', 'cliente__apellido', 
                    'cliente__nombre_empresa', 'usuario__username']
    readonly_fields = ['id_transaccion', 'numero_transaccion', 'fecha_creacion', 'fecha_actualizacion']
    ordering = ['-fecha_creacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero_transaccion', 'tipo_transaccion', 'estado')
        }),
        ('Partes Involucradas', {
            'fields': ('cliente', 'usuario')
        }),
        ('Detalles de Monedas', {
            'fields': ('moneda_origen', 'moneda_destino', 
                      'monto_origen', 'monto_destino', 'tasa_cambio')
        }),
        ('Comisiones', {
            'fields': ('monto_comision', 'moneda_comision')
        }),
        ('Información de Pago', {
            'fields': ('metodo_pago', 'referencia_pago', 'info_cuenta_bancaria')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion', 'fecha_completado', 'fecha_cancelacion')
        }),
        ('Notas', {
            'fields': ('notas', 'motivo_cancelacion')
        })
    )


@admin.register(Factura)
class AdminFactura(admin.ModelAdmin):
    list_display = ['numero_factura', 'tipo_factura', 'cliente', 'estado', 
                   'monto_total', 'moneda', 'fecha_emision']
    list_filter = ['tipo_factura', 'estado', 'moneda', 'fecha_emision']
    search_fields = ['numero_factura', 'cliente__nombre', 'cliente__apellido', 
                    'cliente__nombre_empresa']
    readonly_fields = ['numero_factura', 'fecha_emision']
    ordering = ['-fecha_emision']


@admin.register(SimulacionTransaccion)
class AdminSimulacionTransaccion(admin.ModelAdmin):
    list_display = ['usuario', 'tipo_transaccion', 'moneda_origen', 'moneda_destino', 
                   'monto_origen', 'monto_destino', 'fecha_creacion']
    list_filter = ['tipo_transaccion', 'moneda_origen', 'moneda_destino', 'fecha_creacion']
    search_fields = ['usuario__username', 'usuario__email']
    readonly_fields = ['fecha_creacion']
    ordering = ['-fecha_creacion']


@admin.register(ComisionTransaccion)
class AdminComisionTransaccion(admin.ModelAdmin):
    list_display = ['transaccion', 'tipo_comision', 'monto', 'moneda', 'descripcion']
    list_filter = ['tipo_comision', 'moneda']
    search_fields = ['transaccion__numero_transaccion', 'descripcion']