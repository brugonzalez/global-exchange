from django.db import models

from clientes.models import Cliente

class MedioPago(models.Model):

    """
    Modelo que representa un medio de pago asociado a un cliente.
    Puede ser efectivo, billetera, transferencia, tarjeta o cheque.
    Se almacenan datos específicos según el tipo de medio de pago.

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
        return f"{self.tipo} - {self.cliente.nombre}"