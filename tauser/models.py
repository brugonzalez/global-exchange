from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from divisas.models import Moneda
from rest_framework import serializers

class Tauser(models.Model):
    """
    Modelo para puntos de intercambio Tauser donde los usuarios pueden depositar y retirar divisas.
    """
    ESTADOS_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
        ('MANTENIMIENTO', 'En Mantenimiento'),
        ('TEMPORAL_CERRADO', 'Temporalmente Cerrado'),
    ]

    nombre = models.CharField(max_length=200)

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_CHOICES,
        default='ACTIVO'
    )

    # Información de ubicación
    direccion = models.TextField(help_text="Dirección completa del Tauser")
    ciudad = models.CharField(max_length=100)
    pais = models.CharField(max_length=100, default='Chile')

    # Capacidades operativas
    permite_depositos = models.BooleanField(
        default=True,
        help_text="Si permite que los usuarios depositen dinero/divisas"
    )
    permite_retiros = models.BooleanField(
        default=True,
        help_text="Si permite que los usuarios retiren dinero/divisas"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tauser_tauser'
        verbose_name = 'Tauser'
        verbose_name_plural = 'Tausers'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre}"

    def esta_operativo(self):
        """Verifica si el Tauser está operativo"""
        return self.estado == 'ACTIVO'

    def puede_procesar_retiro(self, monto, moneda):
        """Verifica si puede procesar un retiro de un monto específico"""
        if not self.permite_retiros or not self.esta_operativo():
            return False, "Tauser no disponible para retiros"

        # Verificar stock de la moneda
        try:
            stock = self.stocks.get(moneda=moneda)
            if stock.cantidad_disponible < monto:
                return False, f"Stock insuficiente. Disponible: {stock.cantidad_disponible}"
        except StockTauser.DoesNotExist:
            return False, f"Moneda {moneda.codigo} no disponible en este Tauser"

        return True, "OK"

    def puede_procesar_deposito(self, monto, moneda):
        """Verifica si puede procesar un depósito"""
        if not self.permite_depositos or not self.esta_operativo():
            return False, "Tauser no disponible para depósitos"

        return True, "OK"

    def calcular_comision_retiro(self, monto):
        """Calcula la comisión para un retiro"""
        comision_porcentual = monto * (self.comision_retiro_porcentaje / 100)
        return comision_porcentual + self.comision_retiro_fija

    def calcular_comision_deposito(self, monto):
        """Calcula la comisión para un depósito"""
        comision_porcentual = monto * (self.comision_deposito_porcentaje / 100)
        return comision_porcentual + self.comision_deposito_fija


class StockTauser(models.Model):
    """
    Modelo para el control de stock de divisas por cada Tauser.
    """
    tauser = models.ForeignKey(
        Tauser,
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.CASCADE,
        related_name='stocks_tauser'
    )

    # Stock actual
    cantidad_disponible = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00000000'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Cantidad disponible para operaciones"
    )
    cantidad_reservada = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00000000'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Cantidad reservada para transacciones pendientes"
    )

    # Límites de stock
    stock_minimo = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00000000'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Stock mínimo antes de alertas"
    )
    stock_maximo = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('1000000.00000000'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Stock máximo permitido"
    )

    # Control de alertas
    alerta_stock_bajo = models.BooleanField(
        default=True,
        help_text="Enviar alertas cuando el stock esté bajo"
    )

    fecha_ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tauser_stock_tauser'
        verbose_name = 'Stock de Tauser'
        verbose_name_plural = 'Stocks de Tausers'
        unique_together = ['tauser', 'moneda']
        ordering = ['tauser', 'moneda']

    def __str__(self):
        return f"{self.moneda.codigo}: {self.cantidad_disponible}"

    @property
    def cantidad_total(self):
        """Cantidad total (disponible + reservada)"""
        return self.cantidad_disponible + self.cantidad_reservada

    @property
    def esta_en_stock_minimo(self):
        """Verifica si está en el stock mínimo"""
        return self.cantidad_disponible <= self.stock_minimo

    @property
    def puede_aceptar_mas_stock(self):
        """Verifica si puede aceptar más stock"""
        return self.cantidad_total < self.stock_maximo

    def reservar_cantidad(self, cantidad):
        """Reserva una cantidad para una transacción"""
        if self.cantidad_disponible >= cantidad:
            self.cantidad_disponible -= cantidad
            self.cantidad_reservada += cantidad
            self.save()
            return True
        return False

    def liberar_reserva(self, cantidad):
        """Libera una cantidad reservada"""
        if self.cantidad_reservada >= cantidad:
            self.cantidad_reservada -= cantidad
            self.cantidad_disponible += cantidad
            self.save()
            return True
        return False

    def confirmar_retiro(self, cantidad):
        """Confirma un retiro, reduciendo la cantidad reservada"""
        if self.cantidad_reservada >= cantidad:
            self.cantidad_reservada -= cantidad
            self.save()
            return True
        return False

    def agregar_stock(self, cantidad):
        """Agrega stock (por depósito o reposición)"""
        if self.puede_aceptar_mas_stock:
            nueva_cantidad = self.cantidad_disponible + cantidad
            if nueva_cantidad <= (self.stock_maximo - self.cantidad_reservada):
                self.cantidad_disponible = nueva_cantidad
                self.save()
                return True
        return False


class MovimientoStockTauser(models.Model):
    """
    Modelo para registrar todos los movimientos de stock en los Tausers.
    """
    TIPOS_MOVIMIENTO = [
        ('DEPOSITO', 'Depósito de Cliente'),
        ('RETIRO', 'Retiro de Cliente'),
        ('REPOSICION', 'Reposición de Stock'),
    ]

    stock_tauser = models.ForeignKey(
        StockTauser,
        on_delete=models.CASCADE,
        related_name='movimientos'
    )
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPOS_MOVIMIENTO
    )
    cantidad = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Cantidad del movimiento (positiva para entradas, negativa para salidas)"
    )
    cantidad_anterior = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Cantidad disponible antes del movimiento"
    )
    cantidad_nueva = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Cantidad disponible después del movimiento"
    )

    # Referencias
    referencia_transaccion = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID de transacción relacionada"
    )

    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones del movimiento"
    )

    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tauser_movimiento_stock'
        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f"{self.tipo_movimiento}: {self.cantidad}"


class StockTauserSerializer(serializers.ModelSerializer):
    # Si querés mostrar campos relacionados más descriptivos:
    tauser_nombre = serializers.CharField(source='tauser.nombre', read_only=True)
    moneda_codigo = serializers.CharField(source='moneda.codigo', read_only=True)

    class Meta:
        model = StockTauser
        fields = [
            'id',
            'tauser',
            'tauser_nombre',
            'moneda',
            'moneda_codigo',
            'cantidad_disponible',
            'cantidad_reservada',
            'stock_minimo',
            'stock_maximo',
            'alerta_stock_bajo',
            'fecha_ultima_actualizacion',
            'cantidad_total',
            'esta_en_stock_minimo',
            'puede_aceptar_mas_stock',
        ]