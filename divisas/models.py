from django.db import models
from decimal import Decimal
from django.utils import timezone
from clientes.models import CategoriaCliente
from django.db import transaction
from django_countries.fields import CountryField
import logging

logger = logging.getLogger(__name__)


class Moneda(models.Model):
    """
    Modelo para las monedas soportadas por el sistema.
    """

    codigo = models.CharField(
        max_length=10, 
        unique=True,
        help_text="Código de la moneda (USD, EUR, PYG, etc.)"
    )
    nombre = models.CharField(max_length=100)
    simbolo = models.CharField(max_length=10)
    pais = CountryField(blank=True, null=True)

    esta_activa = models.BooleanField(default=True)
    es_moneda_base = models.BooleanField(
        default=False,
        help_text="Moneda base para cálculos (solo una puede ser base)"
    )

    # configuracion de comision
    comision_compra = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00'),
        help_text="Comisión aplicada en la compra de la moneda"
    )
    comision_venta = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00'),
        help_text="Comisión aplicada en la venta de la moneda"
    )

    # Configuración de visualización
    lugares_decimales = models.PositiveIntegerField(default=2)
    icono = models.ImageField(upload_to='iconos_moneda/', blank=True, null=True)
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'divisas_moneda'
        verbose_name = 'Moneda'
        verbose_name_plural = 'Monedas'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def save(self, *args, **kwargs):
        """Asegura que solo exista una moneda base."""
        if self.es_moneda_base:
            Moneda.objects.exclude(pk=self.pk).update(es_moneda_base=False)
        super().save(*args, **kwargs)

    def obtener_tasa_actual(self, categoria):
        """
        Obtiene la tasa de cambio más reciente para esta moneda y la categoría del cliente.
        """
        return self.tasas_cambio.filter(
            esta_activa=True,
            categoria_cliente=categoria
        ).order_by('-fecha_actualizacion').first()

    def obtener_tasa_compra(self):
        """Obtiene la tasa de compra actual."""
        tasa = self.obtener_tasa_actual()
        return tasa.tasa_compra if tasa else None

    def obtener_tasa_venta(self):
        """Obtiene la tasa de venta actual."""
        tasa = self.obtener_tasa_actual()
        return tasa.tasa_venta if tasa else None

    def obtener_precio_base(self):
        """Obtiene el precio base actual."""
        return self.precio_base.filter(esta_activa=True).first() 
    
    def obtener_tasas_actuales(self):
        return self.tasas_cambio.filter(esta_activa=True).select_related('categoria_cliente')

class PrecioBase(models.Model):
    """
    Modelo para los precios base de las monedas.
    """

    moneda = models.ForeignKey(
        Moneda, 
        on_delete=models.CASCADE, 
        related_name='precio_base'
    )
    moneda_base = models.ForeignKey(
        Moneda, 
        on_delete=models.CASCADE, 
        related_name='precio_base_base'
    )
    
    # Tasas
    precio_base = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Precio base de la moneda en la moneda base",
        default=Decimal('0.00')
    )

    # Fuente y validación
    esta_activa = models.BooleanField(default=True)
    
    # Marcas de tiempo
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    # Usuario que actualizó 
    actualizado_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasas_actualizadas'
    )

    class Meta:
        db_table = 'divisas_precios_base'
        verbose_name = 'Precio Base'
        verbose_name_plural = 'Precios Base'
        ordering = ['-fecha_actualizacion']
        unique_together = ['moneda', 'moneda_base', 'esta_activa']

    def __str__(self):
        return f"{self.moneda.codigo}/{self.moneda_base.codigo} - Precio base: {self.precio_base}"

    def save(self, *args, **kwargs):
        """
        Guarda el precio base y desactiva otros precios base activos para la misma moneda/moneda_base.
        La creación/actualización de tasas de cambio se maneja ahora en una señal post_save.
        """
        with transaction.atomic():
            if self.esta_activa:
                qs = PrecioBase.objects.filter(
                    moneda=self.moneda,
                    moneda_base=self.moneda_base,
                    esta_activa=True
                )
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                qs.update(esta_activa=False)
                self.esta_activa = True
            super().save(*args, **kwargs)

