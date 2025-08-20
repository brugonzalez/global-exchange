from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Usuario(AbstractUser):
    """
    Modelo de Usuario personalizado que extiende el AbstractUser de Django.
    """
    email = models.EmailField(unique=True)
    nombre_completo = models.CharField(max_length=255)
    nro_telefono = models.CharField(max_length=20, blank=True, null=True)
    email_verificado = models.BooleanField(default=False)
    token_verificacion_email = models.CharField(max_length=100, blank=True, null=True)
    intentos_fallidos_login = models.PositiveIntegerField(default=0)
    cuenta_bloqueada_hasta = models.DateTimeField(blank=True, null=True)
    ultimo_cliente_seleccionado = models.ForeignKey(
        'clientes.Cliente', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        related_name='ultimos_usuarios_seleccionados'
    )
    
    # Campos para 2FA
    autenticacion_dos_factores_activa = models.BooleanField(default=False)
    tokens_respaldo = models.JSONField(default=list, blank=True)
    requerir_2fa_para_acciones_sensibles = models.BooleanField(default=True)
    
    # Sistema de roles
    roles = models.ManyToManyField('Rol', related_name='usuarios', blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'nombre_completo']

    class Meta:
        db_table = 'cuentas_usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombre_completo} ({self.email})"

    def esta_cuenta_bloqueada(self):
        """Verifica si la cuenta está actualmente bloqueada."""
        if self.cuenta_bloqueada_hasta:
            return timezone.now() < self.cuenta_bloqueada_hasta
        return False

    def restablecer_intentos_fallidos(self):
        """Restablece los intentos de inicio de sesión fallidos."""
        self.intentos_fallidos_login = 0
        self.cuenta_bloqueada_hasta = None
        self.save(update_fields=['intentos_fallidos_login', 'cuenta_bloqueada_hasta'])

    def incrementar_intentos_fallidos(self):
        """Incrementa los intentos de inicio de sesión fallidos y bloquea la cuenta si es necesario."""
        from django.conf import settings
        max_intentos = getattr(settings, 'INTENTOS_MAX_BLOQUEO_CUENTA', 5)
        duracion_bloqueo = getattr(settings, 'DURACION_BLOQUEO_CUENTA', 1800)  # 30 minutos
        
        self.intentos_fallidos_login += 1
        if self.intentos_fallidos_login >= max_intentos:
            self.cuenta_bloqueada_hasta = timezone.now() + timedelta(seconds=duracion_bloqueo)
        self.save(update_fields=['intentos_fallidos_login', 'cuenta_bloqueada_hasta'])

    def puede_operar_transacciones(self):
        """Verifica si el usuario puede realizar operaciones de compra/venta."""
        return self.clientes.exists()

    def obtener_clientes_disponibles(self):
        """Obtiene todos los clientes asociados a este usuario."""
        return self.clientes.all()

    def requiere_2fa(self, tipo_operacion='normal'):
        """Verifica si se requiere 2FA para operaciones específicas."""
        if not self.autenticacion_dos_factores_activa:
            return False
        
        operaciones_sensibles = ['transaccion', 'cambio_contrasena', 'actualizacion_configuracion']
        if tipo_operacion in operaciones_sensibles and self.requerir_2fa_para_acciones_sensibles:
            return True
        
        return False

    def generar_tokens_respaldo(self):
        """Genera tokens de respaldo para la recuperación de 2FA."""
        import secrets
        import string
        
        tokens = []
        for _ in range(10):
            token = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            tokens.append(token)
        
        self.tokens_respaldo = tokens
        self.save(update_fields=['tokens_respaldo'])
        return tokens

    def usar_token_respaldo(self, token):
        """Usa un token de respaldo para omitir la 2FA."""
        if token in self.tokens_respaldo:
            self.tokens_respaldo.remove(token)
            self.save(update_fields=['tokens_respaldo'])
            return True
        return False

    def obtener_roles(self):
        """Obtiene todos los roles asignados a este usuario."""
        return self.roles.all()

    def obtener_permisos(self):
        """Obtiene todos los permisos del usuario basados en sus roles."""
        permisos = set()
        for rol in self.roles.all():
            permisos.update(rol.obtener_permisos())
        return list(permisos)

    def tiene_permiso(self, codename_permiso):
        """Verifica si el usuario tiene un permiso específico."""
        return any(
            permiso.codename == codename_permiso 
            for permiso in self.obtener_permisos()
        )

    def tiene_rol(self, nombre_rol):
        """Verifica si el usuario tiene un rol específico."""
        return self.roles.filter(nombre_rol=nombre_rol).exists()

    def es_administrador(self):
        """Verifica si el usuario tiene rol de administrador."""
        return self.tiene_rol('Administrador') or self.is_superuser

    def es_cajero(self):
        """Verifica si el usuario tiene rol de cajero."""
        return self.tiene_rol('Cajero')

    def es_usuario_regular(self):
        """Verifica si el usuario tiene rol de usuario regular."""
        return self.tiene_rol('Usuario')

    def es_visitante(self):
        """Verifica si el usuario tiene rol de visitante."""
        return self.tiene_rol('Visitante')


