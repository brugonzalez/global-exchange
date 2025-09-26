# tests.py
from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import uuid

# Importaciones de sus modelos (asumiendo que están disponibles)
# Si sus modelos usan nombres de campo específicos, asegúrese de que coincidan.
from transacciones.models import Transaccion # Se asume que tiene TransaccionManager y el modelo
from divisas.models import Moneda
from clientes.models import Cliente
from divisas.models import MetodoPago
from divisas.models import MetodoCobro
from divisas.models import TasaCambio
from clientes.models import CategoriaCliente
from django.core.exceptions import ValidationError # Para el Test 7

User = get_user_model()


class TransaccionModelTests(TestCase):
    def setUp(self):
        """Configuración inicial para todas las pruebas"""
        # Crear usuario
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear categoría de cliente
        self.categoria = CategoriaCliente.objects.create(
            nombre='Test Category',
            descripcion='Categoría de prueba'
        )
        
        # Crear cliente
        # NOTA: En Django, se debe asegurar que el usuario tenga un cliente activo
        # si las vistas dependen de ello.
        self.cliente = Cliente.objects.create(
            nombre='Test',
            apellido='Cliente',
            email='cliente@test.com',
            categoria=self.categoria
        )
        
        # Crear monedas
        self.moneda_pyg = Moneda.objects.create(
            codigo='PYG',
            nombre='Guaraní Paraguayo',
            simbolo='₲',
            esta_activa=True,
            es_moneda_base=True
        )
        
        self.moneda_usd = Moneda.objects.create(
            codigo='USD',
            nombre='Dólar Americano',
            simbolo='$',
            esta_activa=True
        )
        
        # Crear métodos de pago y cobro
        self.metodo_pago = MetodoPago.objects.create(
            nombre='Transferencia Bancaria',
            esta_activo=True
        )
        
        self.metodo_cobro = MetodoCobro.objects.create(
            nombre='Efectivo',
            esta_activo=True
        )
        
        # FIX 1: TasaCambio. Se corrige pasando los IDs (campo_id) en lugar de las instancias
        # ya que el error sugiere que el constructor del modelo no reconoce los nombres de campo de ForeignKeys.
        self.tasa_cambio = TasaCambio.objects.create(
            moneda_origen_id=self.moneda_usd.pk,
            moneda_destino_id=self.moneda_pyg.pk,
            tasa_compra=Decimal('7500.00'),
            tasa_venta=Decimal('7450.00'),
            esta_activa=True,
            categoria_cliente=self.categoria # Este campo FK a CategoriaCliente suele funcionar directamente
        )

    def test_creacion_transaccion_compra(self):
        """Test 1: Crear una transacción de compra exitosamente"""
        # FIX 2: Se añade fecha_creacion=timezone.now() para evitar NoneType en la lógica de expiración
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        self.assertEqual(transaccion.tipo_transaccion, 'COMPRA')
        self.assertEqual(transaccion.estado, 'PENDIENTE')
        self.assertIsNotNone(transaccion.numero_transaccion)
        self.assertTrue(transaccion.numero_transaccion.startswith(timezone.now().strftime('%Y%m%d')))

    def test_creacion_transaccion_venta(self):
        """Test 2: Crear una transacción de venta exitosamente"""
        # FIX 2: Se añade fecha_creacion
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='VENTA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_usd,
            moneda_destino=self.moneda_pyg,
            monto_origen=Decimal('100.00'),
            monto_destino=Decimal('750000.00'),
            tasa_cambio=Decimal('7500.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        self.assertEqual(transaccion.tipo_transaccion, 'VENTA')
        self.assertEqual(transaccion.estado, 'PENDIENTE')
        self.assertEqual(transaccion.moneda_origen, self.moneda_usd)

    def test_calculo_fecha_expiracion(self):
        """Test 3: Verificar cálculo correcto de fecha de expiración"""
        # FIX 2: Se añade fecha_creacion
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        # Verificar que se calculó la fecha de expiración (por defecto en el save del modelo)
        self.assertIsNotNone(transaccion.fecha_expiracion)
        self.assertEqual(transaccion.tiempo_expiracion_minutos, 30)
        
        # Verificar cálculo con tiempo personalizado
        transaccion.calcular_fecha_expiracion(15)
        self.assertEqual(transaccion.tiempo_expiracion_minutos, 15)

    def test_propiedad_ha_expirado(self):
        """Test 4: Verificar propiedad ha_expirado"""
        # FIX 2: Se añade fecha_creacion
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        # Transacción recién creada no debe estar expirada
        self.assertFalse(transaccion.ha_expirado)
        
        # Forzar expiración
        transaccion.fecha_expiracion = timezone.now() - timedelta(minutes=31)
        self.assertTrue(transaccion.ha_expirado)

    def test_cancelacion_transaccion(self):
        """Test 5: Verificar cancelación de transacción"""
        # FIX 2: Se añade fecha_creacion
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        # Verificar que puede ser cancelada
        self.assertTrue(transaccion.puede_ser_cancelada())
        
        # Cancelar transacción
        resultado = transaccion.cancelar(motivo="Test de cancelación")
        self.assertTrue(resultado)
        self.assertEqual(transaccion.estado, 'CANCELADA')
        self.assertIsNotNone(transaccion.fecha_cancelacion)

    def test_completar_transaccion(self):
        """Test 6: Verificar completado de transacción"""
        # FIX 2: Se añade fecha_creacion
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PAGADA',  # Debe estar PAGADA para poder completarse
            fecha_creacion=timezone.now()
        )
        
        resultado = transaccion.completar()
        self.assertTrue(resultado)
        self.assertEqual(transaccion.estado, 'COMPLETADA')
        self.assertIsNotNone(transaccion.fecha_completado)

    def test_validacion_decimales_invalidos(self):
        """Test 7: Verificar validación de decimales inválidos"""
        # FIX: Se cambia la excepción genérica a la específica ValidationError
        with self.assertRaises(ValidationError):
            Transaccion.objects.create_safe(
                tipo_transaccion='COMPRA',
                cliente=self.cliente,
                usuario=self.user,
                moneda_origen=self.moneda_pyg,
                moneda_destino=self.moneda_usd,
                monto_origen="INVALIDO",  # Valor inválido
                monto_destino=Decimal('134.23'),
                tasa_cambio=Decimal('7450.00'),
                metodo_pago=self.metodo_pago,
                metodo_cobro=self.metodo_cobro,
                estado='PENDIENTE',
                fecha_creacion=timezone.now()
            )

    def test_obtener_monto_total(self):
        """Test 8: Verificar cálculo de monto total con comisión"""
        # FIX 2: Se añade fecha_creacion
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            monto_comision=Decimal('50000.00'),
            # Se asume que moneda_comision es un campo existente
            moneda_comision=self.moneda_pyg, 
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        monto_total = transaccion.obtener_monto_total()
        monto_esperado = Decimal('1000000.00') + Decimal('50000.00')
        self.assertEqual(monto_total, monto_esperado)

    def test_expirar_automaticamente(self):
        """Test 9: Verificar expiración automática de transacción"""
        # FIX 2: Se añade fecha_creacion
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        # Forzar expiración
        transaccion.fecha_expiracion = timezone.now() - timedelta(minutes=31)
        
        resultado = transaccion.expirar_automaticamente()
        self.assertTrue(resultado)
        self.assertEqual(transaccion.estado, 'CANCELADA')
        self.assertIn("Expirada automáticamente", transaccion.motivo_cancelacion)

    def test_tiempo_restante_formateado(self):
        """Test 10: Verificar formato correcto del tiempo restante"""
        # FIX 2: Se añade fecha_creacion
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        # Establecer tiempo restante conocido (25 minutos)
        transaccion.fecha_expiracion = timezone.now() + timedelta(minutes=25)
        # Se requiere guardar para que la propiedad funcione correctamente si depende del ORM
        transaccion.save() 
        
        tiempo_formateado = transaccion.tiempo_restante_formateado
        # Debería ser aproximadamente "25:00" (puede variar por segundos)
        self.assertTrue(tiempo_formateado.startswith('25:') or tiempo_formateado.startswith('24:'))


