"""
Modelos de la app de cuentas.

Este módulo define el modelo de usuario personalizado y entidades relacionadas
para verificación de email, recuperación de contraseña, configuración de 2FA,
roles, permisos y registro de auditoría.

Clases principales
------------------
- :class:`Usuario`: Extiende ``AbstractUser`` y usa el email como identificador.
- :class:`VerificacionEmail`: Tokens de verificación de correo.
- :class:`RestablecimientoContrasena`: Tokens de restablecimiento de contraseña.
- :class:`ConfiguracionDosFactoresUsuario`: Preferencias y recuperación de 2FA.
- :class:`Permiso`: Permisos de negocio (no confundir con los de Django).
- :class:`Rol`: Agrupa permisos de negocio y se asigna a usuarios.
- :class:`RegistroAuditoria`: Bitácora de eventos relevantes de seguridad.

Notas
-----
- Este módulo asume que ``settings.AUTH_USER_MODEL`` apunta a :class:`Usuario`.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta

from global_exchange import settings


class Usuario(AbstractUser):
    """Modelo de usuario personalizado.

    Extiende :class:`django.contrib.auth.models.AbstractUser` y usa
    el email como identificador principal (``USERNAME_FIELD = 'email'``).
    Incluye campos para 2FA, bloqueo/desbloqueo de cuenta, relación con clientes
    y gestión de roles y permisos.

    Attributes
    ----------
    email : EmailField
        Identificador único para autenticación.
    nombre_completo : CharField
        Nombre completo mostrado en UI y reportes.
    autenticacion_dos_factores_activa : BooleanField
        Indica si el usuario tiene 2FA habilitado.
    roles : ManyToManyField[:class:`Rol`]
        Conjunto de roles asignados al usuario.
    nro_telefono : CharField
        Número de teléfono del usuario.
    email_verificado : BooleanField
        Indica si el email del usuario ha sido verificado.
    token_verificacion_email : CharField
        Token de verificación de email.
    intentos_fallidos_login : PositiveIntegerField
        Contador de intentos fallidos de inicio de sesión.
    cuenta_bloqueada_hasta : DateTimeField
        Fecha y hora hasta la cual la cuenta está bloqueada.
    ultimo_cliente_seleccionado : ForeignKey[:class:`Cliente`]
        Último cliente seleccionado por el usuario en UI si aplica.
    tokens_respaldo : JSONField
        Lista de tokens de respaldo para 2FA.
    autenticacion_dos_factores_activa : BooleanField
        Indica si la autenticación de dos factores está habilitada.
    requerir_2fa_para_acciones_sensibles : BooleanField
        Indica si se requiere 2FA para acciones sensibles.
    fecha_creacion : DateTimeField
        Fecha y hora de creación del usuario.
    fecha_actualizacion : DateTimeField
        Fecha y hora de la última actualización del usuario.

    Notes
    -----
    - ``REQUIRED_FIELDS`` incluye ``username`` y ``nombre_completo``.
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
        """Representación legible del usuario.

        Returns
        -------
        str
            Cadena con el formato "<nombre_completo> (<email>)".
        """
        return f"{self.nombre_completo} ({self.email})"

    def esta_cuenta_bloqueada(self):
        """
        Indica si la cuenta está actualmente bloqueada.

        Returns
        -------
        bool
            ``True`` si ``cuenta_bloqueada_hasta`` es futura; de lo contrario ``False``.
        """
        if self.cuenta_bloqueada_hasta:
            return timezone.now() < self.cuenta_bloqueada_hasta
        return False

    def restablecer_intentos_fallidos(self):
        """
        Restablece el contador de intentos fallidos a 0 y desbloquea la cuenta.

        Returns
        -------
        None
        """
        self.intentos_fallidos_login = 0
        self.cuenta_bloqueada_hasta = None
        self.is_active = True
        self.save(update_fields=['intentos_fallidos_login', 'cuenta_bloqueada_hasta', 'is_active'])

    def incrementar_intentos_fallidos(self):
        """Aumenta intentos fallidos y bloquea la cuenta si supera el umbral.

        Luego de un intento fallido de inicio de sesión incrementa ``intentos_fallidos_login`` 
        y, si supera el máximo, bloquea la cuenta (define ``cuenta_bloqueada_hasta`` y ``is_active = False``).

        Lee de ``settings``
        -------------------------
        - ``INTENTOS_MAX_BLOQUEO_CUENTA`` (por defecto 5)
        - ``DURACION_BLOQUEO_CUENTA`` en segundos (por defecto 1800)
        """
        from django.conf import settings
        max_intentos = getattr(settings, 'INTENTOS_MAX_BLOQUEO_CUENTA', 5)
        duracion_bloqueo = getattr(settings, 'DURACION_BLOQUEO_CUENTA', 1800)  # 30 minutos
        
        self.intentos_fallidos_login += 1
        if self.intentos_fallidos_login >= max_intentos:
            self.cuenta_bloqueada_hasta = timezone.now() + timedelta(seconds=duracion_bloqueo)
            self.is_active = False
        self.save(update_fields=['intentos_fallidos_login', 'cuenta_bloqueada_hasta', 'is_active'])

    def puede_operar_transacciones(self):
        """Indica si el usuario tiene clientes asociados para operar.

        Returns
        -----------
        bool
            ``True`` si el usuario está asociado a uno o más clientes.
        """
        return self.clientes.exists()

    def obtener_clientes_disponibles(self):
        """
        Devuelve todos los clientes asociados al usuario.

        Returns
        -------
        QuerySet
            Conjunto de ``Cliente`` asociados al usuario.
        """
        return self.clientes.all()

    def requiere_2fa(self, tipo_operacion='normal'):
        """
        Verifica si se requiere 2FA para operaciones específicas:
            - transacciones
            - cambios de contraseña
            - actualizaciones de configuración
        Parameters
        ------------
        tipo_operacion : str
            Tipo de operación a verificar.

        Returns
        -------
        bool
            ``True`` si se requiere 2FA, de lo contrario ``False``.
        """
        if not self.autenticacion_dos_factores_activa:
            return False
        
        operaciones_sensibles = ['transaccion', 'cambio_contrasena', 'actualizacion_configuracion']
        if tipo_operacion in operaciones_sensibles and self.requerir_2fa_para_acciones_sensibles:
            return True
        
        return False

    def generar_tokens_respaldo(self):
        """
        Genera tokens de respaldo para la recuperación de 2FA.

        Returns
        -------
        list[str]
            Lista con 10 tokens (8 caracteres alfanuméricos cada uno).
        
        Notes
        -----
        - Reemplaza la lista previa de ``tokens_respaldo``.
        - útil para recuperar acceso si se pierde el 2FA principal
        """
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
        """
        Consume un token de respaldo válido para omitir 2FA una vez.

        Parameters
        ----------
        token : str
           Token a validar y usar.

        Returns
        -------
        bool
            ``True`` si el token existía y fue removido; ``False`` en caso contrario.
        """
        if token in self.tokens_respaldo:
            self.tokens_respaldo.remove(token)
            self.save(update_fields=['tokens_respaldo'])
            return True
        return False

    def obtener_roles(self):
        """
        Devuelve los roles asignados al usuario.

        Returns
        -------
        QuerySet[Rol]
            Roles asignados al usuario.
        """
        return self.roles.all()

    def obtener_permisos(self):
        """
        Obtiene todos los permisos del usuario basados en sus roles.

        Returns
        -------
        list[:class:`Permiso`]
            Permisos asignados al usuario sin duplicados.
        """
        permisos = set()
        for rol in self.roles.all():
            permisos.update(rol.obtener_permisos())
        return list(permisos)

    def tiene_permiso(self, codename_permiso):
        """
        Verifica si el usuario tiene un permiso específico.

        Parameters
        ----------
        codename_permiso : str
            Código del permiso a verificar.

        Returns
        -------
        bool
            ``True`` si el usuario tiene el permiso, ``False`` en caso contrario.
        """
        return any(
            permiso.codename == codename_permiso 
            for permiso in self.obtener_permisos()
        )

    def tiene_rol(self, nombre_rol):
        """
        Verifica si el usuario tiene un rol específico.

        Parameters
        ----------
        nombre_rol : str
            Nombre del rol a verificar.

        Returns
        -------
        bool
            ``True`` si el usuario tiene el rol, ``False`` en caso contrario.
        """
        return self.roles.filter(nombre_rol=nombre_rol).exists()

    def es_administrador(self):
        """
        Verifica si el usuario tiene rol de administrador.

        Returns
        -------
        bool
            ``True`` si el usuario tiene rol de administrador, ``False`` en caso contrario.
        """
        return self.tiene_rol('Administrador') or self.is_superuser

    def es_cajero(self):
        """
        Verifica si el usuario tiene rol de cajero.

        Returns
        -------
        bool
            ``True`` si el usuario tiene rol de cajero, ``False`` en caso contrario.
        """
        return self.tiene_rol('Cajero')

    def es_usuario_regular(self):
        """
        Verifica si el usuario tiene rol de usuario regular.

        Returns
        -------
        bool
            ``True`` si el usuario tiene rol de **Usuario**, ``False`` en caso contrario.
        """
        return self.tiene_rol('Usuario')

    def es_visitante(self):
        """
        Verifica si el usuario tiene rol de visitante.

        Returns
        -------
        bool
            ``True`` si el usuario tiene rol de visitante, ``False`` en caso contrario.
        """
        return self.tiene_rol('Visitante')

    def bloquear(self, ejecutor):
        """
        Bloquea la cuenta y registra en auditoría

        Establece la cuenta como inactiva por un período configurado (1800 segundos por defecto)

        Parameters
        ----------
        ejecutor : Usuario
            El usuario que ejecuta la acción de bloqueo.

        Returns
        -------
        None

        Notes
        -----
        - Usa ``settings.DURACION_BLOQUEO_CUENTA`` para configurar la duración del bloqueo.
        - Crea registro en auditoría.
        """
        #duracion_bloqueo = getattr(settings, 'DURACION_BLOQUEO_CUENTA', 1800)  # 30 minutos
        duracion_bloqueo = Configuracion.obtener_valor('DURACION_BLOQUEO_CUENTA', valor_por_defecto=1800)  # en segundos
        if self.is_active:
            self.is_active = False
            self.cuenta_bloqueada_hasta = timezone.now() + timedelta(seconds=duracion_bloqueo)
            self.save(update_fields=['is_active', 'cuenta_bloqueada_hasta'])

            RegistroAuditoria.objects.create(
                usuario=ejecutor,
                accion='USER_BLOCKED',
                descripcion=f'Bloqueó al usuario: {self.email}',
                #direccion_ip='N/A',   si se pasa desde la vista, se puede usar request.META.get('REMOTE_ADDR')
                agente_usuario='N/A',
                datos_adicionales={
                    'usuario_id': self.id,
                    'estado_anterior': True,
                    'estado_nuevo': False
                }
            )

    def desbloquear(self, ejecutor):
        """
        Desbloquea la cuenta y registra en auditoría

        Establece la cuenta como activa.

        Parameters
        ----------
        ejecutor : Usuario
            El usuario que ejecuta la acción de desbloqueo.

        Returns
        -------
        None

        Notes
        -----
        - Crea registro en :class:`RegistroAuditoria`.
        - Restaura ``is_active`` a ``True`` y limpia ``cuenta_bloqueada_hasta``
        """
        if not self.is_active:
            self.is_active = True
            self.cuenta_bloqueada_hasta = None
            self.save(update_fields=['is_active', 'cuenta_bloqueada_hasta'])

            RegistroAuditoria.objects.create(
                usuario=ejecutor,
                accion='USER_UNBLOCKED',
                descripcion=f'Desbloqueó al usuario: {self.email}',
                #direccion_ip='N/A',
                agente_usuario='N/A',
                datos_adicionales={
                    'usuario_id': self.id,
                    'estado_anterior': False,
                    'estado_nuevo': True
                }
            )