class VerificacionEmail(models.Model):
    """
    Modelo para manejar los tokens de verificación de email.
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    utilizado = models.BooleanField(default=False)

    class Meta:
        db_table = 'cuentas_verificacion_email'
        verbose_name = 'Verificación de Email'
        verbose_name_plural = 'Verificaciones de Email'

    def ha_expirado(self):
        """Verifica si el token de verificación ha expirado (24 horas)."""
        return timezone.now() > self.fecha_creacion + timedelta(hours=24)


class RestablecimientoContrasena(models.Model):
    """
    Modelo para manejar los tokens de restablecimiento de contraseña.
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    utilizado = models.BooleanField(default=False)

    class Meta:
        db_table = 'cuentas_restablecimiento_contrasena'
        verbose_name = 'Recuperación de Contraseña'
        verbose_name_plural = 'Recuperaciones de Contraseña'

    def ha_expirado(self):
        """Verifica si el token de restablecimiento ha expirado (1 hora)."""
        return timezone.now() > self.fecha_creacion + timedelta(hours=1)


class ConfiguracionDosFactoresUsuario(models.Model):
    """
    Modelo para almacenar la configuración 2FA específica del usuario.
    """
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='configuracion_2fa')
    
    # Preferencias 2FA
    sms_activo = models.BooleanField(default=False)
    email_activo = models.BooleanField(default=False)
    numero_telefono = models.CharField(max_length=20, blank=True)
    
    # Configuración de seguridad
    requerir_para_login = models.BooleanField(default=True)
    requerir_para_transacciones = models.BooleanField(default=True)
    requerir_para_cambio_contrasena = models.BooleanField(default=True)
    requerir_para_cambio_configuracion = models.BooleanField(default=True)
    
    # Opciones de recuperación
    email_recuperacion = models.EmailField(blank=True)
    telefono_recuperacion = models.CharField(max_length=20, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cuentas_usuario_configuracion_2fa'
        verbose_name = 'Configuración 2FA'
        verbose_name_plural = 'Configuraciones 2FA'

    def __str__(self):
        return f"Configuración 2FA para {self.usuario.username}"


class Permiso(models.Model):
    """
    Modelo para permisos del sistema.
    """
    codename = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cuentas_permiso'
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'
        ordering = ['descripcion']

    def __str__(self):
        return self.descripcion


class Rol(models.Model):
    """
    Modelo para roles del sistema.
    """
    nombre_rol = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    permisos = models.ManyToManyField(Permiso, related_name='roles', blank=True)
    es_sistema = models.BooleanField(default=False, help_text="Rol del sistema que no se puede eliminar")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cuentas_rol'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['nombre_rol']

    def __str__(self):
        return self.nombre_rol

    def obtener_permisos(self):
        """Obtiene todos los permisos asociados a este rol."""
        return self.permisos.all()


class RegistroAuditoria(models.Model):
    """
    Modelo para almacenar registros de auditoría para seguridad y seguimiento.
    """
    TIPOS_ACCION = [
        ('LOGIN', 'Inicio de Sesión'),
        ('LOGOUT', 'Cierre de Sesión'),
        ('FAILED_LOGIN', 'Intento de Login Fallido'),
        ('ACCOUNT_LOCKED', 'Cuenta Bloqueada'),
        ('PASSWORD_CHANGE', 'Cambio de Contraseña'),
        ('EMAIL_VERIFICATION', 'Verificación de Email'),
        ('PROFILE_UPDATE', 'Actualización de Perfil'),
        ('TRANSACTION_CREATE', 'Transacción Creada'),
        ('TRANSACTION_UPDATE', 'Transacción Actualizada'),
        ('RATE_UPDATE', 'Actualización de Tasa'),
        ('CLIENT_CHANGE', 'Cambio de Cliente'),
        ('2FA_SETUP', 'Configuración 2FA'),
        ('2FA_DISABLE', 'Desactivación 2FA'),
        ('2FA_VERIFY', 'Verificación 2FA'),
        ('BACKUP_TOKEN_USED', 'Token de Respaldo Usado'),
        ('ROLE_ASSIGNED', 'Rol Asignado'),
        ('ROLE_REMOVED', 'Rol Removido'),
        ('ROLE_CREATED', 'Rol Creado'),
        ('ROLE_UPDATED', 'Rol Actualizado'),
        ('ROLE_DELETED', 'Rol Eliminado'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, blank=True, null=True)
    accion = models.CharField(max_length=50, choices=TIPOS_ACCION)
    descripcion = models.TextField()
    direccion_ip = models.GenericIPAddressField(blank=True, null=True)
    agente_usuario = models.TextField(blank=True, null=True)
    marca_de_tiempo = models.DateTimeField(auto_now_add=True)
    datos_adicionales = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'cuentas_registro_auditoria'
        verbose_name = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'
        ordering = ['-marca_de_tiempo']

    def __str__(self):
        nombre_usuario = self.usuario.username if self.usuario else 'Usuario Anónimo'
        return f"{nombre_usuario} - {self.get_accion_display()} - {self.marca_de_tiempo}"