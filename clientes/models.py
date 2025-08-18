from django.db import models
from django.core.validators import RegexValidator
from decimal import Decimal


class CategoriaCliente(models.Model):
    """
    Modelo para las categorías/niveles de clientes.
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
        return self.get_nombre_display()


class Cliente(models.Model):
    """
    Modelo para clientes (personas físicas y jurídicas).
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
        if self.tipo_cliente == 'FISICA':
            return f"{self.nombre} {self.apellido} ({self.numero_identificacion})"
        else:
            return f"{self.nombre_empresa} ({self.numero_identificacion})"

    def obtener_nombre_completo(self):
        """Obtiene el nombre completo/nombre de la empresa del cliente."""
        if self.tipo_cliente == 'FISICA':
            return f"{self.nombre} {self.apellido}".strip()
        else:
            return self.nombre_empresa

    def obtener_saldo_actual(self):
        """Obtiene el saldo actual de la cuenta."""
        return self.saldo_cuenta

    def puede_realizar_transaccion(self, monto):
        """Verifica si el cliente puede realizar la transacción según los límites."""
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
    Modelo intermedio para la relación Cliente-Usuario.
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
        return f"{self.usuario.nombre_completo} - {self.cliente.obtener_nombre_completo()} ({self.get_rol_display()})"

    def puede_realizar_transacciones(self):
        """Verifica si esta asociación usuario-cliente permite transacciones."""
        return self.esta_activo and self.rol in ['PROPIETARIO', 'AUTORIZADO']


class MonedaFavorita(models.Model):
    """
    Modelo para las monedas favoritas de un cliente.
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
    Modelo para rastrear los saldos de los clientes por moneda.
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
        return f"{self.cliente.obtener_nombre_completo()} - {self.moneda.codigo}: {self.saldo}"