class VerificacionEmail(models.Model):
    """
    Modelo para manejar los tokens de verificación de correo electrónico.

    Cada registro guarda un token único vinculado al usuario, que se utiliza para
    confirmar la validez del email durante el registro.

    Attributes
    ----------
    usuario : ForeignKey[:class:`Usuario`]
        El usuario asociado a este token de verificación.
    token : CharField
        El token de verificación único.
    fecha_creacion : DateTimeField
        La fecha y hora en que se creó el token.
    utilizado : BooleanField
        Indica si el token ha sido utilizado.

    Notes
    -----
    - Los tokens expiran automáticamente después de 24 horas de su creación.
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
        """
        Verifica si el token de verificación ya no es válido. (duracion: 24 horas)

        Returns
        -------
        bool
             ``True`` si el token ha expirado, ``False`` en caso contrario.
        """
        return timezone.now() > self.fecha_creacion + timedelta(hours=24)


class RestablecimientoContrasena(models.Model):
    """
    Modelo para manejar los tokens de restablecimiento de contraseña.
    Cada registro asocia un token único a un usuario para recuperación de acceso.

    Attributes
    ----------
    usuario : ForeignKey[:class:`Usuario`]
        El usuario al que pertenece el token
    token : CharField
        El token de restablecimiento único.
    fecha_creacion : DateTimeField
        La fecha y hora en que se creó el token.
    utilizado : BooleanField
        Indica si el token ya se usó

    Notes
    -----
    - Los tokens expiran automáticamente después de 1 hora de su creación.
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
        """
        Verifica si el token de restablecimiento ha expirado (1 hora).

        Returns
        -------
        bool
            ``True`` si el token ha expirado, ``False`` en caso contrario.
        """
        return timezone.now() > self.fecha_creacion + timedelta(hours=1)


