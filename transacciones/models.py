from django.db import models
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
import uuid
import logging

logger = logging.getLogger(__name__)


class TransaccionQuerySet(QuerySet):
    """QuerySet personalizado para Transaccion con manejo de errores decimal."""
    
    def safe_iterate(self):
        """Itera sobre las transacciones manejando errores de decimal de forma segura."""
        # Obtener los IDs de todas las transacciones primero
        transaccion_ids = list(self.values_list('id', flat=True))
        
        for transaccion_id in transaccion_ids:
            try:
                yield self.get(id=transaccion_id)
            except (InvalidOperation, ValueError, TypeError) as e:
                # Registrar el error y continuar con la siguiente transacción
                logger.error(f"Error al cargar transacción ID {transaccion_id}: {e}")
                continue
    
    def filter_valid_decimals(self):
        """Filtra solo las transacciones con valores decimales válidos."""
        # Este método puede usarse para obtener solo transacciones válidas
        valid_ids = []
        for transaccion_id in self.values_list('id', flat=True):
            try:
                self.get(id=transaccion_id)
                valid_ids.append(transaccion_id)
            except (InvalidOperation, ValueError, TypeError):
                continue
        
        return self.filter(id__in=valid_ids)


class TransaccionManager(models.Manager):
    """Manager personalizado para Transaccion."""
    
    def get_queryset(self):
        return TransaccionQuerySet(self.model, using=self._db)
    
    def safe_all(self):
        """Obtiene todas las transacciones de forma segura."""
        return self.get_queryset().filter_valid_decimals()
    
    def create_safe(self, **kwargs):
        """Crea una transacción validando los decimales primero."""
        # Validar que los valores decimales sean válidos antes de crear
        decimal_fields = ['monto_origen', 'monto_destino', 'tasa_cambio', 'monto_comision']
        
        for field_name in decimal_fields:
            if field_name in kwargs and kwargs[field_name] is not None:
                try:
                    if isinstance(kwargs[field_name], str):
                        kwargs[field_name] = Decimal(kwargs[field_name])
                    elif not isinstance(kwargs[field_name], Decimal):
                        kwargs[field_name] = Decimal(str(kwargs[field_name]))
                except (InvalidOperation, ValueError, TypeError):
                    raise ValidationError(f'El campo {field_name} debe ser un valor decimal válido.')
        
        return super().create(**kwargs)


