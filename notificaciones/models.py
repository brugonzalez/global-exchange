from django.db import models
from django.utils import timezone


class PlantillaNotificacion(models.Model):
    """
    Modelo para las plantillas de notificación.
    """
    TIPOS_PLANTILLA = [
        ('EMAIL_VERIFICATION', 'Verificación de Email'),
        ('PASSWORD_RESET', 'Recuperación de Contraseña'),
        ('TRANSACTION_CREATED', 'Transacción Creada'),
        ('TRANSACTION_COMPLETED', 'Transacción Completada'),
        ('TRANSACTION_CANCELLED', 'Transacción Cancelada'),
        ('RATE_ALERT', 'Alerta de Tasa'),
        ('ACCOUNT_LOCKED', 'Cuenta Bloqueada'),
        ('LOGIN_NOTIFICATION', 'Notificación de Login'),
        ('INVOICE_GENERATED', 'Factura Generada'),
        ('SYSTEM_MAINTENANCE', 'Mantenimiento del Sistema'),
    ]

    nombre = models.CharField(max_length=100)
    tipo_plantilla = models.CharField(max_length=30, choices=TIPOS_PLANTILLA, unique=True)
    
    # Campos de plantilla de email
    asunto_email = models.CharField(max_length=200)
    cuerpo_email_html = models.TextField(help_text="Cuerpo del email en HTML")
    cuerpo_email_texto = models.TextField(help_text="Cuerpo del email en texto plano")
    
    # Campos de plantilla de SMS (para uso futuro)
    cuerpo_sms = models.CharField(max_length=160, blank=True)
    
    # Campos de notificación push (para uso futuro)
    titulo_push = models.CharField(max_length=100, blank=True)
    cuerpo_push = models.CharField(max_length=200, blank=True)
    
    # Configuración
    esta_activa = models.BooleanField(default=True)
    variables = models.JSONField(
        default=list,
        help_text="Variables disponibles para la plantilla"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notificaciones_plantilla'
        verbose_name = 'Plantilla de Notificación'
        verbose_name_plural = 'Plantillas de Notificación'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_plantilla_display()})"


class Notificacion(models.Model):
    """
    Modelo para almacenar las notificaciones enviadas a los usuarios.
    """
    TIPOS_NOTIFICACION = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('PUSH', 'Push'),
        ('IN_APP', 'En la Aplicación'),
    ]

    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('ENVIADO', 'Enviado'),
        ('ENTREGADO', 'Entregado'),
        ('FALLIDO', 'Fallido'),
        ('LEIDO', 'Leído'),
    ]

    # Información del destinatario
    usuario = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    
    # Detalles de la notificación
    tipo_notificacion = models.CharField(max_length=20, choices=TIPOS_NOTIFICACION)
    plantilla = models.ForeignKey(
        PlantillaNotificacion,
        on_delete=models.CASCADE,
        related_name='notificaciones',
        blank=True,
        null=True
    )
    
    # Contenido
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    
    # Seguimiento de estado
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # Detalles de entrega
    email_destinatario = models.EmailField(blank=True)
    telefono_destinatario = models.CharField(max_length=20, blank=True)
    
    # Metadatos
    datos_contexto = models.JSONField(
        default=dict,
        help_text="Datos adicionales para la plantilla"
    )
    
    # Marcas de tiempo
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(blank=True, null=True)
    fecha_entrega = models.DateTimeField(blank=True, null=True)
    fecha_lectura = models.DateTimeField(blank=True, null=True)
    
    # Información de error
    mensaje_error = models.TextField(blank=True)
    conteo_reintentos = models.PositiveIntegerField(default=0)
    max_reintentos = models.PositiveIntegerField(default=3)

    class Meta:
        db_table = 'notificaciones_notificacion'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.asunto} - {self.usuario.email} ({self.get_estado_display()})"

    def marcar_como_leida(self):
        """Marca la notificación como leída."""
        if self.estado in ['ENVIADO', 'ENTREGADO']:
            self.estado = 'LEIDO'
            self.fecha_lectura = timezone.now()
            self.save(update_fields=['estado', 'fecha_lectura'])

    def puede_reintentar(self):
        """Verifica si la notificación se puede reintentar."""
        return self.estado == 'FALLIDO' and self.conteo_reintentos < self.max_reintentos