class ConfiguracionDosFactoresUsuario(models.Model):
    """
    Modelo de preferencias y opciones de recuperación de 2FA por usuario.

    Define qué métodos de autenticacion de dos factores están habilitados,
    en qué situaciones se exigen y qué canales de respaldo se pueden usar
    para recuperar el acceso en caso de pérdida del 2FA principal

    Attributes
    ----------
    usuario : ForeignKey[:class:`Usuario`]
        El usuario al que pertenece la configuracion
    sms_activo : BooleanField
        Indica si la verificación por SMS está activa.
    email_activo : BooleanField
        Indica si la verificación por email está activa.
    requerir_para_login : BooleanField
        Indica si se requiere 2FA para iniciar sesión.
    requerir_para_transacciones : BooleanField
        Indica si se requiere 2FA para transacciones.
    requerir_para_cambio_contrasena : BooleanField
        Indica si se requiere 2FA para el cambio de contraseña.
    requerir_para_cambio_configuracion : BooleanField
        Indica si se requiere 2FA para el cambio en la configuración.
    email_recuperacion : EmailField
        El email alternativo para recuperación de cuenta.
    telefono_recuperacion : CharField
        El teléfono de recuperación de cuenta.
    fecha_creacion : DateTimeField
        La fecha de creación de la configuración 2FA.
    fecha_actualizacion : DateTimeField
        La fecha de última actualización de esta configuracion.

    Notes
    -----
    - Los campos de recuperación son opcionales.
    - Se crea y asocia automáticamente a cada usuario cuando habilita 2FA.
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
        """
        Devuelve representación legible del objeto.

        Returns
        -------
        str
            Texto con el username del usuario al que corresponde la configuracion.
        """
        return f"Configuración 2FA para {self.usuario.username}"


class Permiso(models.Model):
    """
    Modelo que representa un permiso de operación del sistema.

    Attributes
    ----------
    codename : CharField
        El nombre único del permiso.
    descripcion : CharField
        Una descripción corta del permiso.
    fecha_creacion : DateTimeField
        La fecha y hora en que se creó el permiso.
    fecha_actualizacion : datetime
        La fecha y hora de la última actualización del permiso.
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
        """
        Devuelve la descripción del permiso como representación en texto.

        Returns
        -------
        str
            Texto con la descripción del permiso.
        """
        return self.descripcion