class Transaccion(models.Model):
    """
    Modelo para transacciones de compra/venta.
    """
    TIPOS_TRANSACCION = [
        ('COMPRA', 'Compra'),
        ('VENTA', 'Venta'),
    ]

    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('PAGADA', 'Pagada'),
        ('CANCELADA', 'Cancelada'),
        ('ANULADA', 'Anulada'),
        ('COMPLETADA', 'Completada'),
        ('FALLIDA', 'Fallida'),
    ]

    # Identificación de la transacción
    id_transaccion = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    numero_transaccion = models.CharField(max_length=20, unique=True, blank=True)
    
    # Detalles de la transacción
    tipo_transaccion = models.CharField(max_length=10, choices=TIPOS_TRANSACCION)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # Partes involucradas
    cliente = models.ForeignKey(
        'clientes.Cliente', 
        on_delete=models.PROTECT, 
        related_name='transacciones'
    )
    usuario = models.ForeignKey(
        'cuentas.Usuario', 
        on_delete=models.PROTECT, 
        related_name='transacciones'
    )
    
    # Detalles de la moneda
    moneda_origen = models.ForeignKey(
        'divisas.Moneda',
        on_delete=models.PROTECT,
        related_name='transacciones_como_origen'
    )
    moneda_destino = models.ForeignKey(
        'divisas.Moneda',
        on_delete=models.PROTECT,
        related_name='transacciones_como_destino'
    )
    
    # Montos
    monto_origen = models.DecimalField(
        max_digits=20, 
        decimal_places=8,
        help_text="Cantidad en moneda origen"
    )
    monto_destino = models.DecimalField(
        max_digits=20, 
        decimal_places=8,
        help_text="Cantidad en moneda destino"
    )
    
    # Tasa de cambio utilizada
    tasa_cambio = models.DecimalField(
        max_digits=20, 
        decimal_places=8,
        help_text="Tasa de cambio aplicada"
    )
    fuente_tasa = models.CharField(
        max_length=50,
        default='MANUAL',
        help_text="Fuente de la tasa de cambio"
    )
    
    # Comisiones y costos
    monto_comision = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    moneda_comision = models.ForeignKey(
        'divisas.Moneda',
        on_delete=models.PROTECT,
        related_name='transacciones_comision',
        blank=True,
        null=True
    )
    
    # Información de pago
    metodo_pago = models.ForeignKey(
        'divisas.MetodoPago',
        on_delete=models.PROTECT,
        related_name='transacciones'
    )
    referencia_pago = models.CharField(
        max_length=200,
        blank=True,
        help_text="Referencia del pago (número de transferencia, etc.)"
    )
    
    # Información de banco/billetera
    info_cuenta_bancaria = models.JSONField(
        blank=True,
        null=True,
        help_text="Información de cuenta bancaria o billetera"
    )
    
    # Marcas de tiempo
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_completado = models.DateTimeField(blank=True, null=True)
    fecha_cancelacion = models.DateTimeField(blank=True, null=True)
    fecha_expiracion = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Fecha y hora en que la transacción expirará automáticamente"
    )
    tiempo_expiracion_minutos = models.PositiveIntegerField(
        default=30,
        help_text="Tiempo de expiración en minutos configurado para esta transacción"
    )
    
    # Información adicional
    notas = models.TextField(blank=True)
    motivo_cancelacion = models.TextField(blank=True)

    # Manager personalizado
    objects = TransaccionManager()

    class Meta:
        db_table = 'transacciones_transaccion'
        verbose_name = 'Transacción'
        verbose_name_plural = 'Transacciones'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['cliente', 'fecha_creacion']),
            models.Index(fields=['estado', 'fecha_creacion']),
            models.Index(fields=['tipo_transaccion', 'fecha_creacion']),
        ]

    def __str__(self):
        return f"#{self.numero_transaccion} - {self.get_tipo_transaccion_display()} - {self.cliente.obtener_nombre_completo()}"

    def clean(self):
        """Validar que los campos decimales contengan valores válidos."""
        super().clean()
        
        # Validar monto_origen
        if self.monto_origen is not None:
            try:
                if isinstance(self.monto_origen, str):
                    Decimal(self.monto_origen)
                elif not isinstance(self.monto_origen, Decimal):
                    Decimal(str(self.monto_origen))
            except (InvalidOperation, ValueError, TypeError):
                raise ValidationError({'monto_origen': 'El monto origen debe ser un valor decimal válido.'})
        
        # Validar monto_destino
        if self.monto_destino is not None:
            try:
                if isinstance(self.monto_destino, str):
                    Decimal(self.monto_destino)
                elif not isinstance(self.monto_destino, Decimal):
                    Decimal(str(self.monto_destino))
            except (InvalidOperation, ValueError, TypeError):
                raise ValidationError({'monto_destino': 'El monto destino debe ser un valor decimal válido.'})
        
        # Validar tasa_cambio
        if self.tasa_cambio is not None:
            try:
                if isinstance(self.tasa_cambio, str):
                    Decimal(self.tasa_cambio)
                elif not isinstance(self.tasa_cambio, Decimal):
                    Decimal(str(self.tasa_cambio))
            except (InvalidOperation, ValueError, TypeError):
                raise ValidationError({'tasa_cambio': 'La tasa de cambio debe ser un valor decimal válido.'})
        
        # Validar monto_comision
        if self.monto_comision is not None:
            try:
                if isinstance(self.monto_comision, str):
                    Decimal(self.monto_comision)
                elif not isinstance(self.monto_comision, Decimal):
                    Decimal(str(self.monto_comision))
            except (InvalidOperation, ValueError, TypeError):
                raise ValidationError({'monto_comision': 'El monto de comisión debe ser un valor decimal válido.'})

    def save(self, *args, **kwargs):
        """Genera el número de transacción si no existe y envía notificaciones."""
        # Validar datos antes de guardar
        self.clean()
        
        es_nueva = self.pk is None
        estado_antiguo = None
        
        # Rastrear cambios de estado para transacciones existentes
        if not es_nueva:
            try:
                instancia_antigua = Transaccion.objects.get(pk=self.pk)
                estado_antiguo = instancia_antigua.estado
            except Transaccion.DoesNotExist:
                estado_antiguo = None
        
        if not self.numero_transaccion:
            # Generar número de transacción: YYYYMMDD-XXXXXX
            from django.utils import timezone
            cadena_fecha = timezone.now().strftime('%Y%m%d')
            
            # Buscar la última transacción de forma segura
            try:
                # Intentar obtener la última transacción válida
                ultima_transaccion = Transaccion.objects.filter(
                    numero_transaccion__startswith=cadena_fecha
                ).order_by('-numero_transaccion').first()
            except (InvalidOperation, ValueError, TypeError) as e:
                # Si hay error con decimales, usar método alternativo
                logger.warning(f"Error al buscar última transacción: {e}. Usando método alternativo.")
                # Buscar solo por numero_transaccion usando SQL directo
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT numero_transaccion FROM transacciones_transaccion "
                        "WHERE numero_transaccion LIKE %s "
                        "ORDER BY numero_transaccion DESC LIMIT 1",
                        [f"{cadena_fecha}%"]
                    )
                    resultado = cursor.fetchone()
                    if resultado:
                        # Crear una transacción temporal solo con el número
                        class UltimaTransaccion:
                            def __init__(self, numero):
                                self.numero_transaccion = numero
                        ultima_transaccion = UltimaTransaccion(resultado[0])
                    else:
                        ultima_transaccion = None
            
            if ultima_transaccion:
                ultimo_num = int(ultima_transaccion.numero_transaccion.split('-')[1])
                nuevo_num = str(ultimo_num + 1).zfill(6)
            else:
                nuevo_num = '000001'
            
            self.numero_transaccion = f"{cadena_fecha}-{nuevo_num}"
            
        """Genera el número de transacción si no existe y calcula la fecha de expiración."""
        es_nueva = self.pk is None
        
        # PARA TRANSACCIONES NUEVAS PENDIENTES: calcular fecha de expiración
        if es_nueva and self.estado == 'PENDIENTE':
            self.calcular_fecha_expiracion()
        
        super().save(*args, **kwargs)
        
        # Enviar notificaciones para eventos de transacción
        try:
            from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
            
            if es_nueva:
                # Nueva transacción creada
                llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_CREADA')
            elif estado_antiguo and estado_antiguo != self.estado:
                # El estado cambió
                if self.estado == 'COMPLETADA':
                    llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_COMPLETADA')
                elif self.estado == 'CANCELADA':
                    llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_CANCELADA')
        except Exception as e:
            # Registrar el error pero no fallar el guardado de la transacción
            import logging
            notificacion_logger = logging.getLogger(__name__)
            notificacion_logger.error(f"Error al enviar la notificación de transacción: {e}")

    def calcular_fecha_expiracion(self, minutos_expiracion=None):
        """Calcula y establece la fecha de expiración"""
        if minutos_expiracion is None:
            # Obtener de la configuración del sistema o usar valor por defecto
            minutos_expiracion = getattr(self, '_tiempo_expiracion_configurado', 30)
        
        self.tiempo_expiracion_minutos = minutos_expiracion
        self.fecha_expiracion = self.fecha_creacion + timedelta(minutes=minutos_expiracion)
    
    @property
    def tiempo_restante(self):
        """Calcula el tiempo restante en segundos para la expiración"""
        if self.fecha_expiracion and self.estado == 'PENDIENTE':
            ahora = timezone.now()
            if ahora < self.fecha_expiracion:
                segundos_restantes = int((self.fecha_expiracion - ahora).total_seconds())
                return max(0, segundos_restantes)  # No negativo
        return 0
    
    @property
    def tiempo_restante_formateado(self):
        """Devuelve el tiempo restante formateado como MM:SS"""
        segundos = self.tiempo_restante
        if segundos > 0:
            minutos = segundos // 60
            segundos_restantes = segundos % 60
            return f"{minutos:02d}:{segundos_restantes:02d}"
        return "00:00"
    
    @property
    def ha_expirado(self):
        """Verifica si la transacción ha expirado"""
        if self.fecha_expiracion and self.estado == 'PENDIENTE':
            return timezone.now() > self.fecha_expiracion
        return False
    
    @property
    def minutos_restantes(self):
        """Devuelve los minutos restantes (para clases CSS)"""
        segundos = self.tiempo_restante
        return segundos // 60
    
    def expirar_automaticamente(self):
        """Marca la transacción como expirada automáticamente"""
        if self.ha_expirado and self.estado == 'PENDIENTE':
            self.estado = 'CANCELADA'
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = f"Expirada automáticamente después de {self.tiempo_expiracion_minutos} minutos"
            self.save()
            
            # Enviar notificación de expiración
            try:
                from notificaciones.tasks import enviar_notificacion_transaccion, llamar_tarea_con_fallback
                llamar_tarea_con_fallback(enviar_notificacion_transaccion, self.id, 'TRANSACCION_EXPIRADA')
            except Exception as e:
                logger.error(f"Error al enviar notificación de expiración: {e}")
            
            return True
        return False

    def puede_ser_cancelada(self):
        """Verifica si la transacción puede ser cancelada."""
        return self.estado in ['PENDIENTE'] and not self.fecha_completado
    
    def cancelar_automaticamente(self):
        """Cancela la transacción automáticamente si ha expirado."""
        if self.ha_expirado and self.puede_ser_cancelada():
            self.estado = 'CANCELADA'
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = f"Expirada automáticamente después de {self.tiempo_expiracion_minutos} minutos"
            self.save()
            return True
        return False

    def cancelar(self, motivo="", cancelado_por=None):
        """Cancela la transacción."""
        if self.puede_ser_cancelada():
            self.estado = 'CANCELADA'
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = motivo
            self.save()
            return True
        return False

    def completar(self):
        """Marca la transacción como completada."""
        if self.estado == 'PAGADA':
            self.estado = 'COMPLETADA'
            self.fecha_completado = timezone.now()
            self.save()
            return True
        return False

    def obtener_monto_total(self):
        """Obtiene el monto total incluyendo comisiones."""
        if self.moneda_comision == self.moneda_origen:
            return self.monto_origen + self.monto_comision
        return self.monto_origen

    def obtener_margen_ganancia(self):
        """Calcula el margen de ganancia para la casa."""
        # Esto calcularía la ganancia basada en la diferencia entre
        # la tasa aplicada y la tasa real del mercado.
        # La implementación depende de la lógica de negocio.
        pass


