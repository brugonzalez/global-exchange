from django.db import models
from decimal import Decimal
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Moneda(models.Model):
    """
    Modelo para las monedas soportadas por el sistema.
    """
    TIPOS_MONEDA = [
        ('FIAT', 'Moneda Fiat'),
        ('DIGITAL', 'Moneda Digital'),
        ('CRYPTO', 'Criptomoneda'),
    ]

    codigo = models.CharField(
        max_length=10, 
        unique=True,
        help_text="Código de la moneda (USD, EUR, PYG, etc.)"
    )
    nombre = models.CharField(max_length=100)
    simbolo = models.CharField(max_length=10)
    tipo_moneda = models.CharField(
        max_length=20, 
        choices=TIPOS_MONEDA, 
        default='FIAT'
    )
    esta_activa = models.BooleanField(default=True)
    es_moneda_base = models.BooleanField(
        default=False,
        help_text="Moneda base para cálculos (solo una puede ser base)"
    )
    
    # Para la moneda digital de la empresa
    es_moneda_empresa = models.BooleanField(
        default=False,
        help_text="Moneda digital propia de la empresa"
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

    def obtener_tasa_actual(self):
        """Obtiene la tasa de cambio más reciente para esta moneda."""
        return self.tasas_cambio.filter(esta_activa=True).order_by('-fecha_actualizacion').first()

    def obtener_tasa_compra(self):
        """Obtiene la tasa de compra actual."""
        tasa = self.obtener_tasa_actual()
        return tasa.tasa_compra if tasa else None

    def obtener_tasa_venta(self):
        """Obtiene la tasa de venta actual."""
        tasa = self.obtener_tasa_actual()
        return tasa.tasa_venta if tasa else None


class TasaCambio(models.Model):
    """
    Modelo para las tasas de cambio.
    """
    FUENTES = [
        ('API', 'API Externa'),
        ('MANUAL', 'Ingreso Manual'),
        ('CALCULADO', 'Calculado'),
    ]

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
    
    # Tasas
    tasa_compra = models.DecimalField(
        max_digits=20, 
        decimal_places=8,
        help_text="Tasa de compra (precio al que compramos la moneda)"
    )
    tasa_venta = models.DecimalField(
        max_digits=20, 
        decimal_places=8,
        help_text="Tasa de venta (precio al que vendemos la moneda)"
    )
    diferencial = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        help_text="Diferencial entre compra y venta"
    )
    
    # Fuente y validación
    fuente = models.CharField(max_length=20, choices=FUENTES, default='API')
    esta_activa = models.BooleanField(default=True)
    
    # Marcas de tiempo
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    valida_hasta = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Fecha hasta la cual es válida esta tasa"
    )
    
    # Usuario que actualizó (para tasas manuales)
    actualizado_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasas_actualizadas'
    )

    class Meta:
        db_table = 'divisas_tasa_cambio'
        verbose_name = 'Tasa de Cambio'
        verbose_name_plural = 'Tasas de Cambio'
        ordering = ['-fecha_actualizacion']
        unique_together = ['moneda', 'moneda_base', 'esta_activa']

    def __str__(self):
        return f"{self.moneda.codigo}/{self.moneda_base.codigo} - Compra: {self.tasa_compra} - Venta: {self.tasa_venta}"

    def save(self, *args, **kwargs):
        """Calcula el diferencial y maneja la lógica de la tasa activa."""
        from django.db import transaction
        from decimal import InvalidOperation
        
        # Calcular diferencial con manejo de errores
        try:
            if self.tasa_compra is not None and self.tasa_venta is not None:
                self.diferencial = self.tasa_venta - self.tasa_compra
            else:
                self.diferencial = Decimal('0')
        except (InvalidOperation, TypeError, ValueError) as e:
            logger.warning(f"Error al calcular diferencial para tasa de cambio {self.moneda.codigo}/{self.moneda_base.codigo}: {e}")
            self.diferencial = Decimal('0')
        
        # Usar transacción para asegurar atomicidad y prevenir violaciones de la restricción unique
        with transaction.atomic():
            # Si se está estableciendo esta como activa, desactivar otras tasas para el mismo par
            if self.esta_activa:
                # Primero, manejar el caso donde estamos actualizando un registro existente
                if self.pk:
                    # Establecer temporalmente esta instancia como inactiva para evitar problemas de restricción
                    esta_activa_actual = self.esta_activa
                    self.esta_activa = False
                    super().save(update_fields=['esta_activa'], *args, **kwargs)
                    
                    # Ahora desactivar otras tasas activas para el mismo par
                    TasaCambio.objects.filter(
                        moneda=self.moneda,
                        moneda_base=self.moneda_base,
                        esta_activa=True
                    ).exclude(pk=self.pk).update(esta_activa=False)
                    
                    # Restaurar el estado activo y guardar todos los campos
                    self.esta_activa = esta_activa_actual
                    super().save(*args, **kwargs)
                else:
                    # Para nuevas instancias, desactivar primero otras tasas
                    TasaCambio.objects.filter(
                        moneda=self.moneda,
                        moneda_base=self.moneda_base,
                        esta_activa=True
                    ).update(esta_activa=False)
                    
                    # Luego guardar la nueva instancia
                    super().save(*args, **kwargs)
            else:
                # Si no está activa, simplemente guardar normalmente
                super().save(*args, **kwargs)

    def es_valida(self):
        """Verifica si la tasa todavía es válida."""
        if self.valida_hasta:
            return timezone.now() <= self.valida_hasta
        return True


class HistorialTasaCambio(models.Model):
    """
    Modelo para almacenar tasas de cambio históricas para gráficos y análisis.
    """
    moneda = models.ForeignKey(
        Moneda, 
        on_delete=models.CASCADE, 
        related_name='historial_tasa'
    )
    moneda_base = models.ForeignKey(
        Moneda, 
        on_delete=models.CASCADE, 
        related_name='historial_tasa_base'
    )
    
    # Valores de la tasa
    tasa_compra = models.DecimalField(max_digits=20, decimal_places=8)
    tasa_venta = models.DecimalField(max_digits=20, decimal_places=8)
    
    # Marcas de tiempo
    marca_de_tiempo = models.DateTimeField(default=timezone.now)
    
    # Datos adicionales para análisis
    volumen = models.DecimalField(
        max_digits=20, 
        decimal_places=8, 
        default=Decimal('0.00'),
        help_text="Volumen de transacciones en este período"
    )
    
    class Meta:
        db_table = 'divisas_historial_tasa_cambio'
        verbose_name = 'Historial de Tasa'
        verbose_name_plural = 'Historial de Tasas'
        ordering = ['-marca_de_tiempo']
        indexes = [
            models.Index(fields=['moneda', 'marca_de_tiempo']),
            models.Index(fields=['marca_de_tiempo']),
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