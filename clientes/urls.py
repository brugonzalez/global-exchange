from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    # Gestión de clientes
    path('', views.VistaListaClientes.as_view(), name='lista_clientes'),
    path('crear/', views.VistaCrearCliente.as_view(), name='crear_cliente'),
    path('<int:id_cliente>/', views.VistaDetalleCliente.as_view(), name='detalle_cliente'),
    path('<int:id_cliente>/editar/', views.VistaEditarCliente.as_view(), name='editar_cliente'),
    
    # Asociaciones usuario-cliente
    path('<int:id_cliente>/usuarios/', views.VistaGestionarUsuariosCliente.as_view(), name='gestionar_usuarios_cliente'),
    path('<int:id_cliente>/usuarios/anadir/', views.VistaAnadirUsuarioCliente.as_view(), name='anadir_usuario_cliente'),
    path('<int:id_cliente>/usuarios/<int:id_usuario>/eliminar/', views.VistaEliminarUsuarioCliente.as_view(), name='eliminar_usuario_cliente'),
    path('<int:id_cliente>/usuarios/<int:id_usuario>/detalles/', views.VistaDetallesUsuario.as_view(), name='detalles_usuario'),
    
    # Monedas favoritas
    path('<int:id_cliente>/favoritos/', views.VistaGestionarFavoritos.as_view(), name='gestionar_favoritos'),
    path('<int:id_cliente>/favoritos/anadir/', views.VistaAnadirFavorito.as_view(), name='anadir_favorito'),
    path('<int:id_cliente>/favoritos/<int:id_favorito>/eliminar/', views.VistaEliminarFavorito.as_view(), name='eliminar_favorito'),
    
    # Saldos de cliente
    path('<int:id_cliente>/saldos/', views.VistaSaldosCliente.as_view(), name='saldos_cliente'),
]