class SimulacionTransaccion(models.Model):
    """
    Modelo para simulaciones de transacciones.
    """
    usuario = models.ForeignKey(
        'cuentas.Usuario', 
        on_delete=models.CASCADE, 
        related_name='simulaciones'
    )
    cliente = models.ForeignKey(
        'clientes.Cliente', 
        on_delete=models.CASCADE, 
        related_name='simulaciones',
        blank=True,
        null=True
    )
    
    tipo_transaccion = models.CharField(
        max_length=10, 
        choices=Transaccion.TIPOS_TRANSACCION
    )
    
    # Detalles de la moneda
    moneda_origen = models.ForeignKey(
        'divisas.Moneda',
        on_delete=models.CASCADE,
        related_name='simulaciones_como_origen'
    )
    moneda_destino = models.ForeignKey(
        'divisas.Moneda',
        on_delete=models.CASCADE,
        related_name='simulaciones_como_destino'
    )
    
    # Montos
    monto_origen = models.DecimalField(max_digits=20, decimal_places=8)
    monto_destino = models.DecimalField(max_digits=20, decimal_places=8)
    tasa_cambio = models.DecimalField(max_digits=20, decimal_places=8)
    
    # Información de la sesión
    clave_sesion = models.CharField(max_length=40, blank=True)
    direccion_ip = models.GenericIPAddressField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transacciones_simulacion'
        verbose_name = 'Simulación'
        verbose_name_plural = 'Simulaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Simulación {self.get_tipo_transaccion_display()} - {self.usuario.username if self.usuario else 'Anónimo'}"


