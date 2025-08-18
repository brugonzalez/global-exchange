from django.db import models
from django.utils import timezone
from decimal import Decimal


class Reporte(models.Model):
    """
    Modelo para los reportes generados.
    """
    TIPOS_REPORTE = [
        ('HISTORIAL_TRANSACCIONES', 'Historial de Transacciones'),
        ('TASAS_CAMBIO', 'Tasas de Cambio'),
    ]

    FORMATOS = [
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
    ]

    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('GENERANDO', 'Generando'),
        ('COMPLETADO', 'Completado'),
        ('FALLIDO', 'Fallido'),
    ]

    # Identificación del reporte
    nombre_reporte = models.CharField(max_length=200)
    tipo_reporte = models.CharField(max_length=30, choices=TIPOS_REPORTE)
    formato = models.CharField(max_length=10, choices=FORMATOS)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # Detalles de la solicitud
    solicitado_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.CASCADE,
        related_name='reportes_solicitados'
    )
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.CASCADE,
        related_name='reportes',
        blank=True,
        null=True,
        help_text="Cliente específico para el reporte (opcional)"
    )
    
    # Rango de fechas
    fecha_desde = models.DateTimeField()
    fecha_hasta = models.DateTimeField()
    
    # Filtros y parámetros
    filtros = models.JSONField(
        default=dict,
        help_text="Filtros aplicados al reporte"
    )
    
    # Almacenamiento de archivo
    ruta_archivo = models.FileField(
        upload_to='reportes/',
        blank=True,
        null=True
    )
    tamano_archivo = models.PositiveIntegerField(
        default=0,
        help_text="Tamaño del archivo en bytes"
    )
    
    # Detalles de generación
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateTimeField(blank=True, null=True)
    fecha_finalizacion = models.DateTimeField(blank=True, null=True)
    
    # Información de error
    mensaje_error = models.TextField(blank=True)
    
    # Control de acceso
    fecha_expiracion = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Fecha de expiración del archivo"
    )
    conteo_descargas = models.PositiveIntegerField(default=0)
    max_descargas = models.PositiveIntegerField(
        default=10,
        help_text="Número máximo de descargas permitidas"
    )

    class Meta:
        db_table = 'reportes_reporte'
        verbose_name = 'Reporte'
        verbose_name_plural = 'Reportes'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.nombre_reporte} - {self.get_tipo_reporte_display()}"

    def puede_descargar(self):
        """Verifica si el reporte se puede descargar."""
        if self.estado != 'COMPLETADO':
            return False
        if self.fecha_expiracion and timezone.now() > self.fecha_expiracion:
            return False
        if self.conteo_descargas >= self.max_descargas:
            return False
        return True

    def incrementar_conteo_descargas(self):
        """Incrementa el contador de descargas."""
        self.conteo_descargas += 1
        self.save(update_fields=['conteo_descargas'])


class MetricaPanel(models.Model):
    """
    Modelo para almacenar métricas y KPIs del panel de control.
    """
    TIPOS_METRICA = [
        ('TOTAL_TRANSACCIONES', 'Total de Transacciones'),
        ('VOLUMEN_DIARIO', 'Volumen Diario'),
        ('VOLUMEN_MENSUAL', 'Volumen Mensual'),
        ('MARGEN_GANANCIA', 'Margen de Ganancia'),
        ('CLIENTES_ACTIVOS', 'Clientes Activos'),
        ('DISTRIBUCION_MONEDA', 'Distribución por Moneda'),
        ('TRANSACCION_PROMEDIO', 'Transacción Promedio'),
        ('TASA_CONVERSION', 'Tasa de Conversión'),
    ]

    tipo_metrica = models.CharField(max_length=30, choices=TIPOS_METRICA)
    nombre_metrica = models.CharField(max_length=100)
    
    # Valores de la métrica
    valor = models.DecimalField(
        max_digits=20, 
        decimal_places=8,
        help_text="Valor principal de la métrica"
    )
    moneda = models.ForeignKey(
        'divisas.Moneda',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Moneda asociada a la métrica"
    )
    
    # Período de tiempo
    inicio_periodo = models.DateTimeField()
    fin_periodo = models.DateTimeField()
    
    # Datos adicionales
    metadata = models.JSONField(
        default=dict,
        help_text="Datos adicionales de la métrica"
    )
    
    # Marcas de tiempo
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reportes_metrica_panel'
        verbose_name = 'Métrica del Panel'
        verbose_name_plural = 'Métricas del Panel'
        ordering = ['-fecha_calculo']
        unique_together = ['tipo_metrica', 'inicio_periodo', 'fin_periodo', 'moneda']

    def __str__(self):
        return f"{self.nombre_metrica}: {self.valor}"


class PlantillaReporte(models.Model):
    """
    Modelo para las plantillas de reportes.
    """
    nombre = models.CharField(max_length=200)
    tipo_reporte = models.CharField(max_length=30, choices=Reporte.TIPOS_REPORTE)
    descripcion = models.TextField(blank=True)
    
    # Configuración de la plantilla
    formato_defecto = models.CharField(max_length=10, choices=Reporte.FORMATOS)
    filtros_defecto = models.JSONField(default=dict)
    
    # Consulta SQL o configuración de fuente de datos
    plantilla_consulta = models.TextField(
        blank=True,
        help_text="Plantilla de consulta SQL"
    )
    
    # Permisos
    es_publica = models.BooleanField(
        default=False,
        help_text="Si la plantilla está disponible para todos los usuarios"
    )
    roles_permitidos = models.JSONField(
        default=list,
        help_text="Roles que pueden usar esta plantilla"
    )
    
    creado_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.CASCADE,
        related_name='plantillas_reporte_creadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reportes_plantilla'
        verbose_name = 'Plantilla de Reporte'
        verbose_name_plural = 'Plantillas de Reporte'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ReporteProgramado(models.Model):
    """
    Modelo para reportes programados/recurrentes.
    """
    FRECUENCIAS = [
        ('DIARIO', 'Diario'),
        ('SEMANAL', 'Semanal'),
        ('MENSUAL', 'Mensual'),
        ('TRIMESTRAL', 'Trimestral'),
        ('ANUAL', 'Anual'),
    ]

    plantilla = models.ForeignKey(
        PlantillaReporte,
        on_delete=models.CASCADE,
        related_name='reportes_programados'
    )
    nombre = models.CharField(max_length=200)
    
    # Configuración de programación
    frecuencia = models.CharField(max_length=20, choices=FRECUENCIAS)
    esta_activo = models.BooleanField(default=True)
    
    # Destinatarios
    destinatarios = models.ManyToManyField(
        'cuentas.Usuario',
        related_name='reportes_programados',
        help_text="Usuarios que recibirán el reporte"
    )
    
    # Configuración de email
    asunto_email = models.CharField(max_length=200, blank=True)
    cuerpo_email = models.TextField(blank=True)
    
    # Detalles de programación
    proxima_ejecucion = models.DateTimeField()
    ultima_ejecucion = models.DateTimeField(blank=True, null=True)
    conteo_ejecuciones = models.PositiveIntegerField(default=0)
    
    creado_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.CASCADE,
        related_name='reportes_programados_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reportes_reporte_programado'
        verbose_name = 'Reporte Programado'
        verbose_name_plural = 'Reportes Programados'
        ordering = ['proxima_ejecucion']

    def __str__(self):
        return f"{self.nombre} ({self.get_frecuencia_display()})"