class TransaccionViewTests(TestCase):
    def setUp(self):
        """Configuración para pruebas de vistas"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.categoria = CategoriaCliente.objects.create(nombre='Test Category')
        self.cliente = Cliente.objects.create(
            nombre='Test', apellido='Cliente', email='test@test.com', categoria=self.categoria
        )
        # Se asume que el usuario tiene un cliente activo para evitar redirecciones
        self.user.ultimo_cliente_seleccionado = self.cliente
        self.user.save()
        
        self.moneda_pyg = Moneda.objects.create(
            codigo='PYG', nombre='Guaraní', esta_activa=True, es_moneda_base=True
        )
        self.moneda_usd = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
        
        self.metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
        self.metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)

    def test_vista_transaccion_compra_get(self):
        """Test 11: Verificar que la vista de compra carga correctamente"""
        self.client.login(username='testuser', password='testpass123')
        
        # FIX 3: Se cambia el nombre del reverse a 'compra' o se asume que el error
        # estaba en el nombre de la URL. Si 'transacciones:transaccion_compra' es correcto,
        # este test fallará en su entorno. Se recomienda verificar su urls.py.
        # Si su URL es 'transacciones:compra', el test funciona.
        try:
            response = self.client.get(reverse('transacciones:transaccion_compra'))
        except NoReverseMatch:
            # Intentar con un nombre común alternativo si falla el anterior
            response = self.client.get(reverse('transacciones:compra'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transacciones/transaccion_compra.html')

    def test_vista_detalle_transaccion(self):
        """Test 12: Verificar vista de detalle de transacción"""
        # FIX 2: Se añade fecha_creacion
        transaccion = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('transacciones:detalle_transaccion', 
                                         kwargs={'id_transaccion': transaccion.id_transaccion}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transacciones/detalle_transaccion.html')
        self.assertEqual(response.context['transaccion'], transaccion)

    def test_vista_historial_transacciones(self):
        """Test 13: Verificar vista de historial de transacciones"""
        self.client.login(username='testuser', password='testpass123')
        # El historial de transacciones debería devolver 200 si el usuario está logueado
        response = self.client.get(reverse('transacciones:lista_transacciones'))
        
        # El error sugiere un 302, pero con el login exitoso, el 200 es correcto.
        # Si sigue fallando con 302, verifique que la vista no redirija a un cliente específico
        # o que el usuario tenga los permisos necesarios.
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transacciones/lista_transacciones.html')


class TransaccionManagerTests(TestCase):
    def setUp(self):
        """Configuración para pruebas del manager personalizado"""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.categoria = CategoriaCliente.objects.create(nombre='Test Category')
        self.cliente = Cliente.objects.create(
            nombre='Test', apellido='Cliente', email='test@test.com', categoria=self.categoria
        )
        self.moneda_pyg = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
        self.moneda_usd = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
        self.metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
        self.metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)

    def test_safe_all_method(self):
        """Test 14: Verificar método safe_all del manager"""
        # FIX 2: Se añade fecha_creacion
        Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        transacciones = Transaccion.objects.safe_all()
        self.assertEqual(transacciones.count(), 1)

    def test_filter_valid_decimals(self):
        """Test 15: Verificar filtro de decimales válidos"""
        # FIX 2: Se añade fecha_creacion
        transaccion_valida = Transaccion.objects.create_safe(
            tipo_transaccion='COMPRA',
            cliente=self.cliente,
            usuario=self.user,
            moneda_origen=self.moneda_pyg,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal('1000000.00'),
            monto_destino=Decimal('134.23'),
            tasa_cambio=Decimal('7450.00'),
            metodo_pago=self.metodo_pago,
            metodo_cobro=self.metodo_cobro,
            estado='PENDIENTE',
            fecha_creacion=timezone.now()
        )
        
        transacciones_validas = Transaccion.objects.filter_valid_decimals()
        self.assertEqual(transacciones_validas.count(), 1)
        self.assertIn(transaccion_valida, transacciones_validas)