class TasaCambio(models.Model):
    """
    Modelo para las tasas de cambio.
    """
    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.CASCADE,
        related_name='tasas_cambio'
    )
    moneda_base = models.ForeignKey(
        Moneda,
        on_delete=models.CASCADE,
        related_name='tasas_cambio_base'
    )
    precio_base = models.ForeignKey(
        PrecioBase,
        on_delete=models.CASCADE,
        related_name='tasas_cambio_relacionadas'
    )
    categoria_cliente = models.ForeignKey(
        CategoriaCliente,
        on_delete=models.CASCADE,
        related_name='tasas_cambio_categoria'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    esta_activa = models.BooleanField(default=True)
    
    tasa_compra = models.DecimalField(
        max_digits=20, 
        decimal_places=8, 
        default=Decimal('0.00'), 
        help_text="Tasa de compra"
    )
    tasa_venta = models.DecimalField(
        max_digits=20, 
        decimal_places=8, 
        default=Decimal('0.00'), 
        help_text="Tasa de venta"
    )

    class Meta:
        db_table = 'divisas_tasas_cambio'
        verbose_name = 'Tasa de Cambio'
        verbose_name_plural = 'Tasas de Cambio'
        unique_together = ['moneda', 'moneda_base', 'categoria_cliente', 'esta_activa']

    def __str__(self):
        return f"{self.moneda.codigo}/{self.moneda_base.codigo} - Tasa de Cambio: {self.tasa_compra}/{self.tasa_venta}"
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Agregar SIEMPRE un nuevo historial de tasas de cambio
        with transaction.atomic():
            HistorialTasaCambio.objects.create(
                moneda=self.moneda,
                moneda_base=self.moneda_base,
                categoria_cliente=self.categoria_cliente,
                precio_base=self.precio_base.precio_base,
                tasa_compra=self.tasa_compra,
                tasa_venta=self.tasa_venta,
                comision_compra=self.moneda.comision_compra,
                comision_venta=self.moneda.comision_venta,
                marca_de_tiempo=timezone.now()
            )

class HistorialTasaCambio(models.Model):
    """
    Modelo para almacenar las tasas de cambio históricas para gráficos y análisis.
    """
    moneda = models.ForeignKey(
        Moneda, 
        on_delete=models.CASCADE, 
        related_name='historial_tasa_cambio'
    )
    moneda_base = models.ForeignKey(
        Moneda, 
        on_delete=models.CASCADE, 
        related_name='historial_tasa_cambio_base'
    )
    categoria_cliente = models.ForeignKey(
        CategoriaCliente,
        on_delete=models.CASCADE,
        related_name='historial_tasa_cambio'
    )

    precio_base = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Precio base de la moneda en la moneda base en el momento histórico"
    )
    # Valores de la tasa
    tasa_compra = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00'),
        help_text="Tasa de compra en la fecha de la marca de tiempo"
    )
    tasa_venta = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00'),
        help_text="Tasa de venta en la fecha de la marca de tiempo"
    )

    
    comision_compra = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00'),
        help_text="Comisión de compra en la fecha de la marca de tiempo"
    )
    comision_venta = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00'),
        help_text="Comisión de venta en la fecha de la marca de tiempo"
    )

    # Marcas de tiempo
    marca_de_tiempo = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'divisas_historial_tasas_cambio'
        verbose_name = 'Historial de Tasa de Cambio'
        verbose_name_plural = 'Historial de Tasas de Cambio'
        ordering = ['-marca_de_tiempo']
        indexes = [
            models.Index(fields=['moneda', 'marca_de_tiempo']),
            models.Index(fields=['marca_de_tiempo']),
            models.Index(fields=['categoria_cliente', 'marca_de_tiempo']),
        ]

    def __str__(self):
        return f"{self.moneda.codigo}/{self.moneda_base.codigo} - {self.marca_de_tiempo}"

