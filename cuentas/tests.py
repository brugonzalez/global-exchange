from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Rol, Usuario


class TestAsignacionRolUsuario(TestCase):
    """
    Pruebas para verificar que los nuevos usuarios reciben automáticamente el rol 'Usuario'.
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
    
    def test_nuevo_usuario_recibe_rol_usuario_automaticamente(self):
        """Verificar que un nuevo usuario recibe automáticamente el rol 'Usuario'."""
        # Crear un nuevo usuario
        usuario = Usuario.objects.create_user(
            username='test_usuario',
            email='test@example.com',
            nombre_completo='Usuario de Prueba',
            password='password123'
        )
        
        # Verificar que el usuario tiene el rol 'Usuario'
        self.assertTrue(usuario.tiene_rol('Usuario'))
        self.assertIn(self.rol_usuario, usuario.roles.all())
    
    def test_usuario_creado_via_create_user_recibe_rol(self):
        """Verificar que usuarios creados con create_user también reciben el rol."""
        usuario = Usuario.objects.create_user(
            username='otro_usuario',
            email='otro@example.com',
            password='pass123'
        )
        
        self.assertTrue(usuario.tiene_rol('Usuario'))
    
    def test_signal_no_falla_si_rol_usuario_no_existe(self):
        """Verificar que el signal no causa errores si el rol 'Usuario' no existe."""
        # Eliminar el rol 'Usuario' temporalmente
        Rol.objects.filter(nombre_rol='Usuario').delete()
        
        # Crear un usuario (no debería causar errores)
        usuario = Usuario.objects.create_user(
            username='sin_rol',
            email='sinrol@example.com',
            password='pass123'
        )
        
        # El usuario debería existir pero sin roles
        self.assertEqual(usuario.roles.count(), 0)
    
    def test_usuario_existente_no_se_modifica(self):
        """Verificar que usuarios existentes no se ven afectados por el signal."""
        # Crear usuario sin el signal (simulando usuario existente)
        usuario = Usuario(
            username='existente',
            email='existente@example.com',
            nombre_completo='Usuario Existente'
        )
        usuario.set_password('pass123')
        usuario.save()
        
        # Limpiar roles manualmente para simular usuario sin roles
        usuario.roles.clear()
        
        # Verificar que no tiene roles
        self.assertEqual(usuario.roles.count(), 0)
        
        # Actualizar el usuario (esto no debería activar el signal con created=True)
        usuario.nombre_completo = 'Nombre Actualizado'
        usuario.save()
        
        # Verificar que sigue sin roles
        self.assertEqual(usuario.roles.count(), 0)


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
        from .forms import FormularioRegistro
        
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