class Rol(models.Model):
    """
    Modelo para roles del sistema.

    Un rol de sistema agrupa permisos del negocio.
    Un rol se compone de uno o más :class:`Permiso` y se asigna a uno o más :class:`Usuario`.

    Attributes
    ----------
    nombre_rol : CharField
        El nombre del rol.
    descripcion : TextField
        Una descripción del rol.
    permisos : ManyToManyField[:class:`Permiso`]
        Los permisos asociados a este rol.
    es_sistema : BooleanField
        Indica si el rol es un rol del sistema.
    fecha_creacion : DateTimeField
        La fecha y hora en que se creó el rol.
    fecha_actualizacion : DateTimeField
        La fecha y hora de la última actualización del rol.
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
        """
        Devuelve el nombre del rol como representación en texto.

        Returns
        -------
        str
            El nombre del rol.
        """
        return self.nombre_rol

    def obtener_permisos(self):
        """
        Devuelve todos los permisos asociados al rol.

        Returns
        -------
        QuerySet[`Permiso`]
            Conjunto de permisos asociados al rol.
        """
        return self.permisos.all()


class RegistroAuditoria(models.Model):
    """
    Modelo para guardar registros de auditoría para seguridad y seguimiento.
    Guarda quién, qué, cuándo y desde dónde se ejecutó una acción relevante.

    Choices
    -------
    TIPOS_ACCION :
        Lista de códigos de acción (p.ej. ``LOGIN``, ``PASSWORD_CHANGE``,
        ``USER_BLOCKED``) y sus descripciones legibles

    Attributes
    ----------
    usuario : ForeignKey[:class:`Usuario`]
        El usuario que realizó la acción.
    accion : CharField
        El tipo de acción realizada. (de la lista TIPOS_ACCION)
    descripcion : TextField
        Una descripción de la acción realizada.
    direccion_ip : GenericIPAddressField
        La dirección IP desde la cual se realizó la acción.
    agente_usuario : TextField
        User-Agent del navegador/dispositivo que realizó la acción.
    marca_de_tiempo : DateTimeField
        La marca de tiempo de la acción.
    datos_adicionales : JSONField
        Datos adicionales sobre la acción realizada.
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
        ('MEDIO_PAGO_CREATE', 'Medio de pago Asociado'),
        ('MEDIO_PAGO_DELETED', 'Medio de pago desvinculado'),
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
        """
        Representa la información del registro de auditoría como una cadena.
        Returns
        -------
        str
            Información del registro de auditoría.
        """
        nombre_usuario = self.usuario.username if self.usuario else 'Usuario Anónimo'
        return f"{nombre_usuario} - {self.get_accion_display()} - {self.marca_de_tiempo}"
    


