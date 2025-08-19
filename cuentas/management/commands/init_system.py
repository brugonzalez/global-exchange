from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cuentas.models import Rol, Permiso
from django.db import transaction
from decimal import Decimal

from divisas.models import Moneda, TasaCambio, MetodoPago
from clientes.models import CategoriaCliente
from notificaciones.models import PlantillaNotificacion

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Inicializa el sistema Global Exchange con datos completos: roles, permisos, usuarios, monedas, tasas y configuraciones'

    def handle(self, *args, **options):
        self.stdout.write('Inicializando sistema Global Exchange completo...')
        
        with transaction.atomic():
            # Crear monedas y tasas de cambio
            self.crear_monedas_y_tasas()
            
            # Crear categorías de clientes
            self.crear_categorias_clientes()
            
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

    def crear_monedas_y_tasas(self):
        """Crea las monedas y tasas de cambio iniciales."""
        self.stdout.write('Creando monedas y tasas de cambio...')
        
        # Crear moneda base - PYG (Guaraní Paraguayo)
        guarani_paraguayo, creado = Moneda.objects.get_or_create(
            codigo='PYG',
            defaults={
                'nombre': 'Guaraní Paraguayo',
                'simbolo': '₲',
                'tipo_moneda': 'FIAT',
                'es_moneda_base': True,
                'esta_activa': True,
                'lugares_decimales': 2
            }
        )
        if creado:
            self.stdout.write(f'  ✓ Moneda base creada: {guarani_paraguayo}')
        
        # Crear otras monedas
        datos_monedas = [
            {'codigo': 'USD', 'nombre': 'Dólar Estadounidense', 'simbolo': '$', 'tipo': 'FIAT'},
            {'codigo': 'EUR', 'nombre': 'Euro', 'simbolo': '€', 'tipo': 'FIAT'},
            {'codigo': 'BRL', 'nombre': 'Real Brasileño', 'simbolo': 'R$', 'tipo': 'FIAT'},
            {'codigo': 'ARS', 'nombre': 'Peso Argentino', 'simbolo': '$', 'tipo': 'FIAT'},
            {'codigo': 'CLP', 'nombre': 'Peso Chileno', 'simbolo': '$', 'tipo': 'FIAT'},
            {'codigo': 'UYU', 'nombre': 'Peso Uruguayo', 'simbolo': '$', 'tipo': 'FIAT'},
            {'codigo': 'GEX', 'nombre': 'Global Exchange Coin', 'simbolo': 'GEX', 'tipo': 'DIGITAL', 'empresa': True},
        ]
        
        for dato_moneda in datos_monedas:
            moneda, creado = Moneda.objects.get_or_create(
                codigo=dato_moneda['codigo'],
                defaults={
                    'nombre': dato_moneda['nombre'],
                    'simbolo': dato_moneda['simbolo'],
                    'tipo_moneda': dato_moneda['tipo'],
                    'es_moneda_empresa': dato_moneda.get('empresa', False),
                    'esta_activa': True,
                    'lugares_decimales': 8 if dato_moneda['tipo'] == 'DIGITAL' else 2
                }
            )
            if creado:
                self.stdout.write(f'  ✓ Moneda creada: {moneda}')

        # Crear tasas de cambio iniciales (usando PYG como moneda base)
        datos_tasas = [
            {'moneda': 'USD', 'compra': Decimal('7300.00'), 'venta': Decimal('7500.00')},  # USD a PYG
            {'moneda': 'EUR', 'compra': Decimal('7800.00'), 'venta': Decimal('8000.00')},  # EUR a PYG  
            {'moneda': 'BRL', 'compra': Decimal('1350.00'), 'venta': Decimal('1400.00')},  # BRL a PYG
            {'moneda': 'ARS', 'compra': Decimal('7.40'), 'venta': Decimal('7.60')},       # ARS a PYG
            {'moneda': 'CLP', 'compra': Decimal('8.00'), 'venta': Decimal('8.20')},       # CLP a PYG
            {'moneda': 'UYU', 'compra': Decimal('180.00'), 'venta': Decimal('185.00')},   # UYU a PYG
            {'moneda': 'GEX', 'compra': Decimal('750.00'), 'venta': Decimal('780.00')},   # GEX a PYG
        ]
        
        for dato_tasa in datos_tasas:
            moneda = Moneda.objects.get(codigo=dato_tasa['moneda'])
            
            tasa, creado = TasaCambio.objects.get_or_create(
                moneda=moneda,
                moneda_base=guarani_paraguayo,
                esta_activa=True,
                defaults={
                    'tasa_compra': dato_tasa['compra'],
                    'tasa_venta': dato_tasa['venta'],
                    'fuente': 'MANUAL'
                }
            )
            if creado:
                self.stdout.write(f'  ✓ Tasa de cambio creada: {tasa}')

    def crear_categorias_clientes(self):
        """Crea las categorías de clientes predefinidas."""
        self.stdout.write('Creando categorías de clientes...')
        
        datos_categorias = [
            {
                'nombre': 'RETAIL',
                'limite_diario': Decimal('50000.00'),
                'limite_mensual': Decimal('500000.00'),
                'margen': Decimal('0.0200'),  # 2%
                'prioridad': 3
            },
            {
                'nombre': 'CORPORATE',
                'limite_diario': Decimal('500000.00'),
                'limite_mensual': Decimal('5000000.00'),
                'margen': Decimal('0.0150'),  # 1.5%
                'prioridad': 2
            },
            {
                'nombre': 'VIP',
                'limite_diario': Decimal('1000000.00'),
                'limite_mensual': Decimal('10000000.00'),
                'margen': Decimal('0.0100'),  # 1%
                'prioridad': 1
            }
        ]
        
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
                self.stdout.write(f'  ✓ Categoría de cliente creada: {categoria}')

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
                'porcentaje_comision': Decimal('0.5000'),  # 0.5%
                'grupo': 'BANKING'
            },
            {
                'nombre': 'Billetera Digital - MercadoPago',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': True,
                'soporta_venta': True,
                'monto_minimo': Decimal('100.00'),
                'horas_procesamiento': 1,
                'porcentaje_comision': Decimal('1.0000'),  # 1%
                'grupo': 'DIGITAL_WALLETS'
            },
            {
                'nombre': 'Tarjeta de Débito',
                'tipo': 'DEBIT_CARD',
                'soporta_compra': True,
                'soporta_venta': False,
                'monto_minimo': Decimal('100.00'),
                'horas_procesamiento': 1,
                'porcentaje_comision': Decimal('2.0000'),  # 2%
                'grupo': 'CARDS'
            },
            {
                'nombre': 'Tarjeta de Crédito (Stripe)',
                'tipo': 'CREDIT_CARD',
                'soporta_compra': True,
                'soporta_venta': False,
                'monto_minimo': Decimal('50.00'),
                'horas_procesamiento': 1,
                'porcentaje_comision': Decimal('2.9000'),  # 2.9% (tasa típica de Stripe)
                'grupo': 'CARDS'
            },
            {
                'nombre': 'SIPAP - Sistema de Pagos Paraguay',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': True,
                'soporta_venta': True,
                'monto_minimo': Decimal('1000.00'),
                'horas_procesamiento': 2,
                'porcentaje_comision': Decimal('0.8000'),  # 0.8%
                'grupo': 'DIGITAL_WALLETS'
            },
            {
                'nombre': 'Western Union',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': True,
                'soporta_venta': True,
                'monto_minimo': Decimal('5000.00'),
                'horas_procesamiento': 4,
                'porcentaje_comision': Decimal('1.5000'),  # 1.5%
                'grupo': 'INTERNATIONAL_WALLETS'
            },
            {
                'nombre': 'EuroTransfer',
                'tipo': 'DIGITAL_WALLET',
                'soporta_compra': True,
                'soporta_venta': True,
                'monto_minimo': Decimal('10000.00'),
                'horas_procesamiento': 6,
                'porcentaje_comision': Decimal('1.2000'),  # 1.2%
                'grupo': 'INTERNATIONAL_WALLETS'
            },
            {
                'nombre': 'Retiro en Caja - Peso Chileno',
                'tipo': 'CASH',
                'soporta_compra': False,
                'soporta_venta': True,
                'monto_minimo': Decimal('50000.00'),  # Mínimo CLP
                'horas_procesamiento': 48,
                'porcentaje_comision': Decimal('0.0000'),  # Sin comisión para retiro en efectivo
                'grupo': 'CASH_PICKUP'
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
                usuario.save()
                
                # Asignar solo rol de Administrador (no Usuario)
                rol_admin = Rol.objects.get(nombre_rol='Administrador')
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
                
                self.stdout.write(f'  ✓ Usuario regular creado: {username}')
                self.stdout.write(f'    Contraseña: {username} (¡cambiar inmediatamente!)')