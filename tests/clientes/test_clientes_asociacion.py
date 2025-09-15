from django.test import TestCase
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.urls import reverse
from django.contrib.auth.models import Permission
from clientes.models import Cliente as ModeloCliente, CategoriaCliente, ClienteUsuario

Usuario = get_user_model()


class PruebaIntegracionAsociacionClienteUsuario(TestCase):
    """Prueba de integración para la funcionalidad de asociación de usuario-cliente"""
    
    def setUp(self):
        # Crear un usuario de personal (staff)
        self.usuario_staff = Usuario.objects.create_user(
            username='staff@test.com',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )
        
        # Crear un usuario regular para ser asociado
        self.usuario_regular = Usuario.objects.create_user(
            username='user@test.com', 
            email='user@test.com',
            password='testpass123'
        )
        
        # Crear una categoría de cliente
        self.categoria = CategoriaCliente.objects.create(
            nombre='RETAIL',
            descripcion='Clientes minoristas'
        )
        
        # Crear un cliente
        self.objeto_cliente = ModeloCliente.objects.create(
            tipo_cliente='FISICA',
            estado='ACTIVO',
            categoria=self.categoria,
            nombre='Prueba',
            apellido='Cliente',
            numero_identificacion='12345678',
            email='cliente@test.com',
            creado_por=self.usuario_staff
        )
    
    def test_carga_pagina_gestionar_usuarios_cliente(self):
        """Prueba que la página de gestionar usuarios del cliente carga correctamente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clientes:gestionar_usuarios_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        respuesta = self.client.get(url)
        
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Asociar Usuarios')
        self.assertContains(respuesta, self.objeto_cliente.obtener_nombre_completo())
    
    def test_carga_pagina_anadir_usuario_cliente(self):
        """Prueba que la página de añadir usuario a cliente carga correctamente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clientes:anadir_usuario_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        respuesta = self.client.get(url)
        
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Asociar Usuario')
        self.assertContains(respuesta, self.objeto_cliente.obtener_nombre_completo())
        # Comprobar que el token CSRF está presente en el formulario
        self.assertContains(respuesta, 'name="csrfmiddlewaretoken"')
        self.assertContains(respuesta, 'type="hidden"')
    
    def test_token_csrf_en_respuesta_gestionar_usuarios_cliente(self):
        """Prueba que el token CSRF está disponible en la página de gestionar usuarios del cliente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clientes:gestionar_usuarios_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        respuesta = self.client.get(url)
        
        self.assertEqual(respuesta.status_code, 200)
        
        # Comprobar que el meta tag está presente (de la plantilla base)
        self.assertContains(respuesta, 'name="csrf-token"')
        
    def test_resolucion_correcta_urls(self):
        """Prueba que las URLs mencionadas en el escenario de error se resuelven correctamente"""
        # Probar la URL de gestionar usuarios (donde se originó el error)
        url_gestion = reverse('clientes:gestionar_usuarios_cliente', kwargs={'id_cliente': 1})
        self.assertEqual(url_gestion, '/clientes/1/usuarios/')
        
        # Probar la URL de añadir usuario (donde ocurrió el error)
        url_anadir = reverse('clientes:anadir_usuario_cliente', kwargs={'id_cliente': 1})
        self.assertEqual(url_anadir, '/clientes/1/usuarios/anadir/')
        
        # Esto coincide exactamente con las URLs del mensaje de error
        
        # Probar la URL de eliminar usuario (donde ocurrió el error)
        url_eliminar = reverse('clientes:eliminar_usuario_cliente', kwargs={'id_cliente': 1, 'id_usuario': 1})
        self.assertEqual(url_eliminar, '/clientes/1/usuarios/1/eliminar/')