class MetodoPago(models.Model):
    """
    Modelo para la configuración de métodos de pago.
    """
    TIPOS_METODO = [
        ('BANK_TRANSFER', 'Transferencia Bancaria'),
        ('DIGITAL_WALLET', 'Billetera Digital'),
        ('CREDIT_CARD', 'Tarjeta de Crédito'),
        ('DEBIT_CARD', 'Tarjeta de Débito'),
        ('CASH', 'Efectivo'),
        ('CHECK', 'Cheque'),
    ]

    GRUPOS_METODO = [
        ('BANKING', 'Banca y Transferencias'),
        ('CARDS', 'Tarjetas de Crédito/Débito'),
        ('DIGITAL_WALLETS', 'Billeteras Digitales Locales'),
        ('INTERNATIONAL_WALLETS', 'Billeteras Internacionales'),
        ('CASH_PICKUP', 'Retiro en Caja'),
    ]

    nombre = models.CharField(max_length=100)
    tipo_metodo = models.CharField(max_length=20, choices=TIPOS_METODO)
    grupo_metodo = models.CharField(
        max_length=30, 
        choices=GRUPOS_METODO,
        default='BANKING',
        help_text="Grupo al que pertenece este método de pago"
    )
    esta_activo = models.BooleanField(default=True)
    
    # Configuración
    soporta_compra = models.BooleanField(default=True)
    soporta_venta = models.BooleanField(default=True)
    monto_minimo = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    monto_maximo = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    
    # Detalles de procesamiento
    tiempo_procesamiento_horas = models.PositiveIntegerField(
        default=24,
        help_text="Tiempo de procesamiento en horas"
    )
    porcentaje_comision = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default=Decimal('0.0000'),
        help_text="Comisión como porcentaje"
    )
    comision_fija = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Comisión fija"
    )
    
    # Instrucciones y configuración
    instrucciones = models.TextField(
        blank=True,
        help_text="Instrucciones para el usuario"
    )
    configuracion = models.JSONField(
        default=dict,
        help_text="Configuración específica del método de pago"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'divisas_metodo_pago'
        verbose_name = 'Método de Pago'
        verbose_name_plural = 'Métodos de Pago'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_metodo_display()})"

    def calcular_comision(self, monto):
        """Calcula la comisión para un monto dado."""
        comision_porcentual = monto * (self.porcentaje_comision / 100)
        return comision_porcentual + self.comision_fija


class AlertaTasa(models.Model):
    """
    Modelo para alertas/notificaciones de cambio de tasa.
    """
    TIPOS_ALERTA = [
        ('RATE_INCREASE', 'Subida de Tasa'),
        ('RATE_DECREASE', 'Bajada de Tasa'),
        ('RATE_TARGET', 'Tasa Objetivo'),
        ('VOLATILITY', 'Alta Volatilidad'),
    ]

    usuario = models.ForeignKey(
        'cuentas.Usuario', 
        on_delete=models.CASCADE, 
        related_name='alertas_tasa'
    )
    moneda = models.ForeignKey(
        Moneda, 
        on_delete=models.CASCADE, 
        related_name='alertas'
    )
    tipo_alerta = models.CharField(max_length=20, choices=TIPOS_ALERTA)
    
    # Condiciones de la alerta
    tasa_objetivo = models.DecimalField(
        max_digits=20, 
        decimal_places=8,
        blank=True, 
        null=True
    )
    cambio_porcentual = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        blank=True, 
        null=True,
        help_text="Porcentaje de cambio para activar alerta"
    )
    
    # Estado
    esta_activa = models.BooleanField(default=True)
    ultima_activacion = models.DateTimeField(blank=True, null=True)
    conteo_activaciones = models.PositiveIntegerField(default=0)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'divisas_alerta_tasa'
        verbose_name = 'Alerta de Tasa'
        verbose_name_plural = 'Alertas de Tasa'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.usuario.username} - {self.moneda.codigo} - {self.get_tipo_alerta_display()}"