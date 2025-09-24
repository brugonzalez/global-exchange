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

    Attributes
    ----------
    codigo : str
        Código único de la moneda (ej. "USD").
    nombre : str
        Nombre completo de la moneda (ej. "Dólar Estadounidense").
    simbolo : str
        Símbolo de la moneda (ej. "$").
    pais : CountryField
        País asociado a la moneda.
    esta_activa : bool
        Indica si la moneda está activa.
    es_moneda_base : bool
        Indica si la moneda es la base para cálculos.
    comision_compra : Decimal
        Comisión aplicada en la compra de la moneda.
    comision_venta : Decimal
        Comisión aplicada en la venta de la moneda.
    lugares_decimales : int
        Número de lugares decimales para la representación de la moneda y cálculos.
    icono : ImageField
        Icono representativo de la moneda.
    precio_base_inicial : Decimal
        Precio base inicial al crear la moneda.
    denominacion_minima : Decimal
        Denominación mínima para operaciones con esta moneda.
    stock_inicial : Decimal
        Stock inicial disponible de la moneda.
    disponible_para_compra : bool
        Si está disponible para operaciones de compra.
    disponible_para_venta : bool
        Si está disponible para operaciones de venta.
    denominacion_maxima : Decimal
        Denominación máxima para operaciones con esta moneda.
    fecha_creacion : DateTimeField
        Fecha de creación de la moneda.
    fecha_actualizacion : DateTimeField
        Fecha de última actualización de la moneda.
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
    
    # Configuración de trading y disponibilidad
    precio_base_inicial = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0.00'),
        help_text="Precio base inicial al crear la moneda"
    )
    denominacion_minima = models.DecimalField(
        max_digits=20,
        decimal_places=0,
        default=Decimal('1'),
        help_text="Denominación mínima para operaciones con esta moneda"
    )
    stock_inicial = models.DecimalField(
        max_digits=20,
        decimal_places=0,
        default=Decimal('0'),
        help_text="Stock inicial disponible de la moneda"
    )
    disponible_para_compra = models.BooleanField(
        default=True,
        help_text="Si está disponible para operaciones de compra"
    )
    disponible_para_venta = models.BooleanField(
        default=True,
        help_text="Si está disponible para operaciones de venta"
    )
    
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
        """
        Guarda la moneda y se asegura que solo exista una moneda base.
        Si la instancia es una moneda base, se desactivan ``es_moneda_base``
        en todas las demás.
        """
        if self.es_moneda_base:
            Moneda.objects.exclude(pk=self.pk).update(es_moneda_base=False)
        super().save(*args, **kwargs)

    def obtener_tasa_actual(self, categoria):
        """
        Devuelve la tasa de cambio activa más reciente para esta moneda y una categoría.

        Parameters
        ----------
        categoria : CategoriaCliente
            Categoría del cliente para la que se busca la tasa.

        Returns
        -------
        TasaCambio or None
            La tasa activa más reciente, o ``None`` si no hay tasas activas para esa categoría.

        Notes
        -----
        - Se filtra por ``esta_activa=True`` y se ordena por ``-fecha_actualizacion``.
        """
        return self.tasas_cambio.filter(
            esta_activa=True,
            categoria_cliente=categoria
        ).order_by('-fecha_actualizacion').first()

    def obtener_tasa_compra(self):
        """
        Obtiene la tasa de compra actual.

        Returns
        -------
        Decimal or None
            Valor de la tasa de compra, o ``None`` si no hay tasa disponible.

        Notes
        -----
        - Requiere una tasa actual
        """
        tasa = self.obtener_tasa_actual()
        return tasa.tasa_compra if tasa else None

    def obtener_tasa_venta(self):
        """
        Obtiene la tasa de venta actual.

        Returns
        -------
        Decimal or None
            Valor de la tasa de venta, o ``None`` si no hay tasa disponible.

        Notes
        -----
        - Requiere una tasa actual
        """
        tasa = self.obtener_tasa_actual()
        return tasa.tasa_venta if tasa else None

    def obtener_precio_base(self):
        """
        Devuelve el precio base activo de la moneda.

        Returns
        -------
        PrecioBase or None
            Registro activo más reciente, o ``None`` si no existe.
        """
        return self.precio_base.filter(esta_activa=True).first() 
    
    def obtener_tasas_actuales(self):
        """
        Lista todas las tasas activas para esta moneda.

        Returns
        -------
        QuerySet[TasaCambio]
            Conjunto de tasas activas.
        """
        return self.tasas_cambio.filter(esta_activa=True).select_related('categoria_cliente')
    
    def puede_ser_eliminada(self):
        """
        Indica si la moneda puede ser eliminada.

        La moneda **no** puede eliminarse si existen transacciones donde es
        ``moneda_origen`` o ``moneda_destino``.

        Returns
        -------
        bool
            ``True`` si no tiene transacciones asociadas; ``False`` en caso contrario.
        """
        # Verificar si tiene transacciones donde es moneda origen o destino
        from transacciones.models import Transaccion
        
        tiene_transacciones = Transaccion.objects.filter(
            models.Q(moneda_origen=self) | models.Q(moneda_destino=self)
        ).exists()
        
        return not tiene_transacciones
    
    def obtener_estadisticas_uso(self):
        """
        Calcula estadísticas de uso de la moneda en transacciones.

        Returns
        -------
        dict
            Diccionario con:
            - ``total_transacciones`` : int
                Cantidad total de transacciones donde participa la moneda
                (como origen o destino).
            - ``monto_total_origen`` : Decimal
                Suma de montos donde la moneda fue **origen**.
            - ``monto_total_destino`` : Decimal
                Suma de montos donde la moneda fue **destino**.

        Notes
        -----
        - Los valores None se normalizan a 0.
        """
        from transacciones.models import Transaccion
        from django.db.models import Count, Sum
        
        stats = {
            'total_transacciones': 0,
            'monto_total_origen': Decimal('0.00'),
            'monto_total_destino': Decimal('0.00'),
        }
        
        # Transacciones donde es moneda origen
        transacciones_origen = Transaccion.objects.filter(moneda_origen=self).aggregate(
            total=Count('id'),
            monto_total=Sum('monto_origen')
        )
        
        # Transacciones donde es moneda destino
        transacciones_destino = Transaccion.objects.filter(moneda_destino=self).aggregate(
            total=Count('id'),
            monto_total=Sum('monto_destino')
        )
        
        stats['total_transacciones'] = (
            (transacciones_origen['total'] or 0) + 
            (transacciones_destino['total'] or 0)
        )
        stats['monto_total_origen'] = transacciones_origen['monto_total'] or Decimal('0.00')
        stats['monto_total_destino'] = transacciones_destino['monto_total'] or Decimal('0.00')
        
        return stats

