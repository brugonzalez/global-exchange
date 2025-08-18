from django.contrib import admin
from .models import (
    PlantillaNotificacion, Notificacion, PreferenciaNotificacion,
    TicketSoporte, MensajeTicket
)


@admin.register(PlantillaNotificacion)
class AdminPlantillaNotificacion(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_plantilla', 'esta_activa', 'fecha_creacion']
    list_filter = ['tipo_plantilla', 'esta_activa']
    search_fields = ['nombre', 'asunto_email']


@admin.register(Notificacion)
class AdminNotificacion(admin.ModelAdmin):
    list_display = ['asunto', 'usuario', 'tipo_notificacion', 'estado', 
                   'fecha_creacion', 'fecha_envio']
    list_filter = ['tipo_notificacion', 'estado', 'fecha_creacion']
    search_fields = ['asunto', 'usuario__username', 'usuario__email']
    readonly_fields = ['fecha_creacion', 'fecha_envio', 'fecha_entrega', 'fecha_lectura']
    ordering = ['-fecha_creacion']


@admin.register(PreferenciaNotificacion)
class AdminPreferenciaNotificacion(admin.ModelAdmin):
    list_display = ['usuario', 'email_actualizaciones_transaccion', 'email_alertas_tasa', 
                   'email_alertas_seguridad', 'frecuencia_notificacion']
    list_filter = ['frecuencia_notificacion', 'email_actualizaciones_transaccion', 
                  'email_alertas_tasa', 'email_alertas_seguridad']
    search_fields = ['usuario__username', 'usuario__email']


class MensajeTicketEnLinea(admin.TabularInline):
    model = MensajeTicket
    extra = 0
    readonly_fields = ['fecha_creacion']
    fields = ['autor', 'mensaje', 'es_interno', 'fecha_creacion']


@admin.register(TicketSoporte)
class AdminTicketSoporte(admin.ModelAdmin):
    list_display = ['numero_ticket', 'asunto', 'nombre_usuario', 'categoria', 
                   'prioridad', 'estado', 'asignado_a', 'fecha_creacion']
    list_filter = ['categoria', 'prioridad', 'estado', 'fecha_creacion']
    search_fields = ['numero_ticket', 'asunto', 'nombre_usuario', 'email_usuario']
    readonly_fields = ['numero_ticket', 'fecha_creacion', 'fecha_actualizacion']
    inlines = [MensajeTicketEnLinea]
    
    fieldsets = (
        ('Información del Ticket', {
            'fields': ('numero_ticket', 'asunto', 'descripcion', 'categoria', 'prioridad', 'estado')
        }),
        ('Usuario', {
            'fields': ('usuario', 'nombre_usuario', 'email_usuario')
        }),
        ('Asignación', {
            'fields': ('asignado_a',)
        }),
        ('Resolución', {
            'fields': ('resolucion', 'fecha_resolucion', 'resuelto_por')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion')
        })
    )