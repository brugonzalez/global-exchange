from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Optional

from .models import Moneda

NumberLike = Union[int, float, str, Decimal]

__all__ = [
	"formatear_monto_moneda",
]


def _obtener_lugares_decimales(codigo_moneda: str, default: int = 2) -> int:
	"""Devuelve los lugares decimales configurados para una moneda.

	Parameters
	----------
	codigo_moneda : str
		Código (case-insensitive) de la moneda (p.ej. "USD").
	default : int, optional
		Valor por defecto si la moneda no existe. (default=2)

	Returns
	-------
	int
		Cantidad de lugares decimales.
	"""
	if not codigo_moneda:
		return default
	moneda = (
		Moneda.objects.filter(codigo__iexact=codigo_moneda)
		.only("lugares_decimales")
		.first()
	)
	return moneda.lugares_decimales if moneda else default


def _to_decimal(valor: NumberLike) -> Decimal:
	"""Convierte un valor genérico a Decimal de forma segura.

	Se aceptan int, float, str y Decimal. Para float se convierte a string
	primero para minimizar errores binarios.
	"""
	if isinstance(valor, Decimal):
		return valor
	if isinstance(valor, (int,)):
		return Decimal(valor)
	if isinstance(valor, float):
		# Evitar representación binaria inexacta directa
		return Decimal(str(valor))
	if isinstance(valor, str):
		valor_limpio = valor.strip().replace(',', '.')  # permitir coma decimal de entrada
		return Decimal(valor_limpio) if valor_limpio else Decimal('0')
	raise TypeError(f"Tipo de valor no soportado: {type(valor)!r}")


def formatear_monto_moneda(
	valor: Optional[NumberLike],
	codigo_moneda: Optional[str],
	*,
	separador_miles: str = '.',
	separador_decimales: str = ',',
	usar_lugares_moneda: bool = True,
	lugares_decimales_default: int = 2,
	strip_ceros_derecha: bool = False,
) -> str:
	"""Formatea un monto según los lugares decimales de la moneda y reglas locales.

	Reglas implementadas:
	- Obtiene ``lugares_decimales`` desde ``Moneda.lugares_decimales`` (si existe y ``usar_lugares_moneda`` es True).
	- Aplica redondeo HALF_UP.
	- Separa miles con el caracter indicado (por defecto ".").
	- Usa coma "," como separador decimal por defecto (estilo latino). Puede cambiarse.
	- Permite eliminar ceros no significativos a la derecha si ``strip_ceros_derecha`` es True.

	Parameters
	----------
	valor : int | float | str | Decimal | None
		Monto a formatear. Si es None retorna "0" (o "0,<ceros>").
	codigo_moneda : str | None
		Código de la moneda para determinar los lugares decimales.
	separador_miles : str, optional
		Carácter separador de miles (default='.')
	separador_decimales : str, optional
		Carácter separador decimal (default=',')
	usar_lugares_moneda : bool, optional
		Si True intenta usar ``Moneda.lugares_decimales`` (default=True)
	lugares_decimales_default : int, optional
		Fallback de lugares decimales si no se encuentra la moneda (default=2)
	strip_ceros_derecha : bool, optional
		Si True elimina ceros finales en la parte decimal (manteniendo al menos 1 dígito si existe parte decimal).

	Returns
	-------
	str
		Monto formateado (ej: "1.234,50" o "1.234" si se quitaron ceros).

	Examples
	--------
	>>> formatear_monto_moneda(1234.5, 'USD')
	'1.234,50'
	>>> formatear_monto_moneda('1000000', 'PYG', lugares_decimales_default=0)
	'1.000.000'
	>>> formatear_monto_moneda(Decimal('1234.5678'), 'BTC', strip_ceros_derecha=True)
	'1.234,5678'
	"""
	try:
		lugares = (
			_obtener_lugares_decimales(codigo_moneda, lugares_decimales_default)
			if usar_lugares_moneda
			else lugares_decimales_default
		)
	except Exception:
		# En caso de cualquier error al resolver la moneda, usar fallback
		lugares = lugares_decimales_default

	if valor is None:
		# Construir directamente string base
		if lugares <= 0:
			return '0'
		return '0' + separador_decimales + ('0' * lugares)

	try:
		monto = _to_decimal(valor)
	except (InvalidOperation, TypeError):
		# Si no se puede convertir, devolver string seguro
		if lugares <= 0:
			return '0'
		return '0' + separador_decimales + ('0' * lugares)

	# Normalizar escala mediante quantize
	if lugares > 0:
		quant = Decimal('1') / (Decimal('10') ** lugares)  # e.g. 0.01 para 2 decimales
		monto = monto.quantize(quant, rounding=ROUND_HALF_UP)
	else:
		monto = monto.quantize(Decimal('1'), rounding=ROUND_HALF_UP)

	# Convertir a string con punto decimal estándar
	monto_str = f"{monto:f}"  # evita notación científica

	# Asegurar que exista parte decimal según lugares (si no se va a strippear luego)
	if '.' not in monto_str:
		if lugares > 0:
			monto_str += '.' + ('0' * lugares)
	else:
		parte_entera, parte_decimal = monto_str.split('.')
		if lugares > 0 and len(parte_decimal) < lugares:
			monto_str = parte_entera + '.' + parte_decimal.ljust(lugares, '0')

	parte_entera, _, parte_decimal = monto_str.partition('.')

	# Agrupar miles manualmente para soportar separador personalizado
	# (Evita depender de locale global.)
	invertida = parte_entera[::-1]
	grupos = [invertida[i:i+3] for i in range(0, len(invertida), 3)]
	parte_entera_formateada = separador_miles.join(grupo[::-1] for grupo in grupos[::-1])

	if lugares <= 0:
		return parte_entera_formateada

	if strip_ceros_derecha and parte_decimal:
		parte_decimal = parte_decimal.rstrip('0')
		if parte_decimal == '':
			return parte_entera_formateada  # no mostrar separador si quedó vacía

	return parte_entera_formateada + separador_decimales + parte_decimal

