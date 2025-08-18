from django.contrib import admin
from .models import (
    CategoriaCliente, Cliente, ClienteUsuario, MonedaFavorita, SaldoCliente
)


@admin.register(CategoriaCliente)
class AdminCategoriaCliente(admin.ModelAdmin):
    list_display = ['nombre', 'limite_transaccion_diario', 'limite_transaccion_mensual', 
                   'margen_tasa_preferencial', 'nivel_prioridad']
    list_filter = ['nombre', 'nivel_prioridad']
    ordering = ['nivel_prioridad', 'nombre']


class ClienteUsuarioEnLinea(admin.TabularInline):
    model = ClienteUsuario
    extra = 0
    fields = ['usuario', 'rol', 'esta_activo', 'fecha_asignacion']
    readonly_fields = ['fecha_asignacion']


class MonedaFavoritaEnLinea(admin.TabularInline):
    model = MonedaFavorita
    extra = 0
    fields = ['moneda', 'orden']


class SaldoClienteEnLinea(admin.TabularInline):
    model = SaldoCliente
    extra = 0
    fields = ['moneda', 'saldo', 'ultima_actualizacion']
    readonly_fields = ['ultima_actualizacion']


@admin.register(Cliente)
class AdminCliente(admin.ModelAdmin):
    list_display = ['obtener_nombre_completo', 'tipo_cliente', 'categoria', 'estado', 
                   'numero_identificacion', 'fecha_creacion']
    list_filter = ['tipo_cliente', 'estado', 'categoria', 'fecha_creacion']
    search_fields = ['nombre', 'apellido', 'nombre_empresa', 
                    'numero_identificacion', 'email']
    inlines = [ClienteUsuarioEnLinea, MonedaFavoritaEnLinea, SaldoClienteEnLinea]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('tipo_cliente', 'estado', 'categoria')
        }),
        ('Persona Física', {
            'fields': ('nombre', 'apellido'),
            'classes': ('collapse',)
        }),
        ('Persona Jurídica', {
            'fields': ('nombre_empresa', 'representante_legal'),
            'classes': ('collapse',)
        }),
        ('Información de Contacto', {
            'fields': ('numero_identificacion', 'email', 'telefono', 'direccion')
        }),
        ('Información Financiera', {
            'fields': ('saldo_cuenta',)
        }),
        ('Metadatos', {
            'fields': ('creado_por',),
            'classes': ('collapse',)
        })
    )
    
    def obtener_nombre_completo(self, obj):
        return obj.obtener_nombre_completo()
    obtener_nombre_completo.short_description = 'Nombre Completo'


@admin.register(ClienteUsuario)
class AdminClienteUsuario(admin.ModelAdmin):
    list_display = ['cliente', 'usuario', 'rol', 'esta_activo', 'fecha_asignacion']
    list_filter = ['rol', 'esta_activo', 'fecha_asignacion']
    search_fields = ['cliente__nombre', 'cliente__apellido', 
                    'cliente__nombre_empresa', 'usuario__username', 'usuario__email']