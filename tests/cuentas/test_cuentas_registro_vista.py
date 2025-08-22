from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from cuentas.models import Rol, Usuario

Usuario = get_user_model()

class TestRegistroVista(TestCase):
    """
    Pruebas para verificar que el registro a través de la vista web funciona correctamente.
    """
    
    def setUp(self):
        """Configurar datos de prueba."""
        # Crear el rol 'Usuario' si no existe
        self.rol_usuario, _ = Rol.objects.get_or_create(
            nombre_rol='Usuario',
            defaults={
                'descripcion': 'Usuario regular del sistema',
                'es_sistema': True
            }
        )
        
        self.client = Client()
    
    def test_registro_via_formulario_web_asigna_rol_usuario(self):
        """Verificar que el registro a través del formulario web asigna el rol 'Usuario'."""
        datos_registro = {
            'username': 'usuario_web',
            'email': 'web@example.com',
            'full_name': 'Usuario Web Test',
            'password1': 'contraseña_segura_123',
            'password2': 'contraseña_segura_123',
            'terms_accepted': True
        }
        
        # Verificar que el usuario no existe antes del registro
        self.assertFalse(Usuario.objects.filter(username='usuario_web').exists())
        
        # Realizar registro mediante POST al formulario
        response = self.client.post(reverse('cuentas:registro'), datos_registro)
        
        # Verificar que el usuario fue creado
        self.assertTrue(Usuario.objects.filter(username='usuario_web').exists())
        
        # Obtener el usuario creado
        usuario = Usuario.objects.get(username='usuario_web')
        
        # Verificar que tiene el rol 'Usuario'
        self.assertTrue(usuario.tiene_rol('Usuario'))
        self.assertIn(self.rol_usuario, usuario.roles.all())
        self.assertEqual(usuario.roles.count(), 1)
    
    def test_registro_via_formulario_django_asigna_rol_usuario(self):
        """Verificar que el registro a través del FormularioRegistro asigna el rol 'Usuario'."""
        from cuentas.forms import FormularioRegistro
        
        datos_formulario = {
            'username': 'test_form_user',
            'email': 'form@example.com',
            'full_name': 'Test Form User',
            'password1': 'password_segura_123',
            'password2': 'password_segura_123',
            'terms_accepted': True
        }
        
        # Crear y validar formulario
        formulario = FormularioRegistro(data=datos_formulario)
        self.assertTrue(formulario.is_valid(), f"Formulario no válido: {formulario.errors}")
        
        # Guardar usuario a través del formulario
        usuario = formulario.save()
        
        # Verificar que el usuario tiene el rol 'Usuario'
        self.assertTrue(usuario.tiene_rol('Usuario'))
        self.assertIn(self.rol_usuario, usuario.roles.all())