class PrecioBase(models.Model):
    """
    Precio base vigente de una moneda respecto a una moneda base.

    Representa el precio a partir del cual se calculan tasas de cambio
    y márgenes por categoría. Solo puede existir **un** registro activo por
    (moneda, moneda_base) a la vez; este modelo se encarga de desactivar
    automáticamente los anteriores cuando se guarda uno nuevo activo.

    Attributes
    ----------
    moneda : Moneda
        Moneda cuyo precio estamos definiendo.
    moneda_base : Moneda
        Moneda de referencia (PYG).
    precio_base : Decimal
        Valor base de la moneda expresado en la moneda de referencia.
    esta_activa : bool
        Indica si este registro es el vigente para (moneda, moneda_base).
    fecha_creacion : datetime
        Fecha/hora de alta del registro.
    fecha_actualizacion : datetime
        Última modificación.
    actualizado_por : Usuario or None
        Usuario que realizó la última actualización (si corresponde).

    Notes
    -----
    - La creación/actualización de **tasas de cambio** derivadas de la moneda
      se maneja vía una **señal** `post_save`.
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
        Guarda el registro garantizando que haya un único precio base activo por par.

        Si el registro se guarda con ``esta_activa=True``, desactiva cualquier otro
        precio base activo existente para la misma combinación (moneda, moneda_base).

        Returns
        -------
        None

        Notes
        -----
        - La actualización se ejecuta dentro de una transacción atómica para evitar
          estados intermedios inconsistentes.
        - La generación/actualización de :class:`TasaCambio` vinculadas se gestiona
          en la señal `post_save`, no acá.
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
    Tasas de cambio por moneda, moneda base y categoría de cliente.

    Cada registro representa la tasa vigente para un par
    (moneda/moneda_base) ajustada por la categoría del cliente. 

    Attributes
    ----------
    moneda : Moneda
        Moneda objetivo de la tasa (ej.: EUR).
    moneda_base : Moneda
        Moneda de referencia (ej.: USD).
    precio_base : PrecioBase
        Precio base desde el cual se calcularon las tasas.
    categoria_cliente : CategoriaCliente
        Categoría a la que aplica la tasa
    fecha_creacion : datetime
        Cuándo se creó el registro.
    fecha_actualizacion : datetime
        Última vez que se modificó.
    esta_activa : bool
        Indica si esta tasa está vigente para su combinación.
    tasa_compra : Decimal
        Tasa de compra aplicada al cliente.
    tasa_venta : Decimal
        Tasa de venta aplicada al cliente.

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
        """
        Guarda el registro garantizando que haya un único precio base activo por par.
        Luego agrega una entrada en :class:`HistorialTasaCambio` con las tasas
        del momento
        """
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
    Modelo para guardar las tasas de cambio históricas de cada moneda.

    Attributes
    ----------
    moneda : Moneda
        Moneda a la que corresponde la tasa.
    moneda_base : Moneda
        Moneda base en la que se expresa la tasa
    categoria_cliente : CategoriaCliente
        La categoría de cliente a la que se aplica la tasa de cambio.
    precio_base : Decimal
        El precio base de la moneda en ese momento.
    tasa_compra : Decimal
        Precio de compra en ese momento.
    tasa_venta : Decimal
        Precio de venta en ese momento.
    comision_compra : Decimal
        Comisión de compra en ese momento.
    comision_venta : Decimal
        Comisión de venta en ese momento.
    marca_de_tiempo : datetime
        Cuando se guardó ese registro
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

    Representa una alerta que se activa cuando una moneda alcanza un cierto valor
    o experimenta una variación significativa en su tasa de cambio.

    Attributes
    ----------
    usuario : Usuario
        El usuario que creó la alerta.
    moneda : Moneda
        La moneda para la cual se crea la alerta.
    tipo_alerta : str
        El tipo de alerta (ej. tasa objetivo, aumento, disminución).
    tasa_objetivo : Decimal
        El valor al que tiene que llegar la tasa para activar la alerta (solo requerido en alertas tipo ``RATE_TARGET``).
    cambio_porcentual : Decimal
        El porcentaje de cambio que dispara la alerta
    esta_activa : bool
        Indica si la alerta está activa o no
    ultima_activacion : datetime
        Marca de tiempo de la última activación de la alerta
    conteo_activaciones : int
        Número de veces que se ha disparado la alerta
    fecha_creacion : datetime
        Marca de tiempo de la creación de la alerta
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


class MetodoCobro(models.Model):
    """
    Modelo para la configuración de métodos de cobro (cómo el usuario recibirá el dinero).
    """
    TIPOS_METODO = [
        ('BANK_TRANSFER', 'Transferencia Bancaria'),
        ('DIGITAL_WALLET', 'Billetera Digital'),
        ('CASH', 'Efectivo'),
        ('CHECK', 'Cheque'),
    ]

    GRUPOS_METODO = [
        ('BANKING', 'Banca y Transferencias'),
        ('DIGITAL_WALLETS', 'Billeteras Digitales'),
        ('CASH_PICKUP', 'Retiro en Caja'),
    ]

    nombre = models.CharField(max_length=100)
    tipo_metodo = models.CharField(max_length=20, choices=TIPOS_METODO)
    grupo_metodo = models.CharField(
        max_length=30,
        choices=GRUPOS_METODO,
        default='BANKING',
        help_text="Grupo al que pertenece este método de cobro"
    )
    esta_activo = models.BooleanField(default=True)
    soporta_compra = models.BooleanField(default=True)
    soporta_venta = models.BooleanField(default=True)
    monto_minimo = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    monto_maximo = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'divisas_metodo_cobro'
        verbose_name = 'Método de Cobro'
        verbose_name_plural = 'Métodos de Cobro'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