class Configuracion (models.Model):
    """
    Modelo para almacenar configuraciones del sistema.
    Permite gestionar parámetros configurables de la aplicación.
    """
    TIPOS_VALOR = [
        ('TEXT', 'Texto'),
        ('NUMBER', 'Número'),
        ('BOOLEAN', 'Booleano'),
        ('EMAIL', 'Email'),
        ('URL', 'URL'),
        ('MONTO', 'Monto'),
    ]

    clave = models.CharField(max_length=50, unique=True)
    valor = models.TextField()  # Cambiado a TextField para valores largos
    tipo_valor = models.CharField(max_length=10, choices=TIPOS_VALOR, default='TEXT')
    descripcion = models.CharField(max_length=255, blank=True)
    categoria = models.CharField(max_length=50, default='General')
    es_editable = models.BooleanField(default=True,
                                      help_text="Si la configuración puede ser editada por el usuario")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cuentas_configuracion'
        verbose_name = 'Configuración'
        verbose_name_plural = 'Configuraciones'
        ordering = ['categoria', 'clave']

    def __str__(self):
        return f"{self.clave}: {self.valor}"

    @staticmethod
    def obtener_valor(clave, valor_por_defecto=None):
        """Obtiene el valor de una configuración por su clave."""
        try:
            config = Configuracion.objects.get(clave=clave)
            return config.convertir_valor()
        except Configuracion.DoesNotExist:
            return valor_por_defecto

    @staticmethod
    def establecer_valor(clave, valor, tipo_valor='TEXT', descripcion='', categoria='General'):
        """Establece o actualiza el valor de una configuración."""
        config, creado = Configuracion.objects.get_or_create(
            clave=clave,
            defaults={
                'valor': str(valor),
                'tipo_valor': tipo_valor,
                'descripcion': descripcion,
                'categoria': categoria
            }
        )
        if not creado:
            config.valor = str(valor)
            config.save()
        return config

    def convertir_valor(self):
        """Convierte el valor string al tipo apropiado según tipo_valor."""
        if self.tipo_valor == 'NUMBER':
            try:
                return int(self.valor) if '.' not in self.valor else float(self.valor)
            except ValueError:
                return 0
        elif self.tipo_valor == 'BOOLEAN':
            return self.valor.lower() in ['true', '1', 'yes', 'on']
        else:
            return self.valor
