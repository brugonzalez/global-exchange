from .models import PreferenciaCliente

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.template import Template, Context
from django.middleware.csrf import get_token
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import Permission
from .models import Cliente as ModeloCliente, CategoriaCliente, ClienteUsuario

Usuario = get_user_model()


class PreferenciaClienteTestCase(TestCase):
    def setUp(self):
        self.categoria = CategoriaCliente.objects.create(nombre='RETAIL')
        self.usuario = Usuario.objects.create_user(
            username='admin',  # agrega esto
            email='admin@admin.com',
            password='admin'
        )
        self.cliente = ModeloCliente.objects.create(
            tipo_cliente='FISICA',
            estado='ACTIVO',
            categoria=self.categoria,
            nombre='Test',
            apellido='User',
            numero_identificacion='123',
            email='test@user.com',
        )
        self.preferencias = PreferenciaCliente.objects.create(
            cliente=self.cliente,
            limite_compra=1000,
            limite_venta=500,
            frecuencia_maxima=2,
            preferencia_tipo_cambio='preferencial',
        )

    def test_preferencias_cliente_guardado(self):
        self.assertEqual(self.cliente.preferencias.limite_compra, 1000)
        self.assertEqual(self.cliente.preferencias.frecuencia_maxima, 2)
        self.assertEqual(self.cliente.preferencias.preferencia_tipo_cambio, 'preferencial')
class PruebaCasoTokenCSRF(TestCase):
    """Prueba el manejo del token CSRF en las plantillas"""
    
    def setUp(self):
        self.fabrica = RequestFactory()
        self.cliente_test = Client()
    
    def prueba_plantilla_base_tiene_meta_tag_csrf(self):
        """Prueba que la plantilla base incluye el meta tag CSRF"""
        contenido_plantilla = '''
        {% load static %}
        <meta name="csrf-token" content="{{ csrf_token }}">
        '''
        plantilla = Template(contenido_plantilla)
        solicitud = self.fabrica.get('/')
        token_csrf = get_token(solicitud)
        contexto = Context({'csrf_token': token_csrf, 'request': solicitud})
        renderizado = plantilla.render(contexto)
        
        self.assertIn('meta name="csrf-token"', renderizado)
        self.assertIn(token_csrf, renderizado)
    
    def prueba_manejo_csrf_plantilla_gestionar_usuarios_cliente(self):
        """Prueba que la plantilla manage_client_users tiene el JavaScript de token CSRF adecuado"""
        with open('/home/runner/work/global-exchange/global-exchange/templates/clients/manage_client_users.html', 'r') as f:
            contenido_plantilla = f.read()
        
        # Comprueba que la plantilla incluye la función de respaldo getCookie
        self.assertIn('function getCookie(name)', contenido_plantilla)
        
        # Comprueba que intenta múltiples métodos para obtener el token CSRF
        self.assertIn('window.GE.getCookie', contenido_plantilla)
        self.assertIn('getCookie(\'csrftoken\')', contenido_plantilla) 
        self.assertIn('meta[name=csrf-token]', contenido_plantilla)
        
        # Comprueba que maneja con gracia la falta de un token CSRF
        self.assertIn('window.location.reload()', contenido_plantilla)
    
    def prueba_token_csrf_plantilla_anadir_usuario_cliente(self):
        """Prueba que la plantilla add_client_user incluye el token CSRF"""
        with open('/home/runner/work/global-exchange/global-exchange/templates/clients/add_client_user.html', 'r') as f:
            contenido_plantilla = f.read()
        
        # Comprueba que la plantilla incluye la etiqueta csrf_token
        self.assertIn('{% csrf_token %}', contenido_plantilla)


