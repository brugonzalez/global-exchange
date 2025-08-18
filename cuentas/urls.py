from django.urls import path
from . import views

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
]