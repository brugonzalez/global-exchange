from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cuentas.models import Rol, Permiso
from django.db import transaction

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Inicializa el sistema con roles, permisos y usuarios de prueba'

    def handle(self, *args, **options):
        self.stdout.write('Inicializando sistema de roles y permisos...')
        
        with transaction.atomic():
            # Crear permisos del sistema
            self.crear_permisos()
            
            # Crear roles del sistema
            self.crear_roles()
            
            # Crear usuarios de prueba
            self.crear_usuarios_prueba()
            
        self.stdout.write(
            self.style.SUCCESS('Sistema inicializado correctamente')
        )

    def crear_permisos(self):
        """Crea los permisos predefinidos del sistema."""
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
                usuario.save()
                
                # Asignar rol de Administrador
                rol_admin = Rol.objects.get(nombre_rol='Administrador')
                usuario.roles.add(rol_admin)
                
                self.stdout.write(f'  Creado usuario administrador: {username}')
        
        # Usuarios regulares
        for i in range(1, 7):
            username = f'usuario{i}'
            if not Usuario.objects.filter(username=username).exists():
                usuario = Usuario.objects.create_user(
                    username=username,
                    email=f'{username}@example.com',
                    nombre_completo=f'Usuario {i}',
                    password=username
                )
                usuario.email_verificado = True
                usuario.save()
                
                # Asignar rol de Usuario
                rol_usuario = Rol.objects.get(nombre_rol='Usuario')
                usuario.roles.add(rol_usuario)
                
                self.stdout.write(f'  Creado usuario regular: {username}')