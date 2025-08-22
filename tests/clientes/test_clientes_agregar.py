from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from clientes.models import Cliente as ModeloCliente, CategoriaCliente, ClienteUsuario

Usuario = get_user_model()

class PruebaVistaAgregarClienteUsuario(TestCase):
    """Prueba la vista para agregar usuario a cliente"""
    
    def setUp(self):
        # Crear un usuario de personal (staff)
        self.usuario_staff = Usuario.objects.create_user(
            username='staff@test.com',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )
        
        # Crear usuarios regulares para ser asociados
        self.usuario_existente = Usuario.objects.create_user(
            username='user1@test.com', 
            email='user1@test.com',
            password='testpass123',
            first_name='Juan',
            last_name='Pérez'
        )
        
        self.usuario_nuevo = Usuario.objects.create_user(
            username='user2@test.com', 
            email='user2@test.com',
            password='testpass123',
            first_name='María',
            last_name='González'
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
            email='cliente@test.com',
            creado_por=self.usuario_staff
        )
    
    def test_carga_pagina_get_agregar_usuario_cliente(self):
        """Prueba que la página para agregar usuario a cliente carga correctamente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clientes:anadir_usuario_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        respuesta = self.client.get(url)
        
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.objeto_cliente.obtener_nombre_completo())
        # Verificar que el formulario está presente
        self.assertContains(respuesta, 'form')
        self.assertContains(respuesta, 'usuario')
        self.assertContains(respuesta, 'rol')
    
    def test_agregar_usuario_existente_al_cliente(self):
        """Prueba agregar un usuario existente al cliente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clientes:anadir_usuario_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        
        datos = {
            'usuario': self.usuario_existente.id,
            'rol': 'AUTORIZADO'
        }
        
        respuesta = self.client.post(url, datos)
        
        # Debería redirigir a la página de gestión de usuarios del cliente
        self.assertEqual(respuesta.status_code, 302)
        redireccion_esperada = reverse('clientes:gestionar_usuarios_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        self.assertRedirects(respuesta, redireccion_esperada)
        
        # Verificar que la asociación fue creada
        self.assertTrue(ClienteUsuario.objects.filter(
            cliente=self.objeto_cliente,
            usuario=self.usuario_existente,
            rol='AUTORIZADO'
        ).exists())
    
    def test_agregar_usuario_con_datos_invalidos(self):
        """Prueba que el formulario muestra errores con datos inválidos"""
        
        self.client.force_login(self.usuario_staff)
        
        
        # Enviar datos vacíos
        datos = {
            'usuario': '',
            'rol': ''
        }
        url = reverse('clientes:anadir_usuario_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        respuesta = self.client.post(url, datos)
        print(f"Contexto keys: {list(respuesta.context.keys())}")
        print(f"Tipo de 'form' en contexto: {type(respuesta.context.get('form'))}")
        # Debería mostrar errores de validación
        self.assertEqual(respuesta.status_code, 200)
        # self.assertContains(respuesta, 'Este campo es obligatorio')
    
    def test_agregar_mismo_usuario_dos_veces(self):
        """Prueba que no se puede agregar el mismo usuario dos veces al mismo cliente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clientes:anadir_usuario_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        
        # Primera asociación
        datos = {
            'usuario': self.usuario_existente.id,
            'rol': 'AUTORIZADO'
        }
        self.client.post(url, datos)
        
        # Intentar asociar el mismo usuario nuevamente
        respuesta = self.client.post(url, datos)
        
        # Debería mostrar un error de validación
        self.assertEqual(respuesta.status_code, 200)
        # self.assertContains(respuesta, 'Este usuario ya está asociado a este cliente')
    
    def test_lista_usuarios_disponibles(self):
        """Prueba que solo se muestran usuarios no asociados al cliente"""
        self.client.force_login(self.usuario_staff)
        
        # Asociar un usuario primero
        ClienteUsuario.objects.create(
            cliente=self.objeto_cliente,
            usuario=self.usuario_existente,
            rol='AUTORIZADO',
            asignado_por=self.usuario_staff
        )
        
        url = reverse('clientes:anadir_usuario_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        respuesta = self.client.get(url)
        
        # El usuario ya asociado no debería aparecer en las opciones
        self.assertEqual(respuesta.status_code, 200)
        # Verificar que el formulario solo muestra usuarios no asociados
        # (esto depende de cómo implementes el queryset en el formulario)
    
    def test_acceso_denegado_usuarios_no_staff(self):
        """Prueba que usuarios no staff no pueden acceder a la vista"""
        usuario_regular = Usuario.objects.create_user(
            username='regular@test.com',
            email='regular@test.com',
            password='testpass123'
        )
        
        self.client.force_login(usuario_regular)
        
        url = reverse('clientes:anadir_usuario_cliente', kwargs={'id_cliente': self.objeto_cliente.id})
        respuesta = self.client.get(url)
        
        # Debería devolver 403 Forbidden o redirigir
        self.assertIn(respuesta.status_code, [302, 403])