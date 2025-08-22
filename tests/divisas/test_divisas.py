from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from divisas.models import Moneda, TasaCambio

Usuario = get_user_model()


class PruebaActualizacionTasaCambio(TestCase):
    """Caso de prueba para reproducir el problema de restricción UNIQUE al actualizar tasas de cambio"""
    
    def setUp(self):
        """Configura los datos de prueba"""
        # Crear un usuario de personal (staff)
        self.usuario_staff = Usuario.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        # Marcar el email como verificado si el campo existe
        if hasattr(self.usuario_staff, 'email_verificado'):
            self.usuario_staff.email_verificado = True
            self.usuario_staff.save()
        
        # Crear moneda base
        self.moneda_base = Moneda.objects.create(
            codigo='USD',
            nombre='Dólar Estadounidense',
            simbolo='$',
            es_moneda_base=True,
            esta_activa=True
        )
        
        # Crear una moneda de prueba
        self.moneda_prueba = Moneda.objects.create(
            codigo='EUR',
            nombre='Euro',
            simbolo='€',
            esta_activa=True
        )
        
        self.cliente_test = Client()
        
    def test_problema_restriccion_actualizacion_doble_tasa(self):
        """Prueba que actualizar una tasa dos veces causa un error de restricción UNIQUE"""
        # Forzar inicio de sesión como usuario de personal (evita la autenticación)
        self.cliente_test.force_login(self.usuario_staff)
        
        # Primera actualización - debería funcionar
        respuesta1 = self.cliente_test.post(reverse('divisas:api_actualizar_tasas'), {
            'type': 'manual',
            'currency_id': self.moneda_prueba.id,
            'buy_rate': '0.85',
            'sell_rate': '0.87'
        })
        
        self.assertEqual(respuesta1.status_code, 200)
        datos1 = respuesta1.json()
        self.assertTrue(datos1['success'])
        
        # Verificar que se creó la primera tasa
        tasas = TasaCambio.objects.filter(
            moneda=self.moneda_prueba,
            moneda_base=self.moneda_base,
            esta_activa=True
        )
        self.assertEqual(tasas.count(), 1)
        
        # Segunda actualización - esto debería causar el error de restricción UNIQUE
        respuesta2 = self.cliente_test.post(reverse('divisas:api_actualizar_tasas'), {
            'type': 'manual',
            'currency_id': self.moneda_prueba.id,
            'buy_rate': '0.86',
            'sell_rate': '0.88'
        })
        
        self.assertEqual(respuesta2.status_code, 200)
        datos2 = respuesta2.json()
        
        # En la implementación rota actual, esto debería fallar
        # Después de nuestra corrección, esto debería tener éxito
        print(f"Éxito de la segunda respuesta: {datos2['success']}")
        if 'error' in datos2:
            print(f"Error de la segunda respuesta: {datos2['error']}")
        
        if not datos2['success']:
            # Este es el error esperado con el código actual
            self.assertIn('UNIQUE constraint failed', datos2['error'])
            print("PRUEBA CONFIRMADA: Ocurrió el error de restricción UNIQUE como se esperaba")
        else:
            # Después de nuestra corrección, esto debería funcionar
            # Verificar que solo existe una tasa activa con los valores actualizados
            tasas = TasaCambio.objects.filter(
                moneda=self.moneda_prueba,
                moneda_base=self.moneda_base,
                esta_activa=True
            )
            print(f"Tasas activas después de la segunda actualización: {tasas.count()}")
            self.assertEqual(tasas.count(), 1)
            tasa_activa = tasas.first()
            print(f"Tasa final de compra: {tasa_activa.tasa_compra}, tasa de venta: {tasa_activa.tasa_venta}")
            self.assertEqual(tasa_activa.tasa_compra, Decimal('0.86'))
            self.assertEqual(tasa_activa.tasa_venta, Decimal('0.88'))

    def test_problema_restriccion_actualizacion_triple_tasa(self):
        """Prueba que actualizar una tasa múltiples veces para provocar el error de restricción"""
        # Forzar inicio de sesión como usuario de personal
        self.cliente_test.force_login(self.usuario_staff)
        
        # Primera actualización
        respuesta1 = self.cliente_test.post(reverse('divisas:api_actualizar_tasas'), {
            'type': 'manual',
            'currency_id': self.moneda_prueba.id,
            'buy_rate': '0.85',
            'sell_rate': '0.87'
        })
        
        self.assertEqual(respuesta1.status_code, 200)
        datos1 = respuesta1.json()
        self.assertTrue(datos1['success'])
        print(f"Primera actualización: Éxito = {datos1['success']}")
        
        # Segunda actualización (aquí es donde el usuario experimentó el problema)
        respuesta2 = self.cliente_test.post(reverse('divisas:api_actualizar_tasas'), {
            'type': 'manual',
            'currency_id': self.moneda_prueba.id,
            'buy_rate': '0.86',
            'sell_rate': '0.88'
        })
        
        self.assertEqual(respuesta2.status_code, 200)
        datos2 = respuesta2.json()
        print(f"Segunda actualización: Éxito = {datos2['success']}")
        if 'error' in datos2:
            print(f"Error de la segunda actualización: {datos2['error']}")
        
        # Tercera actualización para intentar provocar el problema
        respuesta3 = self.cliente_test.post(reverse('divisas:api_actualizar_tasas'), {
            'type': 'manual',
            'currency_id': self.moneda_prueba.id,
            'buy_rate': '0.87',
            'sell_rate': '0.89'
        })
        
        self.assertEqual(respuesta3.status_code, 200)
        datos3 = respuesta3.json()
        print(f"Tercera actualización: Éxito = {datos3['success']}")
        if 'error' in datos3:
            print(f"Error de la tercera actualización: {datos3['error']}")
        
        # Comprobar cuántas tasas totales existen (activas e inactivas)
        todas_las_tasas = TasaCambio.objects.filter(
            moneda=self.moneda_prueba,
            moneda_base=self.moneda_base
        )
        tasas_activas = todas_las_tasas.filter(esta_activa=True)
        print(f"Total de tasas creadas: {todas_las_tasas.count()}")
        print(f"Tasas activas: {tasas_activas.count()}")
        
        # El estado final debería ser: solo 1 tasa activa con los últimos valores
        self.assertEqual(tasas_activas.count(), 1)
        if tasas_activas.exists():
            tasa_final = tasas_activas.first()
            print(f"Tasa final: compra={tasa_final.tasa_compra}, venta={tasa_final.tasa_venta}")
        
        # Todas las respuestas deberían ser exitosas después de nuestra corrección
        self.assertTrue(datos1['success'])
        self.assertTrue(datos2['success'])  
        self.assertTrue(datos3['success'])