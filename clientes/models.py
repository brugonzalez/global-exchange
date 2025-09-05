"""
Módulo de gestión de clientes para Global Exchange.

Contiene los modelos y funciones relacionados con la administración de clientes,
incluyendo datos personales, preferencias y relaciones con cuentas de usuario
"""

from django.db import models
from django.core.validators import RegexValidator
from decimal import Decimal


class CategoriaCliente(models.Model):
    """
    Modelo para las categorías de clientes.

    Define diferentes categorías de clientes con límites de transacción, márgenes preferenciales y niveles de prioridad específicos.

    Attributes
    ----------
    nombre : CharField
        Tipo de categoría (Minorista, Corporativo, VIP).
    descripcion : TextField
        Descripción de la categoría.
    limite_transaccion_diario : DecimalField
        Límite diario de transacciones.
    limite_transaccion_mensual : DecimalField
        Límite mensual de transacciones.
    margen_tasa_preferencial : DecimalField
        Margen preferencial de tasa de cambio.
    fecha_creacion : DateTimeField
        Fecha de creación del registro.
    fecha_actualizacion : DateTimeField
        Fecha de última actualización del registro.
    """
    TIPOS_CATEGORIA = [
        ('RETAIL', 'Minorista'),
        ('CORPORATE', 'Corporativo'),
        ('VIP', 'VIP'),
    ]

    nombre = models.CharField(max_length=50, choices=TIPOS_CATEGORIA, unique=True)
    descripcion = models.TextField(blank=True)
    limite_transaccion_diario = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('10000.00'),
        help_text="Límite diario de transacciones"
    )
    limite_transaccion_mensual = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('100000.00'),
        help_text="Límite mensual de transacciones"
    )
    margen_tasa_preferencial = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0100'),
        help_text="Margen preferencial de tasa de cambio (porcentaje)"
    )
    nivel_prioridad = models.PositiveIntegerField(
        default=1,
        help_text="Nivel de prioridad (1=más alta, 5=más baja)"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clientes_categoria'
        verbose_name = 'Categoría de Cliente'
        verbose_name_plural = 'Categorías de Cliente'
        ordering = ['nivel_prioridad', 'nombre']

    def __str__(self):
        """
        Representación en cadena de la categoría de cliente.

        Returns
        -------
        str
            Nombre de la categoría.
        """
        return self.get_nombre_display()


class PreferenciaCliente(models.Model):
    """
    Preferencias específicas y límites personalizados para un cliente.

    Permite establecer límites de compra y venta individualizados y configuraciones específicas
    que sobreescriben los valores por defecto de la categoría del cliente.

    Attributes
    ----------
    cliente : Cliente
        Relación con el cliente.
    limite_compra : DecimalField
        Límite máximo de compra en gs.
    limite_venta : DecimalField
        Límite máximo de venta en gs.
    frecuencia_maxima : PositiveIntegerField
        Frecuencia máxima de transacciones por día.
    fecha_creacion : DateTimeField
        Fecha de creación del registro.
    fecha_actualizacion : DateTimeField
        Fecha de última actualización del registro.

    Notes
    -----
    - Los límites definidos aquí sobreescriben los valores por defecto de la categoría del cliente.
    - Tabla: `clientes_preferencia_cliente`.
    - Un cliente puede tener solo una preferencia personalizada.
    """
    cliente = models.OneToOneField('Cliente', on_delete=models.CASCADE, related_name='preferencias')
    limite_compra = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text="Límite máximo de compra")
    limite_venta = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text="Límite máximo de venta")
    frecuencia_maxima = models.PositiveIntegerField(default=0, help_text="Frecuencia máxima de transacciones por día (0 = sin límite)")
    preferencia_tipo_cambio = models.CharField(max_length=50, blank=True, help_text="Preferencia de tipo de cambio (ej: 'preferencial', 'mercado', etc.)")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clientes_preferencia_cliente'
        verbose_name = 'Preferencia de Cliente'
        verbose_name_plural = 'Preferencias de Cliente'

    def __str__(self):
        """
        Representación en cadena de las preferencias del cliente.

        Returns
        -------
        str
            Formato "Preferencias de {Nombre Completo del Cliente}".
        """
        return f"Preferencias de {self.cliente.obtener_nombre_completo()}"


