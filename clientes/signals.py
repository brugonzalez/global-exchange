"""Señales de la aplicación clientes.

Actualmente:
	- post_save(Cliente): crea automáticamente un registro
	  LimiteTransaccionCliente si no existe todavía.

Notas:
	- No lanza excepción si no hay monedas disponibles; simplemente no crea.
	- Usa la primera moneda activa; si ninguna tiene flag de activo, usa la primera disponible.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Cliente, LimiteTransaccionCliente

try:
	from divisas.models import Moneda
except Exception:  # pragma: no cover - fallback si todavía no migró app divisas
	Moneda = None  # type: ignore


@receiver(post_save, sender=Cliente)
def crear_limites_cliente_post_creacion(sender, instance: Cliente, created: bool, **kwargs):
	"""Crea automáticamente un registro de límites de transacción para el cliente recién creado.

	Estrategia de moneda:
		1. Intentar una moneda marcada como activa (campo 'esta_activa' si existe).
		2. Si no existe ese campo o no hay activas, tomar la primera moneda ordenada por PK.
		3. Si no hay monedas -> abortar silenciosamente.

	Idempotencia:
		- Usa get_or_create para evitar violar la relación OneToOne.
	"""
	if not created:
		return

	# Evitar duplicados si por alguna razón ya existe
	if hasattr(instance, 'limites'):
		try:
			if instance.limites:  # type: ignore[attr-defined]
				return
		except LimiteTransaccionCliente.DoesNotExist:  # pragma: no cover
			pass

	if Moneda is None:
		return

	try:
		moneda = None
		# Intentar filtrar por un campo de actividad si existe
		if hasattr(Moneda, 'esta_activa'):
			moneda = Moneda.objects.filter(esta_activa=True, es_moneda_base=True).order_by('id').first()
		if moneda is None:
			moneda = Moneda.objects.filter(esta_activa=False, es_moneda_base=True).order_by('id').first()
		if moneda is None:
			return  # No hay moneda disponible todavía

		LimiteTransaccionCliente.objects.get_or_create(
			cliente=instance,
			defaults={
				'moneda_limite': moneda,
				'monto_limite_diario': 0,
				'monto_limite_mensual': 0,
			}
		)
	except Exception:  # pragma: no cover - no interrumpir creación de cliente
		# Se podría loggear usando logging.getLogger(__name__).exception("...")
		pass

