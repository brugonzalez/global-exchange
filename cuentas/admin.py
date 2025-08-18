from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AdministradorUsuarioBase
from .models import Usuario, VerificacionEmail, RestablecimientoContrasena, RegistroAuditoria


@admin.register(Usuario)
class AdministradorUsuario(AdministradorUsuarioBase):
    """Configuración del admin para el modelo de Usuario personalizado"""
    list_display = ['username', 'email', 'nombre_completo', 'email_verificado', 
                   'is_active', 'is_staff', 'fecha_creacion']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'email_verificado', 'fecha_creacion']
    search_fields = ['username', 'email', 'nombre_completo']
    ordering = ['-fecha_creacion']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('nombre_completo', 'email')}),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Verificación y Seguridad', {
            'fields': ('email_verificado', 'intentos_fallidos_login', 'cuenta_bloqueada_hasta'),
        }),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
        ('Cliente Activo', {'fields': ('ultimo_cliente_seleccionado',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'nombre_completo', 'contrasena1', 'contrasena2'),
        }),
    )


@admin.register(VerificacionEmail)
class AdministradorVerificacionEmail(admin.ModelAdmin):
    list_display = ['usuario', 'token', 'fecha_creacion', 'utilizado']
    list_filter = ['utilizado', 'fecha_creacion']
    search_fields = ['usuario__username', 'usuario__email', 'token']
    readonly_fields = ['token', 'fecha_creacion']


@admin.register(RestablecimientoContrasena)
class AdministradorRestablecimientoContrasena(admin.ModelAdmin):
    list_display = ['usuario', 'token', 'fecha_creacion', 'utilizado']
    list_filter = ['utilizado', 'fecha_creacion']
    search_fields = ['usuario__username', 'usuario__email', 'token']
    readonly_fields = ['token', 'fecha_creacion']


@admin.register(RegistroAuditoria)
class AdministradorRegistroAuditoria(admin.ModelAdmin):
    list_display = ['usuario', 'accion', 'marca_de_tiempo', 'direccion_ip']
    list_filter = ['accion', 'marca_de_tiempo']
    search_fields = ['usuario__username', 'descripcion', 'direccion_ip']
    readonly_fields = ['usuario', 'accion', 'descripcion', 'direccion_ip', 
                      'agente_usuario', 'marca_de_tiempo', 'datos_adicionales']
    date_hierarchy = 'marca_de_tiempo'
    
    def has_add_permission(self, solicitud):
        return False
    
    def has_change_permission(self, solicitud, objeto=None):
        return False