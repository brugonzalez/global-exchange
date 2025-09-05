
# Señales para crear PrecioBase y tasas de cambio automáticamente
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Moneda, PrecioBase, TasaCambio
from clientes.models import CategoriaCliente
from django.db import transaction
from decimal import Decimal

@receiver(post_save, sender=PrecioBase)
def crear_actualizar_tasas_cambio(sender, instance, created, **kwargs):
	"""
	Crea o actualiza las tasas de cambio cada vez que se guarda un PrecioBase.

	Parameters
	----------
	sender : Model
		Modelo que dispara la señal (:class:`PrecioBase`).
	instance : PrecioBase
		Instancia del PrecioBase recién guardado.
	created : bool
		``True`` si se acaba de crear el PrecioBase, ``False`` si fue una actualización.

	Notes
	-----
	- Solo se ejecuta si el ``PrecioBase`` está activo.
	"""
	if instance.esta_activa:
		with transaction.atomic():
			categorias = CategoriaCliente.objects.all()
			for categoria in categorias:
				# Verificar si ya existe una tasa activa para esta combinación
				tasa_existente = TasaCambio.objects.filter(
					moneda=instance.moneda,
					moneda_base=instance.moneda_base,
					categoria_cliente=categoria,
					esta_activa=True
				).first()
				
				if tasa_existente:
					# Si existe, actualizar los valores
					tasa_existente.precio_base = instance
					tasa_existente.tasa_compra = instance.precio_base + instance.moneda.comision_compra - (categoria.margen_tasa_preferencial * instance.moneda.comision_compra)
					tasa_existente.tasa_venta = instance.precio_base + instance.moneda.comision_venta - (categoria.margen_tasa_preferencial * instance.moneda.comision_venta)
					tasa_existente.save()
				else:
					# Si no existe, crear nueva
					TasaCambio.objects.create(
						moneda=instance.moneda,
						moneda_base=instance.moneda_base,
						precio_base=instance,
						categoria_cliente=categoria,
						tasa_compra=instance.precio_base + instance.moneda.comision_compra - (categoria.margen_tasa_preferencial * instance.moneda.comision_compra),
						tasa_venta=instance.precio_base + instance.moneda.comision_venta - (categoria.margen_tasa_preferencial * instance.moneda.comision_venta),
						esta_activa=True,
					)

@receiver(post_save, sender=Moneda)
def crear_precio_base_al_crear_moneda(sender, instance, created, **kwargs):
	"""
	Crea un PrecioBase para la nueva moneda si no es la moneda base.

	Cada vez que se crea una moneda que no sea la base, se asegura que
	exista un registro de ``PrecioBase`` para esa moneda.

	Parameters
	----------
	sender : Model
		Modelo que dispara la señal (:class:`Moneda`).
	instance : Moneda
		Instancia de la moneda recién guardada.
	created : bool
		``True`` si se acaba de crear la moneda, ``False`` si fue una actualización.

	Notes
	-----
	- Si la moneda ya tiene un PrecioBase, no se crea uno nuevo.
	- El valor inicial por defecto del PrecioBase es 0
	"""
	if created:
		# Buscar la moneda base (es_moneda_base=True)
		moneda_base = Moneda.objects.filter(es_moneda_base=True).first()
		if moneda_base and instance != moneda_base:
			# Solo crear si no es la moneda base
			PrecioBase.objects.get_or_create(
				moneda=instance,
				moneda_base=moneda_base,
				defaults={
					'precio_base': Decimal(0.0),  # Puedes ajustar el valor por defecto
					'esta_activa': True
				}
			)