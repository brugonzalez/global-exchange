"""Utilidades para límites de transacción de clientes.

Se exponen dos funciones independientes para obtener cada límite por separado:

	obtener_limite_diario(cliente)  -> Decimal
	obtener_limite_mensual(cliente) -> Decimal

Reglas:
	- Si `cliente.usa_limites_default` es True se usan los valores de su categoría.
	- Si es False se intenta usar el registro OneToOne `cliente.limites`.
	- Si no existe el registro personalizado (caso anómalo) se hace fallback
	  a la categoría.

Estas funciones NO realizan consultas agregadas de transacciones; solo devuelven
el número máximo configurado.
"""

from decimal import Decimal
from django.db.models import Sum
from cuentas.models import Configuracion
from transacciones.models import Transaccion
from django.utils import timezone
from django.db.models import Case, When, DecimalField, Value, Q




def _config_decimal(clave: str, fallback: any) -> Decimal:
	"""
    Obtiene un valor desde Configuracion y lo convierte a Decimal.

    Parameters
	----------
	clave : str
		Clave de configuración a buscar.
	

	"""
	valor = Configuracion.obtener_valor(clave, valor_por_defecto=None)
	if valor is None:
		return fallback
	try:
		return Decimal(str(valor))
	except Exception:
		return fallback


def obtener_limite_diario(cliente) -> Decimal:
	"""Devuelve el límite diario efectivo para el cliente.

	Parámetros
	----------
	cliente : Cliente
		Instancia del modelo Cliente.

	Returns
	-------
	Decimal
		Valor del límite diario en gs.
	"""
	if getattr(cliente, "usa_limites_default", True):
		return _config_decimal('LIMITE_TRANSACCION_DIARIO_DEFAULT', None)
	limites = getattr(cliente, "limites", None)
	if limites is not None:
		return limites.monto_limite_diario
	return _config_decimal('LIMITE_TRANSACCION_DIARIO_DEFAULT', None)


def obtener_limite_mensual(cliente) -> Decimal:
	"""Devuelve el límite mensual efectivo para el cliente.

	Parámetros
	----------
	cliente : Cliente
		Instancia del modelo Cliente.

	Returns
	-------
	Decimal
		Valor del límite mensual en gs.
	"""
	if getattr(cliente, "usa_limites_default", True):
		return _config_decimal('LIMITE_TRANSACCION_MENSUAL_DEFAULT', None)
	limites = getattr(cliente, "limites", None)
	if limites is not None:
		return limites.monto_limite_mensual
	# Fallback si no existe registro personalizado aún
	return _config_decimal('LIMITE_TRANSACCION_MENSUAL_DEFAULT', None)

def obtener_monto_transacciones_hoy(cliente) -> Decimal:
    """Devuelve el monto total (en PYG) de las transacciones del cliente para hoy.

    Criterio (alineado con la función mensual):
    - Para transacciones de tipo COMPRA se suma `monto_origen` SOLO si `moneda_origen.codigo == 'PYG'`.
    - Para transacciones de tipo VENTA  se suma `monto_destino` SOLO si `moneda_destino.codigo == 'PYG'`.
    - Estados considerados: COMPLETADA, PAGADA, PENDIENTE.

    Se usa un solo aggregate con Case/When para evitar dos consultas y asegurar consistencia.
    Si no existen transacciones válidas devuelve Decimal('0.00').
    
    Parameters
	----------
	cliente : Cliente
		Instancia del modelo Cliente.
            
	Returns
	-------
	Decimal
		Monto total de transacciones realizadas por el cliente en la fecha especificada.
    """

    hoy = timezone.localdate()
    estados_validos = ['COMPLETADA', 'PAGADA', 'PENDIENTE']

    qs = Transaccion.objects.filter(
        cliente=cliente,
		fecha_creacion__date=hoy,
        estado__in=estados_validos
    ).filter(
        Q(tipo_transaccion='COMPRA') |
        Q(tipo_transaccion='VENTA')
    ) # DEBUG: Ver la consulta generada
    total = qs.aggregate(
        total=Sum(
            Case(
                When(
                    tipo_transaccion='COMPRA',
                    then='monto_origen'
                ),
                When(
                    tipo_transaccion='VENTA',
                    then='monto_destino'
                ),
                default=Value(0),
                output_field=DecimalField(max_digits=20, decimal_places=8)
            )
        )
    )['total'] or Decimal('0.00')

    # Normalizar a 2 decimales si quieres consistencia con límites (que suelen ser enteros/2 dec)
    try:
        return Decimal(total).quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0.00')