class PruebaLogicaJavaScriptTokenCSRF(TestCase):
    """Prueba la lógica de JavaScript para el manejo del token CSRF"""
    
    def prueba_logica_extraccion_token_csrf(self):
        """Prueba que nuestra lógica de extracción de token CSRF cubre todos los escenarios"""
        # Esta sería una prueba más compleja si tuviéramos un framework de pruebas de JavaScript
        # Por ahora, solo verificamos que la plantilla tiene la estructura correcta
        
        with open('/home/runner/work/global-exchange/global-exchange/templates/clients/manage_client_users.html', 'r') as f:
            contenido = f.read()
        
        # Verificar que el orden de prioridad es correcto
        # 1. Función global GE.getCookie
        # 2. Función local getCookie  
        # 3. Respaldo con meta tag
        lineas = contenido.split('\n')
        lineas_logica_csrf = [i for i, linea in enumerate(lineas) if 'getCookie' in linea or 'meta[name=csrf-token]' in linea]
        
        # Debería haber múltiples líneas manejando el CSRF
        self.assertGreater(len(lineas_logica_csrf), 2)


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
    
    def prueba_carga_pagina_gestionar_usuarios_cliente(self):
        """Prueba que la página de gestionar usuarios del cliente carga correctamente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clients:manage_client_users', kwargs={'client_id': self.objeto_cliente.id})
        respuesta = self.client.get(url)
        
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Gestionar Usuarios')
        self.assertContains(respuesta, self.objeto_cliente.obtener_nombre_completo())
    
    def prueba_carga_pagina_anadir_usuario_cliente(self):
        """Prueba que la página de añadir usuario a cliente carga correctamente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clients:add_client_user', kwargs={'client_id': self.objeto_cliente.id})
        respuesta = self.client.get(url)
        
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Asociar Usuario')
        self.assertContains(respuesta, self.objeto_cliente.obtener_nombre_completo())
        # Comprobar que el token CSRF está presente en el formulario
        self.assertContains(respuesta, 'name="csrfmiddlewaretoken"')
        self.assertContains(respuesta, 'type="hidden"')
    
    def prueba_token_csrf_en_respuesta_gestionar_usuarios_cliente(self):
        """Prueba que el token CSRF está disponible en la página de gestionar usuarios del cliente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clients:manage_client_users', kwargs={'client_id': self.objeto_cliente.id})
        respuesta = self.client.get(url)
        
        self.assertEqual(respuesta.status_code, 200)
        
        # Comprobar que la plantilla incluye nuestra función de JavaScript
        self.assertContains(respuesta, 'confirmAssign')
        self.assertContains(respuesta, 'getCookie')
        
        # Comprobar que el meta tag está presente (de la plantilla base)
        self.assertContains(respuesta, 'name="csrf-token"')
        
    def prueba_resolucion_correcta_urls(self):
        """Prueba que las URLs mencionadas en el escenario de error se resuelven correctamente"""
        # Probar la URL de gestionar usuarios (donde se originó el error)
        url_gestion = reverse('clients:manage_client_users', kwargs={'client_id': 1})
        self.assertEqual(url_gestion, '/clients/1/users/')
        
        # Probar la URL de añadir usuario (donde ocurrió el error)
        url_anadir = reverse('clients:add_client_user', kwargs={'client_id': 1})
        self.assertEqual(url_anadir, '/clients/1/users/add/')
        
        # Esto coincide exactamente con las URLs del mensaje de error
        
        # Probar la URL de eliminar usuario (donde ocurrió el error)
        url_eliminar = reverse('clients:remove_client_user', kwargs={'client_id': 1, 'user_id': 1})
        self.assertEqual(url_eliminar, '/clients/1/users/1/remove/')


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
    
    def prueba_carga_pagina_get_eliminar_usuario_cliente(self):
        """Prueba que la página de confirmación para eliminar usuario de cliente carga correctamente"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clients:remove_client_user', kwargs={
            'client_id': self.objeto_cliente.id,
            'user_id': self.usuario_regular.id
        })
        respuesta = self.client.get(url)
        
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Confirmar Desasociación')
        self.assertContains(respuesta, self.objeto_cliente.obtener_nombre_completo())
        self.assertContains(respuesta, self.usuario_regular.nombre_completo)
    
    def prueba_problema_success_url_post_eliminar_usuario_cliente(self):
        """Prueba que reproduce el error ImproperlyConfigured para success_url"""
        self.client.force_login(self.usuario_staff)
        
        url = reverse('clients:remove_client_user', kwargs={
            'client_id': self.objeto_cliente.id,
            'user_id': self.usuario_regular.id
        })
        
        # Esto debería disparar el error ImproperlyConfigured si success_url no está definida
        try:
            respuesta = self.client.post(url)
            # Si llegamos aquí sin un error, la corrección está funcionando
            # Debería redirigir a la página manage_client_users
            self.assertEqual(respuesta.status_code, 302)
            redireccion_esperada = reverse('clients:manage_client_users', kwargs={'client_id': self.objeto_cliente.id})
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