"""
Modelo para gestionar los medios de pago asociados a los clientes.

Este modelo permite almacenar diferentes tipos de medios de pago
como efectivo, billetera, transferencia, tarjeta y cheque.
Cada medio de pago está vinculado a un cliente específico y puede
incluir detalles adicionales según el tipo de medio de pago.

Clases principales:
-------------------
- MedioPago: Representa un medio de pago asociado a un cliente.

Notas:
De momento solo se tiene el metodo de pago con tarjeta.
"""
from django.db import models

from clientes.models import Cliente

class MedioPago(models.Model):

    """
    Modelo que representa un medio de pago asociado a un cliente.
    Puede ser efectivo, billetera, transferencia, tarjeta o cheque.
    Se almacenan datos específicos según el tipo de medio de pago.

    Atributes:
    ----------
    cliente : ForeignKey
        Referencia al cliente asociado al medio de pago.
    usuario_creacion : ForeignKey
        Usuario que creó el medio de pago.
    tipo : CharField
        Tipo de medio de pago (efectivo, billetera, transferencia, tarjeta, cheque).
    activo : BooleanField
        Indica si el medio de pago está activo.
    fecha_creacion : DateTimeField
        Fecha y hora de creación del medio de pago.
    nombre_titular : CharField
        Nombre del titular de la tarjeta (si aplica).
    stripe_payment_method_id : CharField
        ID del metodo de pago en Stripe si aplica
    ultimos_digitos : CharField
        Últimos cuatro dígitos de la tarjeta (si aplica).
    marca : CharField
        Marca de la tarjeta (si aplica).
    alias_bancario : CharField
        Alias bancario para transferencias (si aplica).
    cbu : CharField
        CBU para transferencias (si aplica).

    Metodos:
    __str__: Retorna una representación legible del medio de pago.

    """
    # TIPOS = [
    #     ("efectivo", "Efectivo"),
    #     ("billetera", "Billetera"),
    #     ("transferencia", "Transferencia"),
    #     ("tarjeta", "Tarjeta"),
    #     ("cheque", "Cheque"),
    # ]

    TIPOS = [
        ("tarjeta", "Tarjeta"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='medio_pagos', default=0)
    usuario_creacion = models.ForeignKey('cuentas.Usuario', on_delete=models.SET_NULL, null=True, blank=True)

    tipo = models.CharField(max_length=20, choices=TIPOS, default="efectivo")

    activo= models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    #campos para una tarjeta
    nombre_titular = models.CharField(max_length=100, blank=True, null=True)
    stripe_payment_method_id = models.CharField(max_length=100)  #puede ser visa, mastercard
    ultimos_digitos = models.CharField(max_length=4, blank=True, null=True)
    marca = models.CharField(max_length=100, blank=True, null=True)

    #campos para la transferencia
    alias_bancario = models.CharField(max_length=50, blank=True, null=True)
    cbu = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        """
        Retorna una representación legible del medio de pago.
        """
        return f"{self.nombre_titular} - {self.marca} - {self.ultimos_digitos}"