def obtener_monto_transacciones_mes(cliente) -> Decimal:
    """Devuelve el monto total (indistinto de moneda) de las transacciones del cliente en el mes actual.

    Alineado con la lógica de `obtener_monto_transacciones_hoy`:
    - Si es COMPRA suma `monto_origen`.
    - Si es VENTA  suma `monto_destino`.
    - Estados considerados: COMPLETADA, PAGADA, PENDIENTE.

    Si quieres limitar solo a PYG, agrega filtros similares a:
        .filter(Q(tipo_transaccion='COMPRA', moneda_origen__codigo='PYG') | Q(tipo_transaccion='VENTA', moneda_destino__codigo='PYG'))
    antes del aggregate.
    """

    ahora = timezone.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Primer día del mes siguiente
    if inicio_mes.month == 12:
        inicio_mes_siguiente = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
    else:
        inicio_mes_siguiente = inicio_mes.replace(month=inicio_mes.month + 1)

    estados_validos = ['COMPLETADA', 'PAGADA', 'PENDIENTE']

    qs = (Transaccion.objects
          .filter(
              cliente=cliente,
              fecha_creacion__gte=inicio_mes,
              fecha_creacion__lt=inicio_mes_siguiente,
              estado__in=estados_validos
          )
          .filter(Q(tipo_transaccion='COMPRA') | Q(tipo_transaccion='VENTA')))

    total = qs.aggregate(
        total=Sum(
            Case(
                When(tipo_transaccion='COMPRA', then='monto_origen'),
                When(tipo_transaccion='VENTA', then='monto_destino'),
                default=Value(0),
                output_field=DecimalField(max_digits=20, decimal_places=8)
            )
        )
    )['total'] or Decimal('0.00')

    try:
        return Decimal(total).quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0.00')

def verificar_limites(cliente, monto_propuesto: Decimal):
    """Devuelve un dict con el estado de límites para un monto propuesto.

	Parameters
	----------
	cliente : Cliente
		Instancia del modelo Cliente.
	monto_propuesto : Decimal
		Monto que se quiere evaluar contra los límites.
		Se asume que está en la moneda base (PYG).
            
	Returns
	-------
	dict
		Un diccionario con las siguientes claves:
		- 'limite_diario': Decimal o None
		- 'limite_mensual': Decimal o None
		- 'usado_diario': Decimal
		- 'usado_mensual': Decimal
		- 'restante_diario': Decimal o None	
    """
    from . import utils as _u  # por si se importa indirectamente
    # Para evitar recursión si renombrado, usamos funciones locales ya definidas
    limite_d = obtener_limite_diario(cliente)
    limite_m = obtener_limite_mensual(cliente)
    usado_d = obtener_monto_transacciones_hoy(cliente)
    usado_m = obtener_monto_transacciones_mes(cliente)

    # Tratar None como 0 (sin límite => None => no se bloquea)
    ilimitado_d = (limite_d is None or limite_d == 0)
    ilimitado_m = (limite_m is None or limite_m == 0)

    excede_diario = False
    excede_mensual = False
    restante_d = None
    restante_m = None

    if not ilimitado_d:
        restante_d = limite_d - usado_d
        excede_diario = (usado_d + monto_propuesto) > limite_d
    if not ilimitado_m:
        restante_m = limite_m - usado_m
        excede_mensual = (usado_m + monto_propuesto) > limite_m

    return {
        'limite_diario': limite_d,
        'limite_mensual': limite_m,
        'usado_diario': usado_d,
        'usado_mensual': usado_m,
        'restante_diario': restante_d,
        'restante_mensual': restante_m,
        'excede_diario': excede_diario,
        'excede_mensual': excede_mensual,
    }