from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AdministradorUsuarioBase
from .models import Usuario, VerificacionEmail, RestablecimientoContrasena, RegistroAuditoria, Rol, Permiso


@admin.register(Permiso)
class AdministradorPermiso(admin.ModelAdmin):
    """Configuración del admin para el modelo Permiso"""
    list_display = ['codename', 'descripcion', 'fecha_creacion']
    list_filter = ['fecha_creacion']
    search_fields = ['codename', 'descripcion']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    ordering = ['descripcion']


@admin.register(Rol)
class AdministradorRol(admin.ModelAdmin):
    """Configuración del admin para el modelo Rol"""
    list_display = ['nombre_rol', 'descripcion', 'es_sistema', 'fecha_creacion']
    list_filter = ['es_sistema', 'fecha_creacion']
    search_fields = ['nombre_rol', 'descripcion']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    filter_horizontal = ['permisos']
    ordering = ['nombre_rol']
    
    def get_readonly_fields(self, request, obj=None):
        """Hacer que los roles del sistema no sean editables en ciertos campos"""
        readonly_fields = list(self.readonly_fields)
        if obj and obj.es_sistema and obj.nombre_rol == 'Administrador':
            # El rol de Administrador no debe ser editable en sus permisos críticos
            readonly_fields.extend(['nombre_rol', 'es_sistema'])
        return readonly_fields

    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar roles del sistema"""
        if obj and obj.es_sistema:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Usuario)
class AdministradorUsuario(AdministradorUsuarioBase):
    """Configuración del admin para el modelo de Usuario personalizado"""
    list_display = ['username', 'email', 'nombre_completo', 'email_verificado', 
                   'is_active', 'is_staff', 'fecha_creacion', 'mostrar_roles']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'email_verificado', 
                  'fecha_creacion', 'roles']
    search_fields = ['username', 'email', 'nombre_completo']
    ordering = ['-fecha_creacion']
    filter_horizontal = ['roles', 'groups', 'user_permissions']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('nombre_completo', 'email')}),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Roles del Sistema', {
            'fields': ('roles',),
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
    
    def mostrar_roles(self, obj):
        """Muestra los roles del usuario en la lista"""
        return ', '.join([rol.nombre_rol for rol in obj.roles.all()])
    mostrar_roles.short_description = 'Roles'


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