from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cuentas.models import Rol, Permiso, Configuracion
from django.db import transaction
from decimal import Decimal

from divisas.models import Moneda, PrecioBase, TasaCambio, MetodoPago, MetodoCobro
from clientes.models import CategoriaCliente, Cliente, ClienteUsuario
from notificaciones.models import PlantillaNotificacion
from tauser.models import Tauser, StockTauser

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Inicializa el sistema Global Exchange con datos completos: roles, permisos, usuarios, monedas, tasas y configuraciones'

    def handle(self, *args, **options):
        self.stdout.write('Inicializando sistema Global Exchange completo...')


        #dividimos en mas transacciones por dependencia

        with transaction.atomic():
            # Crear categorías de clientes
            self.crear_categorias_clientes()

            # Crear monedas y tasas de cambio
            self.crear_monedas_y_tasas()
            
            # Crear métodos de pago
            self.crear_metodos_pago()
            
            # Crear plantillas de notificación
            self.crear_plantillas_notificacion()
            
            # Crear permisos del sistema
            self.crear_permisos()
            
            # Crear roles del sistema
            self.crear_roles()
            
            # Crear usuarios de prueba
            self.crear_usuarios_prueba()

            self.crear_metodos_cobro()

            self.crear_configuraciones()

            self.crear_tausers()

            self.crear_clientes()

            #self.asignar_cliente_usuario()

            self.crear_stock_tausers()

        self.stdout.write(
            self.style.SUCCESS('¡Sistema Global Exchange inicializado exitosamente!')
        )
        self.stdout.write('\nSiguientes pasos:')
        self.stdout.write('1. Ejecute el servidor de desarrollo: python manage.py runserver')
        self.stdout.write('2. Visite http://127.0.0.1:8000/ para ver el panel de control')
        self.stdout.write('3. Visite http://127.0.0.1:8000/admin/ para acceder al panel de administración')
        self.stdout.write('4. Inicie sesión con usuarios administradores:')
        self.stdout.write('   - Email: admin1@globalexchange.com / Contraseña: admin1')
        self.stdout.write('   - Email: admin2@globalexchange.com / Contraseña: admin2')
        self.stdout.write('5. O inicie sesión con usuarios regulares:')
        self.stdout.write('   - Email: usuario1@globalexchange.com / Contraseña: usuario1')
        self.stdout.write('   - Email: usuario2@globalexchange.com / Contraseña: usuario2')
        self.stdout.write('   - ... hasta usuario6@globalexchange.com / Contraseña: usuario6')
        self.stdout.write(self.style.WARNING('\nNOTA: El sistema usa EMAIL como usuario para login, no el username.'))

    def crear_categorias_clientes(self):
        """Crea las categorías de clientes predefinidas."""
        self.stdout.write('Creando categorías de clientes...')
        
        datos_categorias = [
            {
                'nombre': 'RETAIL',
                'limite_diario': Decimal('50000.00'),
                'limite_mensual': Decimal('500000.00'),
                'margen': Decimal('0.0000'),  # 0%
                'prioridad': 3
            },
            {
                'nombre': 'CORPORATE',
                'limite_diario': Decimal('500000.00'),
                'limite_mensual': Decimal('5000000.00'),
                'margen': Decimal('0.0500'),  # 5%
                'prioridad': 2
            },
            {
                'nombre': 'VIP',
                'limite_diario': Decimal('1000000.00'),
                'limite_mensual': Decimal('10000000.00'),
                'margen': Decimal('0.1000'),  # 10%
                'prioridad': 1
            }
        ]

        categoriasCliente = {}
        i = 1
        for dato_cat in datos_categorias:
            categoria, creado = CategoriaCliente.objects.get_or_create(
                nombre=dato_cat['nombre'],
                defaults={
                    'limite_transaccion_diario': dato_cat['limite_diario'],
                    'limite_transaccion_mensual': dato_cat['limite_mensual'],
                    'margen_tasa_preferencial': dato_cat['margen'],
                    'nivel_prioridad': dato_cat['prioridad']
                }
            )
            if creado:
                categoriasCliente[i] = categoria
                i = i + 1
                self.stdout.write(f'  ✓ Categoría de cliente creada: {categoria}')

        return categoriasCliente

    def crear_monedas_y_tasas(self):
        """Crea las monedas y tasas de cambio iniciales."""
        self.stdout.write('Creando monedas y tasas de cambio...')

        # Crear moneda base - PYG (Guaraní Paraguayo)
        guarani_paraguayo, creado = Moneda.objects.get_or_create(
            codigo='PYG',
            defaults={
                'nombre': 'Guaraní Paraguayo',
                'simbolo': '₲',
                'es_moneda_base': True,
                'esta_activa': True,
                'lugares_decimales': 2,
                'pais': 'PY'
            }
        )
        if creado:
            self.stdout.write(f'  ✓ Moneda base creada: {guarani_paraguayo}')

        # Crear otras monedas
        datos_monedas = [
            {'codigo': 'USD', 'nombre': 'Dólar Estadounidense', 'simbolo': '$', 'pais': 'US'},
            {'codigo': 'EUR', 'nombre': 'Euro', 'simbolo': '€', 'pais': 'EU'},
            {'codigo': 'BRL', 'nombre': 'Real Brasileño', 'simbolo': 'R$', 'pais': 'BR'},
            {'codigo': 'ARS', 'nombre': 'Peso Argentino', 'simbolo': '$', 'pais': 'AR'},
            {'codigo': 'CLP', 'nombre': 'Peso Chileno', 'simbolo': '$', 'pais': 'CL'},
            {'codigo': 'UYU', 'nombre': 'Peso Uruguayo', 'simbolo': '$', 'pais': 'UY'},
        ]

        for dato_moneda in datos_monedas:
            moneda, creado = Moneda.objects.get_or_create(
                codigo=dato_moneda['codigo'],
                defaults={
                    'nombre': dato_moneda['nombre'],
                    'simbolo': dato_moneda['simbolo'],
                    'pais': dato_moneda['pais'],
                    'es_moneda_base': False,
                    'esta_activa': True,
                    'lugares_decimales': 2,
                    'comision_compra': Decimal('100.00'),
                    'comision_venta': Decimal('200.00')
                }
            )
            if creado:
                self.stdout.write(f'  ✓ Moneda creada: {moneda}')

        # Crear precios base (PrecioBase) para cada moneda respecto a PYG
        datos_precios_base = [
            {'moneda': 'USD', 'precio_base': Decimal('7300.00')},  # USD a PYG
            {'moneda': 'EUR', 'precio_base': Decimal('7800.00')},  # EUR a PYG
            {'moneda': 'BRL', 'precio_base': Decimal('1350.00')},  # BRL a PYG
            {'moneda': 'ARS', 'precio_base': Decimal('7.40')},     # ARS a PYG
            {'moneda': 'CLP', 'precio_base': Decimal('8.00')},     # CLP a PYG
            {'moneda': 'UYU', 'precio_base': Decimal('180.00')},   # UYU a PYG
        ]

        for dato_precio in datos_precios_base:
            moneda = Moneda.objects.get(codigo=dato_precio['moneda'])
            precio_base, creado = PrecioBase.objects.update_or_create(
                moneda=moneda,
                moneda_base=guarani_paraguayo,
                esta_activa=True,
                defaults={
                    'precio_base': dato_precio['precio_base']
                }
            )
            if creado:
                self.stdout.write(f'  ✓ Precio base creado: {precio_base}')




    def crear_metodos_pago(self):
        """Crea los métodos de pago disponibles."""
        self.stdout.write('Creando métodos de pago...')
        
        datos_metodos_pago = [
            {
                'nombre': 'Transferencia Bancaria',
                'tipo': 'BANK_TRANSFER',
                'soporta_compra': True,
                'soporta_venta': True,
                'monto_minimo': Decimal('1000.00'),
                'horas_procesamiento': 24,
                'porcentaje_comision': Decimal('0.05000'),  # 0.5%
                'grupo': 'BANKING',
                'porcentaje_visual': 5
            },
            {
                'nombre': 'Billetera Digital - MercadoPago',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': True,
                'soporta_venta': True,
                'monto_minimo': Decimal('100.00'),
                'horas_procesamiento': 1,
                'porcentaje_comision': Decimal('0.0100'),
                'grupo': 'DIGITAL_WALLETS',
                'porcentaje_visual': 1
            },
            {
                'nombre': 'Tarjeta de Crédito',
                'tipo': 'CREDIT_CARD',
                'soporta_compra': True,
                'soporta_venta': False,
                'monto_minimo': Decimal('50.00'),
                'horas_procesamiento': 1,
                'porcentaje_comision': Decimal('0.0290'),  # 2.9% (tasa típica de Stripe)
                'grupo': 'CARDS',
                'porcentaje_visual': 2
            },
            {
                'nombre': 'Western Union',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': True,
                'soporta_venta': True,
                'monto_minimo': Decimal('5000.00'),
                'horas_procesamiento': 4,
                'porcentaje_comision': Decimal('0.0150'),  # 1.5%
                'grupo': 'INTERNATIONAL_WALLETS',
                'porcentaje_visual': 1
            },
            {
                'nombre': 'EuroTransfer',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': True,
                'soporta_venta': True,
                'monto_minimo': Decimal('10000.00'),
                'horas_procesamiento': 6,
                'porcentaje_comision': Decimal('0.0120'),  # 1.2%
                'grupo': 'INTERNATIONAL_WALLETS',
                'porcentaje_visual': 1
            },
            {
                'nombre': 'Efectivo',
                'tipo': 'CASH',
                'soporta_compra': False,
                'soporta_venta': True,
                'monto_minimo': Decimal('50000.00'),  # Mínimo CLP
                'horas_procesamiento': 48,
                'porcentaje_comision': Decimal('0.0000'),  # Sin comisión para retiro en efectivo
                'grupo': 'CASH_PICKUP',
                'porcentaje_visual': 0
            },
            {
                'nombre': 'Cheque',
                'tipo': 'CASH',
                'soporta_compra': False,
                'soporta_venta': True,
                'monto_minimo': Decimal('50000.00'),  # Mínimo CLP
                'horas_procesamiento': 48,
                'porcentaje_comision': Decimal('0.0000'),  # Sin comisión para retiro en efectivo
                'grupo': 'CASH_PICKUP',
                'porcentaje_visual': 0
            }
        ]
        
        for dato_mp in datos_metodos_pago:
            metodo_pago, creado = MetodoPago.objects.get_or_create(
                nombre=dato_mp['nombre'],
                defaults={
                    'tipo_metodo': dato_mp['tipo'],
                    'grupo_metodo': dato_mp['grupo'],
                    'soporta_compra': dato_mp['soporta_compra'],
                    'soporta_venta': dato_mp['soporta_venta'],
                    'monto_minimo': dato_mp['monto_minimo'],
                    'tiempo_procesamiento_horas': dato_mp['horas_procesamiento'],
                    'porcentaje_comision': dato_mp['porcentaje_comision'],
                    'porcentaje_visual': dato_mp['porcentaje_visual'],
                    'esta_activo': True,
                    'configuracion': {
                        'grupo': dato_mp['grupo'],
                        'pseudo_integracion': dato_mp['nombre'] in ['SIPAP - Sistema de Pagos Paraguay', 'Western Union', 'EuroTransfer'],
                        'requiere_manejo_especial': dato_mp['nombre'] == 'Retiro en Caja - Peso Chileno'
                    }
                }
            )
            if creado:
                self.stdout.write(f'  ✓ Método de pago creado: {metodo_pago}')

    def crear_metodos_cobro(self):
        """Crea los métodos de cobro disponibles."""
        self.stdout.write('Creando métodos de cobro...')

        datos_metodos_pago = [
            {
                'nombre': 'Transferencia Bancaria',
                'tipo': 'BANK_TRANSFER',
                'soporta_compra': True,
                'soporta_venta': True,
                'monto_minimo': Decimal('1000.00'),
                'horas_procesamiento': 24,
                'porcentaje_comision': Decimal('0.0100'),  # 0.5%
                'grupo': 'BANKING',
                'porcentaje_visual': 1
            },
            {
                'nombre': 'Billetera Digital - MercadoPago',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': False,
                'soporta_venta': True,
                'monto_minimo': Decimal('100.00'),
                'horas_procesamiento': 1,
                'porcentaje_comision': Decimal('0.0100'),
                'grupo': 'DIGITAL_WALLETS',
                'porcentaje_visual': 1
            },
            {
                'nombre': 'Western Union',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': False,
                'soporta_venta': True,
                'monto_minimo': Decimal('5000.00'),
                'horas_procesamiento': 4,
                'porcentaje_comision': Decimal('0.0150'),  # 1.5%
                'grupo': 'INTERNATIONAL_WALLETS',
                'porcentaje_visual': 1
            },
            {
                'nombre': 'EuroTransfer',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': False,
                'soporta_venta': True,
                'monto_minimo': Decimal('10000.00'),
                'horas_procesamiento': 6,
                'porcentaje_comision': Decimal('0.0120'),  # 1.2%
                'grupo': 'INTERNATIONAL_WALLETS',
                'porcentaje_visual': 1
            },
            {
                'nombre': 'Efectivo',
                'tipo': 'CASH',
                'soporta_compra': False,
                'soporta_venta': True,
                'monto_minimo': Decimal('50000.00'),  # Mínimo CLP
                'horas_procesamiento': 48,
                'porcentaje_comision': Decimal('0.0100'),  # Sin comisión para retiro en efectivo
                'grupo': 'CASH_PICKUP',
                'porcentaje_visual': 1
            }
        ]

        for dato_mp in datos_metodos_pago:
            metodo_pago, creado = MetodoCobro.objects.get_or_create(
                nombre=dato_mp['nombre'],
                defaults={
                    'tipo_metodo': dato_mp['tipo'],
                    'grupo_metodo': dato_mp['grupo'],
                    'soporta_compra': dato_mp['soporta_compra'],
                    'soporta_venta': dato_mp['soporta_venta'],
                    'monto_minimo': dato_mp['monto_minimo'],
                    'porcentaje_comision': dato_mp['porcentaje_comision'],
                    'porcentaje_visual': dato_mp['porcentaje_visual'],
                    'esta_activo': True
                }
            )
            if creado:
                self.stdout.write(f'  ✓ Método de pago creado: {metodo_pago}')

    def crear_plantillas_notificacion(self):
        """Crea las plantillas de notificación del sistema."""
        self.stdout.write('Creando plantillas de notificación...')
        
        datos_plantillas = [
            {
                'nombre': 'Verificación de Email',
                'tipo': 'EMAIL_VERIFICATION',
                'asunto': 'Verifique su dirección de email - Global Exchange',
                'cuerpo_html': '''
                <h2>Bienvenido a Global Exchange</h2>
                <p>Para completar su registro, por favor verifique su dirección de email haciendo clic en el siguiente enlace:</p>
                <p><a href="{{enlace_verificacion}}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verificar Email</a></p>
                <p>Si no puede hacer clic en el enlace, copie y pegue la siguiente URL en su navegador:</p>
                <p>{{enlace_verificacion}}</p>
                <p>Este enlace expirará en 24 horas.</p>
                ''',
                'cuerpo_texto': '''
                Bienvenido a Global Exchange
                
                Para completar su registro, por favor verifique su dirección de email visitando el siguiente enlace:
                {{enlace_verificacion}}
                
                Este enlace expirará en 24 horas.
                '''
            },
            {
                'nombre': 'Transacción Creada',
                'tipo': 'TRANSACTION_CREATED',
                'asunto': 'Nueva transacción creada - #{{numero_transaccion}}',
                'cuerpo_html': '''
                <h2>Transacción Creada</h2>
                <p>Se ha creado una nueva transacción en su cuenta:</p>
                <ul>
                    <li><strong>Número:</strong> {{numero_transaccion}}</li>
                    <li><strong>Tipo:</strong> {{tipo_transaccion}}</li>
                    <li><strong>Monto:</strong> {{monto}} {{moneda}}</li>
                    <li><strong>Estado:</strong> {{estado}}</li>
                </ul>
                <p>Puede ver los detalles de su transacción en su panel de control.</p>
                ''',
                'cuerpo_texto': '''
                Transacción Creada
                
                Se ha creada una nueva transacción en su cuenta:
                - Número: {{numero_transaccion}}
                - Tipo: {{tipo_transaccion}}
                - Monto: {{monto}} {{moneda}}
                - Estado: {{estado}}
                
                Puede ver los detalles de su transacción en su panel de control.
                '''
            }
        ]
        
        for dato_plantilla in datos_plantillas:
            plantilla, creado = PlantillaNotificacion.objects.get_or_create(
                tipo_plantilla=dato_plantilla['tipo'],
                defaults={
                    'nombre': dato_plantilla['nombre'],
                    'asunto_email': dato_plantilla['asunto'],
                    'cuerpo_email_html': dato_plantilla['cuerpo_html'],
                    'cuerpo_email_texto': dato_plantilla['cuerpo_texto'],
                    'esta_activa': True
                }
            )
            if creado:
                self.stdout.write(f'  ✓ Plantilla de notificación creada: {plantilla}')

    def crear_permisos(self):
        """Crea los permisos predefinidos del sistema."""
        self.stdout.write('Creando permisos del sistema...')
        
        permisos = [
            # Permisos de Administrador
            ('crear_usuarios', 'Crear usuarios'),
            ('editar_usuarios', 'Editar usuarios'),
            ('eliminar_usuarios', 'Eliminar usuarios'),
            ('crear_clientes', 'Crear clientes'),
            ('editar_clientes', 'Editar clientes'),
            ('eliminar_clientes', 'Eliminar clientes'),
            ('configurar_monedas', 'Configurar monedas'),
            ('configurar_tasas', 'Configurar tasas de cambio'),
            ('ver_reportes', 'Ver reportes'),
            ('asignar_roles', 'Asignar roles a usuarios'),
            ('ver_logs', 'Ver logs del sistema'),
            ('gestionar_roles', 'Gestionar roles y permisos'),
            
            # Permisos de Cajero
            ('registrar_depositos', 'Registrar depósitos'),
            ('registrar_retiros', 'Registrar retiros'),
            ('confirmar_pagos', 'Confirmar pagos'),
            
            # Permisos de Usuario
            ('visualizar_clientes', 'Visualizar clientes asociados'),
            ('seleccionar_cliente', 'Seleccionar cliente para operar'),
            ('solicitar_cambio_compra', 'Realizar solicitudes de cambio de compra'),
            ('solicitar_cambio_venta', 'Realizar solicitudes de cambio de venta'),
            ('consultar_transacciones', 'Consultar transacciones'),
            ('simular_cambios', 'Realizar simulación de cambios de divisa'),
            
            # Permisos de Visitante
            ('visualizar_tasas', 'Visualizar tasas de cambio'),
            ('simular_transacciones', 'Realizar simulaciones de transacciones'),
        ]
        
        for codename, descripcion in permisos:
            permiso, creado = Permiso.objects.get_or_create(
                codename=codename,
                defaults={'descripcion': descripcion}
            )
            if creado:
                self.stdout.write(f'  Creado permiso: {descripcion}')

    def crear_roles(self):
        """Crea los roles predefinidos del sistema."""
        self.stdout.write('Creando roles del sistema...')
        
        # Rol Administrador
        rol_admin, creado = Rol.objects.get_or_create(
            nombre_rol='Administrador',
            defaults={
                'descripcion': 'Administrador del sistema con acceso completo',
                'es_sistema': True
            }
        )
        if creado:
            self.stdout.write('  Creado rol: Administrador')
            
        # Asignar permisos al Administrador
        permisos_admin = [
            'crear_usuarios', 'editar_usuarios', 'eliminar_usuarios',
            'crear_clientes', 'editar_clientes', 'eliminar_clientes',
            'configurar_monedas', 'configurar_tasas', 'ver_reportes',
            'asignar_roles', 'ver_logs', 'gestionar_roles'
        ]
        self.asignar_permisos_a_rol(rol_admin, permisos_admin)
        
        # Rol Cajero
        rol_cajero, creado = Rol.objects.get_or_create(
            nombre_rol='Cajero',
            defaults={
                'descripcion': 'Cajero con permisos para transacciones y pagos',
                'es_sistema': True
            }
        )
        if creado:
            self.stdout.write('  Creado rol: Cajero')
            
        permisos_cajero = [
            'registrar_depositos', 'registrar_retiros', 'confirmar_pagos'
        ]
        self.asignar_permisos_a_rol(rol_cajero, permisos_cajero)
        
        # Rol Usuario
        rol_usuario, creado = Rol.objects.get_or_create(
            nombre_rol='Usuario',
            defaults={
                'descripcion': 'Usuario regular del sistema',
                'es_sistema': True
            }
        )
        if creado:
            self.stdout.write('  Creado rol: Usuario')
            
        permisos_usuario = [
            'visualizar_clientes', 'seleccionar_cliente',
            'solicitar_cambio_compra', 'solicitar_cambio_venta',
            'consultar_transacciones', 'simular_cambios'
        ]
        self.asignar_permisos_a_rol(rol_usuario, permisos_usuario)
        
        # Rol Visitante
        rol_visitante, creado = Rol.objects.get_or_create(
            nombre_rol='Visitante',
            defaults={
                'descripcion': 'Visitante con permisos limitados de consulta',
                'es_sistema': True
            }
        )
        if creado:
            self.stdout.write('  Creado rol: Visitante')
            
        permisos_visitante = [
            'visualizar_tasas', 'simular_transacciones'
        ]
        self.asignar_permisos_a_rol(rol_visitante, permisos_visitante)

    def asignar_permisos_a_rol(self, rol, codenames_permisos):
        """Asigna permisos a un rol."""
        permisos = Permiso.objects.filter(codename__in=codenames_permisos)
        rol.permisos.set(permisos)
        
    def crear_usuarios_prueba(self):
        """Crea usuarios de prueba."""
        self.stdout.write('Creando usuarios de prueba...')

        usuarios = {}

        # Administradores
        for i in range(1, 3):
            username = f'admin{i}'
            if not Usuario.objects.filter(username=username).exists():
                usuario = Usuario.objects.create_user(
                    username=username,
                    email=f'{username}@globalexchange.com',
                    nombre_completo=f'Administrador {i}',
                    password=username
                )
                usuario.email_verificado = True
                usuario.is_staff = True
                usuario.is_superuser = True
                usuarios[i] = usuario
                usuario.save()
                
                # Asignar solo rol de Administrador (no Usuario)
                rol_admin = Rol.objects.get(nombre_rol='Administrador')
                self.stdout.write(f'  ✓ Objeto administrador: {rol_admin}')
                usuario.roles.set([rol_admin])  # Use set() to replace instead of add()
                
                self.stdout.write(f'  ✓ Usuario administrador creado: {username}')
                self.stdout.write(f'    Contraseña: {username} (¡cambiar inmediatamente!)')
        
        # Usuarios regulares
        for i in range(1, 7):
            username = f'usuario{i}'
            if not Usuario.objects.filter(username=username).exists():
                usuario = Usuario.objects.create_user(
                    username=username,
                    email=f'{username}@globalexchange.com',
                    nombre_completo=f'Usuario {i}',
                    password=username
                )
                usuario.email_verificado = True
                usuario.save()
                
                # Asignar rol de Usuario
                rol_usuario = Rol.objects.get(nombre_rol='Usuario')
                usuario.roles.set([rol_usuario])  # Use set() to ensure only this role

                usuarios[i] = usuario

                self.stdout.write(f'  ✓ Usuario regular creado: {username}')
                self.stdout.write(f'    Contraseña: {username} (¡cambiar inmediatamente!)')

        return usuarios

    def crear_clientes(self):
        """Crea clientes de prueba."""
        self.stdout.write('Creando clientes...')

        clientes = [
            {'tipo': 'FISICA', 'estado': 'ACTIVO', 'nombre': 'Juan', 'apellido': 'Perez', 'nombre_empresa': '', 'numero_identificacion': '12345', 'email': 'JuanPerez@gmail.com', 'saldo_cuenta': 0, 'stripe_customer_id': 'cus_SznbqGdw7Ep1G4', 'usa_limites': True},
            {'tipo': 'JURIDICA', 'estado': 'ACTIVO', 'nombre': '', 'apellido': '', 'nombre_empresa': 'Cervepar', 'numero_identificacion': '12346', 'email': 'cervepar@gmail.com', 'saldo_cuenta': 0, 'stripe_customer_id': 'cus_SzqrNFH3P4HGFp', 'usa_limites': True},
            {'tipo': 'JURIDICA', 'estado': 'ACTIVO', 'nombre': '', 'apellido': '', 'nombre_empresa': 'FPUNA', 'numero_identificacion': '12347', 'email': 'fpuna@gmail.com', 'saldo_cuenta': 0, 'stripe_customer_id': 'cus_SzqrNFH3P4HGFp', 'usa_limites': True},
        ]

        clientes_creados = {}

        usuario_creador = Usuario.objects.get(username='admin1')
        categoria_retail = CategoriaCliente.objects.get(nombre='RETAIL')
        categoria_corporate = CategoriaCliente.objects.get(nombre='CORPORATE')
        categoria_vip = CategoriaCliente.objects.get(nombre='VIP')

        # Usuarios regulares
        for i, data in enumerate(clientes):
            if i == 0:
                categorias_cliente = categoria_retail
            elif i == 1:
                categorias_cliente = categoria_corporate
            else:
                categorias_cliente = categoria_vip

            cliente = Cliente.objects.create(
                tipo_cliente=clientes[i]['tipo'],
                estado=clientes[i]['estado'],
                nombre=clientes[i]['nombre'],
                apellido=clientes[i]['apellido'],
                nombre_empresa=clientes[i]['nombre_empresa'],
                numero_identificacion=clientes[i]['numero_identificacion'],
                email=clientes[i]['email'],
                saldo_cuenta=clientes[i]['saldo_cuenta'],
                stripe_customer_id=clientes[i]['stripe_customer_id'],
                usa_limites_default=clientes[i]['usa_limites'],
                creado_por=usuario_creador,
                categoria_id=categorias_cliente.id,
            )

            self.stdout.write(f'  ✓ Cliente creado: {cliente}')
            clientes_creados[i] = cliente
            cliente.save()

        return clientes_creados

    def asignar_cliente_usuario(self):
        """Asigna clientes a usuarios de prueba."""
        self.stdout.write('Asignando clientes...')

        clientes = [
            {'rol': 'AUTORIZADO', 'esta_activo': True, 'asignado_por': 1, 'cliente_id': 2, 'usuario_id': 3},
            {'rol': 'AUTORIZADO', 'esta_activo': True, 'asignado_por': 1, 'cliente_id': 2, 'usuario_id': 4},
            {'rol': 'AUTORIZADO', 'esta_activo': True, 'asignado_por': 1, 'cliente_id': 1, 'usuario_id': 3},
            {'rol': 'AUTORIZADO', 'esta_activo': True, 'asignado_por': 1, 'cliente_id': 1, 'usuario_id': 4},
            {'rol': 'AUTORIZADO', 'esta_activo': True, 'asignado_por': 1, 'cliente_id': 1, 'usuario_id': 5},
            {'rol': 'AUTORIZADO', 'esta_activo': True, 'asignado_por': 1, 'cliente_id': 3, 'usuario_id': 3},
        ]

        usuario_creador = Usuario.objects.get(username='admin1')
        cliente1 = Cliente.objects.get(nombre='Juan')
        cliente2 = Cliente.objects.get(nombre_empresa='Cervepar')
        cliente3 = Cliente.objects.get(nombre_empresa='FPUNA')

        # Usuarios regulares
        for i in range(1, 6):

            if i in [1, 2]:
                cliente_id = cliente1.id
            elif i in [3, 5]:
                cliente_id = cliente2.id
            else:
                cliente_id = cliente3.id

            #

            self.stdout.write('Se realizo la asignacion de cliente a usuario')
            #cliente.save()

    def crear_tausers(self):
        """Crea los tausers del sistema."""
        self.stdout.write('Creando tausers...')

        datos_tausers = [
            {
                'nombre': 'asuncion',
                'estado': 'ACTIVO',
                'direccion': 'calle palma',
                'ciudad': 'asuncion',
                'pais': 'paraguay',
                'permite_depositos': True,
                'permite_retiros': True
            },
            {
                'nombre': 'san lorenzo',
                'estado': 'ACTIVO',
                'direccion': 'saturio rios',
                'ciudad': 'san lorenzo',
                'pais': 'paraguay',
                'permite_depositos': True,
                'permite_retiros': True
            },
            {
                'nombre': 'ñemby',
                'estado': 'ACTIVO',
                'direccion': 'santa rosa',
                'ciudad': 'ñemby',
                'pais': 'paraguay',
                'permite_depositos': True,
                'permite_retiros': True
            }
        ]

        tausers = {}
        i = 1
        for dato_tauser in datos_tausers:
            tauser, creado = Tauser.objects.get_or_create(
                nombre=dato_tauser['nombre'],
                defaults={
                    'estado': dato_tauser['estado'],
                    'direccion': dato_tauser['direccion'],
                    'ciudad': dato_tauser['ciudad'],
                    'pais': dato_tauser['pais'],
                    'permite_depositos': dato_tauser['permite_depositos'],
                    'permite_retiros': dato_tauser['permite_retiros']
                }
            )
            if creado:
                tausers[i] = tauser
                self.stdout.write(f'  ✓ Tauser creado: {tauser}')

        return tausers

    def crear_configuraciones(self):
        """Crea las configuraciones del sistema."""
        self.stdout.write('Creando configuraciones del sistema...')

        datos_configuraciones = [
            {
                'clave': 'LIMITE_TRANSACCION_DIARIO_DEFAULT',
                'valor': '100000000',
                'tipo_valor': 'MONTO',
                'descripcion': 'Límite del monto total equivalente a la suma de los montos de las transacciones de un cliente en el día',
                'categoria': 'Transacciones',
                'nombre': 'Limite Diario'
            },
            {
                'clave': 'LIMITE_TRANSACCION_MENSUAL_DEFAULT',
                'valor': '100000000',
                'tipo_valor': 'MONTO',
                'descripcion': 'Límite del monto total equivalente a la suma de los montos de las transacciones de un cliente en el mes',
                'categoria': 'Transacciones',
                'nombre': 'Limite Mensual'
            },
            {
                'clave': 'INTENTOS_MAX_BLOQUEO_CUENTA',
                'valor': '5',
                'tipo_valor': 'NUMBER',
                'descripcion': 'intentos maximos que tiene el usuario antes que se le bloquee la cuenta',
                'categoria': 'Cuenta'
            },
            {
                'clave': 'DURACION_BLOQUEO_CUENTA',
                'valor': '1800',
                'tipo_valor': 'NUMBER',
                'descripcion': 'duracion de bloqueo de la cuenta',
                'categoria': 'Cuenta'
            }
        ]

        for dato_config in datos_configuraciones:
            configuracion, creado = Configuracion.objects.get_or_create(
                clave=dato_config['clave'],
                defaults={
                    'valor': dato_config['valor'],
                    'tipo_valor': dato_config['tipo_valor'],
                    'descripcion': dato_config['descripcion'],
                    'categoria': dato_config['categoria'],
                    'nombre': dato_config.get('nombre', ''),
                    'es_editable': True
                }
            )
            if creado:
                self.stdout.write(f'  ✓ Configuración creada: {configuracion.clave}')

    def crear_stock_tausers(self):
        """Crea el stock de monedas para los tausers."""
        self.stdout.write('Creando stock de tausers...')

        # Datos de stock basados en el JSON proporcionado
        # Nota: Los IDs se generan automáticamente, por lo que los omitimos
        datos_stock = [
            # Stock para tauser 1 (asuncion)
            {'moneda_codigo': 'USD', 'tauser_nombre': 'asuncion', 'cantidad_disponible': Decimal('1000.00'), 'tauser_id': 1},
            {'moneda_codigo': 'EUR', 'tauser_nombre': 'asuncion', 'cantidad_disponible': Decimal('1000.00'), 'tauser_id': 1},
            {'moneda_codigo': 'BRL', 'tauser_nombre': 'asuncion', 'cantidad_disponible': Decimal('1000.00'), 'tauser_id': 1},
            {'moneda_codigo': 'PYG', 'tauser_nombre': 'asuncion', 'cantidad_disponible': Decimal('10000.00'), 'tauser_id': 1},

            # Stock para tauser 2 (san lorenzo)
            {'moneda_codigo': 'USD', 'tauser_nombre': 'san lorenzo', 'cantidad_disponible': Decimal('50.00'), 'tauser_id': 2},
            {'moneda_codigo': 'EUR', 'tauser_nombre': 'san lorenzo', 'cantidad_disponible': Decimal('50.00'), 'tauser_id': 2},
            {'moneda_codigo': 'BRL', 'tauser_nombre': 'san lorenzo', 'cantidad_disponible': Decimal('50.00'), 'tauser_id': 2},

            # Stock para tauser 3 (ñemby)
            {'moneda_codigo': 'USD', 'tauser_nombre': 'ñemby', 'cantidad_disponible': Decimal('10.00'), 'tauser_id': 3},
            {'moneda_codigo': 'EUR', 'tauser_nombre': 'ñemby', 'cantidad_disponible': Decimal('10.00'), 'tauser_id': 3},
            {'moneda_codigo': 'BRL', 'tauser_nombre': 'ñemby', 'cantidad_disponible': Decimal('10.00'), 'tauser_id': 3},
        ]

        for dato_stock in datos_stock:
            try:
                moneda = Moneda.objects.get(codigo=dato_stock['moneda_codigo'])
                tauser = Tauser.objects.get(nombre=dato_stock['tauser_nombre'])

                stock, creado = StockTauser.objects.get_or_create(
                    moneda=moneda,
                    tauser=tauser,
                    defaults={
                        'cantidad_disponible': dato_stock['cantidad_disponible'],
                        'cantidad_reservada': Decimal('0.00'),
                        'stock_minimo': Decimal('1.00'),
                        'stock_maximo': Decimal('100000000.00'),
                        'alerta_stock_bajo': False
                    }
                )
                if creado:
                    self.stdout.write(
                        f'  ✓ Stock creado: {tauser.nombre} - {moneda.codigo} ({dato_stock["cantidad_disponible"]})')

            except Moneda.DoesNotExist:
                self.stdout.write(f'  ❌ Moneda no encontrada: {dato_stock["moneda_codigo"]}')
            except Tauser.DoesNotExist:
                self.stdout.write(f'  ❌ Tauser no encontrado: {dato_stock["tauser_nombre"]}')

    # ... resto de métodos existentes permanecen igual ...