class Cliente(models.Model):
    """
    Modelo que representa a un cliente de la casa de cambio.

    Attributes
    ----------
    nombre : CharField
        Nombre completo del cliente (personas físicas).
    apellido : CharField
        Apellido del cliente (personas físicas).
    nombre_empresa : CharField
        Nombre de la empresa (personas jurídicas).
    representante_legal : CharField
        Nombre del representante legal (personas jurídicas).
    email : EmailField
        Correo electrónico del cliente.
    telefono : CharField
        Número de teléfono del cliente.
    direccion : TextField
        Dirección del cliente.
    tipo_cliente : CharField
        Tipo de cliente (física o jurídica).
    estado : CharField
        Estado del cliente (Activo, Inactivo, Suspendido, Pendiente).
    categoria : CategoriaCliente
        Categoría a la que pertenece el cliente.
    numero_identificacion : CharField
        Número de identificación (CI, RUC).
    usuarios : ManyToManyField[Usuario]
        Usuarios asociados al cliente.
    creado_por : Usuario
        Usuario que creó el registro.
    fecha_creacion : DateTimeField
        Fecha de creación del registro.
    fecha_actualizacion : DateTimeField
        Fecha de última actualización del registro.
    saldo_cuenta : DecimalField
        Saldo de la cuenta principal del cliente.
    """
    TIPOS_CLIENTE = [
        ('FISICA', 'Persona Física'),
        ('JURIDICA', 'Persona Jurídica'),
    ]

    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
        ('SUSPENDIDO', 'Suspendido'),
        ('PENDIENTE', 'Pendiente'),
    ]

    # Información Básica
    tipo_cliente = models.CharField(max_length=20, choices=TIPOS_CLIENTE)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVO')
    categoria = models.ForeignKey(
        CategoriaCliente, 
        on_delete=models.PROTECT, 
        related_name='clientes'
    )

    # Campos de Persona Física
    nombre = models.CharField(max_length=100, blank=True)
    apellido = models.CharField(max_length=100, blank=True)
    
    # Campos de Persona Jurídica
    nombre_empresa = models.CharField(max_length=200, blank=True)
    representante_legal = models.CharField(max_length=200, blank=True)
    
    # Campos Comunes
    numero_identificacion = models.CharField(
        max_length=50, 
        unique=True,
        help_text="DNI/CUIT/RUC u otro documento de identificación"
    )
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    
    # Usuarios Asociados (relación muchos a muchos)
    usuarios = models.ManyToManyField(
        'cuentas.Usuario',
        through='ClienteUsuario',
        through_fields=('cliente', 'usuario'),
        related_name='clientes',
        blank=True
    )

    # customer_id para integración con Stripe
    stripe_customer_id = models.CharField(max_length=100, default="")

    # Información Financiera
    saldo_cuenta = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clientes_creados'
    )

    class Meta:
        db_table = 'clientes_cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-fecha_creacion']

    def __str__(self):
        """
        Representación en cadena del cliente.

        Returns
        -------
        str
            Formato "Nombre Apellido (Número Identificación)" (para personas físicas) o
            "Nombre Empresa (Número Identificación)" (para personas jurídicas).
        """
        if self.tipo_cliente == 'FISICA':
            return f"{self.nombre} {self.apellido} ({self.numero_identificacion})"
        else:
            return f"{self.nombre_empresa} ({self.numero_identificacion})"

    def obtener_nombre_completo(self):
        """
        Obtiene el nombre completo o nombre de la empresa del cliente.

        Returns
        -------
        str
            Nombre completo (para personas físicas) o nombre de la empresa (para personas jurídicas).
        """
        if self.tipo_cliente == 'FISICA':
            return f"{self.nombre} {self.apellido}".strip()
        else:
            return self.nombre_empresa


    def puede_realizar_transaccion(self, monto):
        """
        Verifica si el cliente puede realizar la transacción según los límites establecidos.

        Evalúa los límites diarios y mensuales de transacción basándose en la categoría del cliente y
        las transacciones ya realizadas.

        Parameters
        ----------
        monto : Decimal
            Monto de la transacción a verificar.

        Returns
        -------
        bool
            True si la transacción puede realizarse sin exceder los límites, False en caso contrario.

        Notes
        -----
        - Este método considera los límites establecidos en la categoría del cliente.
        - Solo considera transacciones con estado 'COMPLETADA' o 'PAGADA' para el cálculo de los límites.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        hoy = timezone.now().date()
        mes_actual = timezone.now().replace(day=1).date()
        
        # Calcular transacciones diarias
        transacciones_diarias = self.transacciones.filter(
            fecha_creacion__date=hoy,
            estado__in=['COMPLETADA', 'PAGADA']
        ).aggregate(
            total=models.Sum('monto_origen')
        )['total'] or Decimal('0.00')
        
        # Calcular transacciones mensuales
        transacciones_mensuales = self.transacciones.filter(
            fecha_creacion__date__gte=mes_actual,
            estado__in=['COMPLETADA', 'PAGADA']
        ).aggregate(
            total=models.Sum('monto_origen')
        )['total'] or Decimal('0.00')
        
        # Comprobar límites
        limite_diario = self.categoria.limite_transaccion_diario
        limite_mensual = self.categoria.limite_transaccion_mensual
        
        return (
            transacciones_diarias + monto <= limite_diario and
            transacciones_mensuales + monto <= limite_mensual
        )


class ClienteUsuario(models.Model):
    """
    Modelo intermedio para la relación muchos a muchos entre Cliente y Usuario.

    Attributes
    ----------
    cliente : Cliente
        Relación con el cliente.
    usuario : Usuario
        Relación con el usuario.
    rol : str
        Rol asignado al usuario para este cliente.
    esta_activo : bool
        Indica si la relación está activa.
    fecha_asignacion : datetime
        Fecha de asignación del rol.
    asignado_por : Usuario
        Usuario que asignó el rol.
    permisos : dict
        Permisos específicos para este usuario en este cliente.

    """
    ROLES = [
        ('PROPIETARIO', 'Propietario'),
        ('AUTORIZADO', 'Autorizado'),
        ('CONSULTA', 'Solo Consulta'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    usuario = models.ForeignKey('cuentas.Usuario', on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choices=ROLES, default='AUTORIZADO')
    esta_activo = models.BooleanField(default=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    asignado_por = models.ForeignKey(
        'cuentas.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_cliente_asignados'
    )
    permisos = models.JSONField(
        default=dict,
        help_text="Permisos específicos para este usuario en este cliente"
    )

    class Meta:
        db_table = 'clientes_cliente_usuario'
        verbose_name = 'Usuario-Cliente'
        verbose_name_plural = 'Usuarios-Clientes'
        unique_together = ['cliente', 'usuario']

    def __str__(self):
        """
        Representación en cadena de la relación usuario-cliente.

        Returns
        -------
        str
            Formato "Nombre Usuario - Nombre Cliente (Rol)".
        """
        return f"{self.usuario.nombre_completo} - {self.cliente.obtener_nombre_completo()} ({self.get_rol_display()})"



class MonedaFavorita(models.Model):
    """
    Modelo para las monedas favoritas de un cliente.

    Attributes
    ----------
    cliente : Cliente
        Relación con el cliente.
    moneda : Moneda
        Relación con la moneda.
    fecha_creacion : DateTimeField
        Fecha de creación del registro.
    orden : PositiveIntegerField
        Orden de preferencia de la moneda para el cliente.
    """
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        related_name='monedas_favoritas'
    )
    moneda = models.ForeignKey(
        'divisas.Moneda', 
        on_delete=models.CASCADE,
        related_name='favorita_por_clientes'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'clientes_moneda_favorita'
        verbose_name = 'Moneda Favorita'
        verbose_name_plural = 'Monedas Favoritas'
        unique_together = ['cliente', 'moneda']
        ordering = ['orden', 'fecha_creacion']

    def __str__(self):
        return f"{self.cliente.obtener_nombre_completo()} - {self.moneda.codigo}"


class SaldoCliente(models.Model):
    """
    Modelo para rastrear los saldos disponibles para retiro de los clientes por moneda.

    Permite gestionar múltiples saldos en diferentes monedas para cada cliente.

    Attributes
    ----------
    cliente : Cliente
        Relación con el cliente.
    moneda : Moneda
        Relación con la moneda.
    saldo : DecimalField
        Saldo disponible para retiro.
    ultima_actualizacion : DateTimeField
        Fecha de la última actualización del saldo.

    Notes
    -----
    - Un cliente puede tener múltiples saldos, uno por cada moneda.
    - La combinación de cliente y moneda debe ser única.
    """
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        related_name='saldos_moneda'
    )
    moneda = models.ForeignKey(
        'divisas.Moneda', 
        on_delete=models.CASCADE,
        related_name='saldos_cliente'
    )
    saldo = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.00'))
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clientes_saldo'
        verbose_name = 'Saldo de Cliente'
        verbose_name_plural = 'Saldos de Clientes'
        unique_together = ['cliente', 'moneda']

    def __str__(self):
        """
        Representación en cadena del saldo del cliente.

        Returns
        -------
        str
            Formato "Nombre Cliente - Código Moneda: Saldo".
        """
        return f"{self.cliente.obtener_nombre_completo()} - {self.moneda.codigo}: {self.saldo}"