class PreferenciaNotificacion(models.Model):
    """
    Modelo para las preferencias de notificación del usuario.
    """
    usuario = models.OneToOneField(
        'cuentas.Usuario',
        on_delete=models.CASCADE,
        related_name='preferencias_notificacion'
    )
    
    # Preferencias de email
    email_actualizaciones_transaccion = models.BooleanField(default=True)
    email_alertas_tasa = models.BooleanField(default=True)
    email_alertas_seguridad = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=False)
    email_notificaciones_sistema = models.BooleanField(default=True)
    
    # Preferencias de SMS (para uso futuro)
    sms_actualizaciones_transaccion = models.BooleanField(default=False)
    sms_alertas_tasa = models.BooleanField(default=False)
    sms_alertas_seguridad = models.BooleanField(default=True)
    
    # Preferencias de notificación push (para uso futuro)
    push_actualizaciones_transaccion = models.BooleanField(default=True)
    push_alertas_tasa = models.BooleanField(default=True)
    push_alertas_seguridad = models.BooleanField(default=True)
    
    # Preferencias generales
    frecuencia_notificacion = models.CharField(
        max_length=20,
        choices=[
            ('IMMEDIATE', 'Inmediato'),
            ('DAILY', 'Diario'),
            ('WEEKLY', 'Semanal'),
            ('NEVER', 'Nunca'),
        ],
        default='IMMEDIATE'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notificaciones_preferencia'
        verbose_name = 'Preferencia de Notificación'
        verbose_name_plural = 'Preferencias de Notificación'

    def __str__(self):
        return f"Preferencias de {self.usuario.nombre_completo}"


class TicketSoporte(models.Model):
    """
    Modelo para tickets de soporte.
    """
    ESTADOS = [
        ('ABIERTO', 'Abierto'),
        ('EN_PROGRESO', 'En Progreso'),
        ('PENDIENTE_USUARIO', 'Pendiente Usuario'),
        ('RESUELTO', 'Resuelto'),
        ('CERRADO', 'Cerrado'),
    ]

    PRIORIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    CATEGORIAS = [
        ('TECNICO', 'Técnico'),
        ('CUENTA', 'Cuenta'),
        ('TRANSACCION', 'Transacción'),
        ('FACTURACION', 'Facturación'),
        ('GENERAL', 'General'),
        ('SUGERENCIA', 'Sugerencia'),
    ]

    # Identificación del ticket
    numero_ticket = models.CharField(max_length=20, unique=True, blank=True)
    
    # Información del usuario
    usuario = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.CASCADE,
        related_name='tickets_soporte',
        blank=True,
        null=True
    )
    email_usuario = models.EmailField()
    nombre_usuario = models.CharField(max_length=200)
    
    # Detalles del ticket
    asunto = models.CharField(max_length=200)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    prioridad = models.CharField(max_length=20, choices=PRIORIDADES, default='MEDIA')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ABIERTO')
    
    # Asignación
    asignado_a = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        related_name='tickets_asignados',
        blank=True,
        null=True
    )
    
    # Resolución
    resolucion = models.TextField(blank=True)
    fecha_resolucion = models.DateTimeField(blank=True, null=True)
    resuelto_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        related_name='tickets_resueltos',
        blank=True,
        null=True
    )
    
    # Marcas de tiempo
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Información adicional
    adjuntos = models.JSONField(
        default=list,
        help_text="Lista de archivos adjuntos"
    )

    class Meta:
        db_table = 'notificaciones_ticket_soporte'
        verbose_name = 'Ticket de Soporte'
        verbose_name_plural = 'Tickets de Soporte'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"#{self.numero_ticket} - {self.asunto}"

    def save(self, *args, **kwargs):
        """Genera el número de ticket si no existe."""
        if not self.numero_ticket:
            ultimo_ticket = TicketSoporte.objects.order_by('-id').first()
            if ultimo_ticket and ultimo_ticket.numero_ticket:
                ultimo_num = int(ultimo_ticket.numero_ticket.split('-')[1])
                nuevo_num = str(ultimo_num + 1).zfill(6)
            else:
                nuevo_num = '000001'
            
            self.numero_ticket = f"SOP-{nuevo_num}"
        
        super().save(*args, **kwargs)


class MensajeTicket(models.Model):
    """
    Modelo para mensajes/respuestas de tickets de soporte.
    """
    ticket = models.ForeignKey(
        TicketSoporte,
        on_delete=models.CASCADE,
        related_name='mensajes'
    )
    autor = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.CASCADE,
        related_name='mensajes_ticket'
    )
    mensaje = models.TextField()
    es_interno = models.BooleanField(
        default=False,
        help_text="Mensaje interno (no visible para el usuario)"
    )
    adjuntos = models.JSONField(
        default=list,
        help_text="Archivos adjuntos al mensaje"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificaciones_mensaje_ticket'
        verbose_name = 'Mensaje de Ticket'
        verbose_name_plural = 'Mensajes de Ticket'
        ordering = ['fecha_creacion']

    def __str__(self):
        return f"Mensaje de {self.autor.nombre_completo} en {self.ticket.numero_ticket}"