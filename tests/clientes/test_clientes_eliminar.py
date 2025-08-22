from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from clientes.models import Cliente as ModeloCliente, CategoriaCliente, ClienteUsuario

Usuario = get_user_model()

class PruebaVistaEliminarClienteUsuario(TestCase):
    """Prueba la VistaEliminarClienteUsuario que tiene el problema con success_url"""
    
    def setUp(self):
        # Crear un usuario de personal (staff)
        self.usuario_staff = Usuario.objects.create_user(
            username='staff2@test.com',
            email='staff2@test.com',
            password='testpass123',
            is_staff=True
        )
        
        # Crear un usuario regular para ser asociado
        self.usuario_regular = Usuario.objects.create_user(
            username='user2@test.com', 
            email='user2@test.com',
            password='testpass123'
        )
        
        # Crear una categoría de cliente
        self.categoria = CategoriaCliente.objects.create(
            nombre='RETAIL_TEST',
            descripcion='Clientes minoristas de prueba'
        )
        
        # Crear un cliente
        self.objeto_cliente = ModeloCliente.objects.create(
            tipo_cliente='FISICA',
            estado='ACTIVO',
            categoria=self.categoria,
            nombre='Prueba',
            apellido='Cliente',
            numero_identificacion='12345678_test',
            email='cliente2@test.com',
            creado_por=self.usuario_staff
        )
        
        # Crear una asociación cliente-usuario
        self.cliente_usuario = ClienteUsuario.objects.create(
            cliente=self.objeto_cliente,
            usuario=self.usuario_regular,
            rol='AUTORIZADO',
            asignado_por=self.usuario_staff
        )
    
    def test_carga_pagina_get_eliminar_usuario_cliente(self):
        """Prueba que la página de confirmación para eliminar usuario de cliente carga correctamente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clientes:eliminar_usuario_cliente', kwargs={
            'id_cliente': self.objeto_cliente.id,
            'id_usuario': self.usuario_regular.id
        })
        respuesta = self.client.get(url)
        
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Confirmar Desasociación')
        self.assertContains(respuesta, self.objeto_cliente.obtener_nombre_completo())
        self.assertContains(respuesta, self.usuario_regular.nombre_completo)
    
    def test_problema_success_url_post_eliminar_usuario_cliente(self):
        """Prueba que reproduce el error ImproperlyConfigured para success_url"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clientes:eliminar_usuario_cliente', kwargs={
            'id_cliente': self.objeto_cliente.id,
            'id_usuario': self.usuario_regular.id
        })
        
        # Esto debería disparar el error ImproperlyConfigured si success_url no está definida
        try:
            respuesta = self.client.post(url)
            # Si llegamos aquí sin un error, la corrección está funcionando
            # Debería redirigir a la página manage_client_users
            self.assertEqual(respuesta.status_code, 302)
            redireccion_esperada = reverse('clientes:gestionar_usuarios_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
            self.assertRedirects(respuesta, redireccion_esperada)
            
            # Verificar que la asociación cliente-usuario fue eliminada
            self.assertFalse(ClienteUsuario.objects.filter(
                cliente=self.objeto_cliente,
                usuario=self.usuario_regular
            ).exists())
            
        except Exception as e:
            if "No URL to redirect to. Provide a success_url" in str(e):
                self.fail("VistaEliminarClienteUsuario carece de success_url o del método get_success_url")
            else:
                raise