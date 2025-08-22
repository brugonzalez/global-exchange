from django.urls import path
from . import views

from .views import (
    VistaSolicitudDesbloqueoCuenta,
    VistaVerificarCodigoDesbloqueo,
)

app_name = 'cuentas'

urlpatterns = [
    # Autenticación
    path('iniciar-sesion/', views.VistaLogin.as_view(), name='iniciar_sesion'),
    path('cerrar-sesion/', views.VistaLogout.as_view(), name='cerrar_sesion'),
    path('registro/', views.VistaRegistro.as_view(), name='registro'),
    path('verificar-email/<str:token>/', views.VistaVerificarEmail.as_view(), name='verificar_email'),
    
    # Gestión de contraseña
    path('contrasena/restablecer/', views.VistaSolicitudRestablecimientoContrasena.as_view(), name='restablecer_contrasena'),
    path('contrasena/restablecer/<str:token>/', views.VistaRestablecimientoContrasena.as_view(), name='restablecer_contrasena_confirmar'),
    path('contrasena/cambiar/', views.VistaCambioContrasena.as_view(), name='cambiar_contrasena'),
    
    # Gestión de perfil
    path('perfil/', views.VistaPerfil.as_view(), name='perfil'),
    path('perfil/editar/', views.VistaEditarPerfil.as_view(), name='editar_perfil'),
    
    # Selección de cliente
    path('seleccionar-cliente/', views.VistaSeleccionarCliente.as_view(), name='seleccionar_cliente'),
    path('cambiar-cliente/<int:id_cliente>/', views.VistaCambiarCliente.as_view(), name='cambiar_cliente'),
    path('deseleccionar-cliente/', views.VistaDeseleccionarCliente.as_view(), name='deseleccionar_cliente'),
    
    # Gestión de iToken/2FA
    path('itoken/configurar/', views.VistaConfiguracionDosFactores.as_view(), name='itoken_configurar'),
    path('itoken/activar/', views.VistaActivarDosFactores.as_view(), name='itoken_activar'),
    path('itoken/verificar/', views.VistaVerificarDosFactores.as_view(), name='itoken_verificar'),
    path('itoken/verificar-sensible/', views.VistaVerificarDosFactoresSensible.as_view(), name='itoken_verificar_sensible'),
    path('itoken/tokens-respaldo/', views.VistaTokensRespaldoDosFactores.as_view(), name='itoken_tokens_respaldo'),
    path('itoken/desactivar/', views.VistaDesactivarDosFactores.as_view(), name='itoken_desactivar'),
    
    # Gestión de Roles y Permisos (solo administradores)
    path('admin/roles/', views.VistaGestionarRoles.as_view(), name='gestionar_roles'),
    path('admin/roles/crear/', views.VistaCrearRol.as_view(), name='crear_rol'),
    path('admin/roles/editar/<int:rol_id>/', views.VistaEditarRol.as_view(), name='editar_rol'),
    path('admin/roles/eliminar/<int:rol_id>/', views.VistaEliminarRol.as_view(), name='eliminar_rol'),
    
    # Asignación de Roles a Usuarios
    path('admin/usuarios-roles/', views.VistaGestionarRolesUsuarios.as_view(), name='gestionar_roles_usuarios'),
    path('admin/usuarios/<int:usuario_id>/roles/', views.VistaAsignarRolesUsuario.as_view(), name='asignar_roles_usuario'),
    path('desbloqueo/', VistaSolicitudDesbloqueoCuenta.as_view(), name='solicitud_desbloqueo'),
    path('desbloqueo/verificar/', VistaVerificarCodigoDesbloqueo.as_view(), name='verificar_codigo_desbloqueo'),
]