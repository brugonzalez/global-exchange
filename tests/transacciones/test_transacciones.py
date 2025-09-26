import pytest
from django.utils import timezone
from decimal import Decimal
from transacciones.models import Transaccion
from clientes.models import Cliente, CategoriaCliente
from divisas.models import Moneda, MetodoPago, MetodoCobro
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_transaccion_creacion_compra():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    assert trans.tipo_transaccion == 'COMPRA'
    assert trans.estado == 'PENDIENTE'

@pytest.mark.django_db
def test_transaccion_creacion_venta():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='VENTA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('750000.00'),
        monto_destino=Decimal('100.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    assert trans.tipo_transaccion == 'VENTA'
    assert trans.estado == 'PENDIENTE'

@pytest.mark.django_db
def test_transaccion_estado_cancelada():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    trans.cancelar(motivo="Test cancel")
    assert trans.estado == 'CANCELADA'
    assert trans.motivo_cancelacion == "Test cancel"

@pytest.mark.django_db
def test_transaccion_estado_completada():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PAGADA',
        fecha_creacion=timezone.now()
    )
    trans.completar()
    assert trans.estado == 'COMPLETADA'
    assert trans.fecha_completado is not None

@pytest.mark.django_db
def test_transaccion_fecha_expiracion_default():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    assert trans.fecha_expiracion is not None
    assert trans.tiempo_expiracion_minutos == 30

@pytest.mark.django_db
def test_transaccion_fecha_expiracion_personalizada():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    trans.calcular_fecha_expiracion(10)
    assert trans.tiempo_expiracion_minutos == 10

@pytest.mark.django_db
def test_transaccion_ha_expirado_false_true():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    assert not trans.ha_expirado
    trans.fecha_expiracion = timezone.now() - timezone.timedelta(minutes=31)
    trans.save()
    assert trans.ha_expirado

@pytest.mark.django_db
def test_transaccion_obtener_monto_total():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        monto_comision=Decimal('10.00'),
        moneda_comision=moneda_origen,
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    assert trans.obtener_monto_total() == Decimal('110.00')

@pytest.mark.django_db
def test_transaccion_expirar_automaticamente():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    trans.fecha_expiracion = timezone.now() - timezone.timedelta(minutes=31)
    trans.save()
    result = trans.expirar_automaticamente()
    assert result is True
    assert trans.estado == 'CANCELADA'
    assert "Expirada automáticamente" in trans.motivo_cancelacion
    
    
@pytest.mark.django_db
def test_transaccion_str_method():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    assert str(trans) != ""

@pytest.mark.django_db
def test_transaccion_clean_validation():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    trans.clean()  # Should not raise

@pytest.mark.django_db
def test_transaccion_manager_get_queryset():
    qs = Transaccion.objects.get_queryset()
    assert hasattr(qs, 'safe_iterate')

@pytest.mark.django_db
def test_transaccion_puede_ser_cancelada():
    categoria = CategoriaCliente.objects.create(nombre='Cat')
    cliente = Cliente.objects.create(nombre='Test', apellido='User', email='test@user.com', categoria=categoria)
    user = User.objects.create_user(username='testuser', password='testpass')
    moneda_origen = Moneda.objects.create(codigo='USD', nombre='Dólar', esta_activa=True)
    moneda_destino = Moneda.objects.create(codigo='PYG', nombre='Guaraní', esta_activa=True)
    metodo_pago = MetodoPago.objects.create(nombre='Transferencia', esta_activo=True)
    metodo_cobro = MetodoCobro.objects.create(nombre='Efectivo', esta_activo=True)
    trans = Transaccion.objects.create_safe(
        tipo_transaccion='COMPRA',
        cliente=cliente,
        usuario=user,
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        monto_origen=Decimal('100.00'),
        monto_destino=Decimal('750000.00'),
        tasa_cambio=Decimal('7500.00'),
        metodo_pago=metodo_pago,
        metodo_cobro=metodo_cobro,
        estado='PENDIENTE',
        fecha_creacion=timezone.now()
    )
    assert trans.puede_ser_cancelada() is True