class Factura(models.Model):
    """
    Modelo para facturas electrónicas.
    """
    ESTADOS = [
        ('EMITIDA', 'Emitida'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('CANCELADA', 'Cancelada'),
    ]

    TIPOS_FACTURA = [
        ('TRANSACCION', 'Factura de Transacción'),
        ('COMISION', 'Factura de Comisión'),
        ('SERVICIO', 'Factura de Servicio'),
    ]

    # Identificación de la factura
    numero_factura = models.CharField(max_length=50, unique=True)
    tipo_factura = models.CharField(max_length=20, choices=TIPOS_FACTURA)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='EMITIDA')
    
    # Transacción relacionada
    transaccion = models.OneToOneField(
        Transaccion,
        on_delete=models.PROTECT,
        related_name='factura',
        blank=True,
        null=True
    )
    
    # Información del cliente
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        related_name='facturas'
    )
    
    # Detalles de la factura
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    monto_impuesto = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    monto_total = models.DecimalField(max_digits=15, decimal_places=2)
    moneda = models.ForeignKey(
        'divisas.Moneda',
        on_delete=models.PROTECT,
        related_name='facturas'
    )
    
    # Ítems de la factura (almacenados como JSON para flexibilidad)
    lineas_detalle = models.JSONField(
        default=list,
        help_text="Líneas de la factura en formato JSON"
    )
    
    # Marcas de tiempo
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField(blank=True, null=True)
    
    # Información de factura electrónica
    firma_electronica = models.TextField(blank=True)
    codigo_autoridad_fiscal = models.CharField(max_length=100, blank=True)
    
    # Almacenamiento de archivos
    archivo_pdf = models.FileField(upload_to='facturas/pdf/', blank=True, null=True)
    archivo_xml = models.FileField(upload_to='facturas/xml/', blank=True, null=True)
    
    creada_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.PROTECT,
        related_name='facturas_creadas'
    )

    class Meta:
        db_table = 'transacciones_factura'
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"Factura #{self.numero_factura} - {self.cliente.obtener_nombre_completo()}"

    def save(self, *args, **kwargs):
        """Genera el número de factura si no existe."""
        if not self.numero_factura:
            from django.utils import timezone
            cadena_fecha = timezone.now().strftime('%Y%m%d')
            ultima_factura = Factura.objects.filter(
                numero_factura__startswith=f"FAC-{cadena_fecha}"
            ).order_by('-numero_factura').first()
            
            if ultima_factura:
                ultimo_num = int(ultima_factura.numero_factura.split('-')[2])
                nuevo_num = str(ultimo_num + 1).zfill(4)
            else:
                nuevo_num = '0001'
            
            self.numero_factura = f"FAC-{cadena_fecha}-{nuevo_num}"
        
        super().save(*args, **kwargs)

    def generar_pdf(self):
        """Genera la versión en PDF de la factura."""
        # Implementación para la generación de PDF usando reportlab
        pass

    def enviar_a_autoridad_fiscal(self):
        """Envía la factura a la autoridad fiscal para su aprobación."""
        # Implementación para el envío de factura electrónica
        pass


class ComisionTransaccion(models.Model):
    """
    Modelo para el desglose de comisiones de una transacción.
    """
    transaccion = models.ForeignKey(
        Transaccion,
        on_delete=models.CASCADE,
        related_name='comisiones'
    )
    tipo_comision = models.CharField(
        max_length=50,
        choices=[
            ('CAMBIO', 'Comisión de Cambio'),
            ('PROCESAMIENTO', 'Comisión de Procesamiento'),
            ('TRANSFERENCIA', 'Comisión de Transferencia'),
            ('SERVICIO', 'Comisión de Servicio'),
        ]
    )
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    moneda = models.ForeignKey(
        'divisas.Moneda',
        on_delete=models.PROTECT
    )
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'transacciones_comision'
        verbose_name = 'Comisión'
        verbose_name_plural = 'Comisiones'

    def __str__(self):
        return f"{self.get_tipo_comision_display()} - {self.monto} {self.moneda.codigo}"