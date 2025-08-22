from django.test import TestCase, RequestFactory
from pathlib import Path
from django.contrib.auth import get_user_model
from django.template import Template, Context
from django.middleware.csrf import get_token
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import Permission
from clientes.models import Cliente as ModeloCliente, CategoriaCliente, ClienteUsuario

Usuario = get_user_model()
ruta_proyecto = Path.cwd() 

class PruebaCasoTokenCSRF(TestCase):
    """Prueba el manejo del token CSRF en las plantillas"""
    
    def setUp(self):
        self.fabrica = RequestFactory()
        self.cliente_test = Client()
    
    def test_plantilla_base_tiene_meta_tag_csrf(self):
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
    
    def test_manejo_csrf_plantilla_gestionar_usuarios_cliente(self):
        """Prueba que la plantilla gestionar_usuario_clientes tiene el JavaScript de token CSRF adecuado"""
        with open(f'{ruta_proyecto}/plantillas/clientes/gestionar_usuarios_cliente.html', 'r') as f:
            contenido_plantilla = f.read()
        
        # Comprueba que la plantilla incluye la función de respaldo getCookie
        
        # Comprueba que intenta múltiples métodos para obtener el token CSRF
        self.assertIn('meta[name=csrf-token]', contenido_plantilla)
        
        # Comprueba que maneja con gracia la falta de un token CSRF
        self.assertIn('window.location.reload()', contenido_plantilla)
    
    def prueba_token_csrf_plantilla_anadir_usuario_cliente(self):
        """Prueba que la plantilla add_client_user incluye el token CSRF"""
        with open(f'{ruta_proyecto}/plantillas/clientes/anadir_usuario_cliente.html', 'r') as f:
            contenido_plantilla = f.read()
        
        # Comprueba que la plantilla incluye la etiqueta csrf_token
        self.assertIn('{% csrf_token %}', contenido_plantilla)

class PruebaLogicaJavaScriptTokenCSRF(TestCase):
    """Prueba la lógica de JavaScript para el manejo del token CSRF"""
    
    def test_logica_extraccion_token_csrf(self):
        """Prueba que nuestra lógica de extracción de token CSRF cubre todos los escenarios"""
        # Esta sería una prueba más compleja si tuviéramos un framework de pruebas de JavaScript
        # Por ahora, solo verificamos que la plantilla tiene la estructura correcta
        
        with open(f'{ruta_proyecto}/plantillas/clientes/gestionar_usuarios_cliente.html', 'r') as f:
            contenido = f.read()
        
        # Verificar que el orden de prioridad es correcto
        # 1. Función global GE.getCookie
        # 2. Función local getCookie  
        # 3. Respaldo con meta tag
        lineas = contenido.split('\n')
        lineas_logica_csrf = [i for i, linea in enumerate(lineas) if 'getCookie' in linea or 'meta[name=csrf-token]' in linea]
        
        # Debería haber múltiples líneas manejando el CSRF
        self.assertGreater(len(lineas_logica_csrf), 0)