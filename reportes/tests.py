from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
from .models import Reporte

Usuario = get_user_model()


class PruebaDescargaReporte(TestCase):
    """Prueba para la funcionalidad de descarga de reportes - corrigiendo el error 404"""
    
    def setUp(self):
        """Configura los datos de prueba"""
        self.cliente_test = Client()
        self.usuario = Usuario.objects.create_user(
            username='usuarioprueba',
            email='prueba@ejemplo.com',
            password='contraseñasegura123',
            nombre_completo='Usuario de Prueba',
            email_verificado=True
        )
        
        # Crear un archivo de reporte de prueba usando el manejo de archivos de Django
        self.contenido_archivo_prueba = b'Contenido del reporte de prueba'
        self.archivo_prueba = SimpleUploadedFile(
            "reporte_prueba.pdf", 
            self.contenido_archivo_prueba, 
            content_type="application/pdf"
        )
        
        # Crear un reporte para las pruebas
        self.reporte = Reporte.objects.create(
            nombre_reporte='Reporte de Prueba',
            tipo_reporte='HISTORIAL_TRANSACCIONES',
            formato='PDF',
            estado='COMPLETADO',
            solicitado_por=self.usuario,
            fecha_desde=timezone.now() - timedelta(days=30),
            fecha_hasta=timezone.now(),
            ruta_archivo=self.archivo_prueba,
            tamano_archivo=len(self.contenido_archivo_prueba)
        )

    
    def test_descargar_reporte_con_parametro_url_correcto(self):
        """Prueba que la descarga de reportes funciona con el parámetro de URL correcto (id_reporte)"""
        # Iniciar sesión del usuario
        self.cliente_test.login(username='prueba@ejemplo.com', password='contraseñasegura123')
        
        # Acceder a la URL de descarga que antes fallaba
        url = reverse('reportes:descargar_reporte', kwargs={'id_reporte': self.reporte.id})
        respuesta = self.cliente_test.get(url)
        
        # Ahora debería funcionar en lugar de devolver 404
        self.assertEqual(respuesta.status_code, 200, "La descarga debería funcionar con el parámetro id_reporte")
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertIn('attachment', respuesta['Content-Disposition'])
        self.assertIn('Reporte de Prueba.pdf', respuesta['Content-Disposition'])
        
    def test_descargar_reporte_inexistente_devuelve_404(self):
        """Prueba que descargar un reporte inexistente devuelve 404"""
        # Iniciar sesión del usuario
        self.cliente_test.login(username='prueba@ejemplo.com', password='contraseñasegura123')
        
        # Intentar descargar un reporte inexistente
        url = reverse('reportes:descargar_reporte', kwargs={'id_reporte': 99999})
        respuesta = self.cliente_test.get(url)
        
        # Debería devolver 404
        self.assertEqual(respuesta.status_code, 404)
        
    def test_descargar_reporte_de_otro_usuario_devuelve_404(self):
        """Prueba que descargar el reporte de otro usuario devuelve 404"""
        # Crear otro usuario y su reporte
        otro_usuario = Usuario.objects.create_user(
            username='otrousuario',
            email='otro@ejemplo.com',
            password='contraseñasegura123',
            nombre_completo='Otro Usuario',
            email_verificado=True
        )
        
        otro_archivo = SimpleUploadedFile(
            "otro_reporte.pdf", 
            b'Contenido de otro usuario', 
            content_type="application/pdf"
        )
        
        otro_reporte = Reporte.objects.create(
            nombre_reporte='Reporte de Otro Usuario',
            tipo_reporte='HISTORIAL_TRANSACCIONES',
            formato='PDF',
            estado='COMPLETADO',
            solicitado_por=otro_usuario,
            fecha_desde=timezone.now() - timedelta(days=30),
            fecha_hasta=timezone.now(),
            ruta_archivo=otro_archivo,
            tamano_archivo=len(b'Contenido de otro usuario')
        )
        
        # Iniciar sesión como el primer usuario
        self.cliente_test.login(username='prueba@ejemplo.com', password='contraseñasegura123')
        
        # Intentar descargar el reporte del otro usuario
        url = reverse('reportes:descargar_reporte', kwargs={'id_reporte': otro_reporte.id})
        respuesta = self.cliente_test.get(url)
        
        # Debería devolver 404 (permiso denegado)
        self.assertEqual(respuesta.status_code, 404)
        
    def test_descarga_requiere_autenticacion(self):
        """Prueba que la descarga requiere autenticación del usuario"""
        # No iniciar sesión - acceder como usuario anónimo
        url = reverse('reportes:descargar_reporte', kwargs={'id_reporte': self.reporte.id})
        respuesta = self.cliente_test.get(url)
        
        # Debería redirigir al login
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/cuentas/iniciar-sesion/', respuesta.url)
        
    def test_descarga_incrementa_contador(self):
        """Prueba que la descarga incrementa el contador de descargas"""
        # Iniciar sesión del usuario
        self.cliente_test.login(username='prueba@ejemplo.com', password='contraseñasegura123')
        
        # Comprobar el conteo inicial de descargas
        conteo_inicial = self.reporte.conteo_descargas
        
        # Descargar el reporte
        url = reverse('reportes:descargar_reporte', kwargs={'id_reporte': self.reporte.id})
        respuesta = self.cliente_test.get(url)
        
        # Verificar que la descarga funcionó
        self.assertEqual(respuesta.status_code, 200)
        
        # Refrescar el reporte desde la base de datos y comprobar el contador
        self.reporte.refresh_from_db()
        self.assertEqual(self.reporte.conteo_descargas, conteo_inicial + 1)