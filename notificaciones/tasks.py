
import threading
from django.core.mail import send_mail
from django.conf import settings
from django.template import Template, Context
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def asegurar_preferencias_notificacion(usuario):
    """
    Asegura que el usuario tenga preferencias de notificación, crea las predeterminadas si no existen.
    """
    from .models import PreferenciaNotificacion
    preferencias, creado = PreferenciaNotificacion.objects.get_or_create(
        usuario=usuario,
        defaults={
            'email_actualizaciones_transaccion': True,
            'email_alertas_tasa': True,
            'email_alertas_seguridad': True,
            'email_marketing': False,
            'email_notificaciones_sistema': True,
        }
    )
    return preferencias


def llamar_tarea_con_fallback(funcion_tarea, *args, **kwargs):
    """
    Ejecuta la tarea de forma asíncrona usando hilos para evitar bloquear la solicitud web.
    """
    def ejecutar_tarea():
        try:
            funcion_tarea(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error al ejecutar la tarea asíncrona {funcion_tarea.__name__}: {e}")
    
    # Iniciar la tarea en un hilo separado
    hilo = threading.Thread(target=ejecutar_tarea, daemon=True)
    hilo.start()
    return hilo


def enviar_email_confirmacion_ticket(id_ticket):
    """
    Envía un email de confirmación cuando se crea un ticket de soporte.
    """
    try:
        from .models import TicketSoporte
        
        ticket = TicketSoporte.objects.get(id=id_ticket)
        
        asunto = f"Ticket #{ticket.numero_ticket} - Confirmación de recepción"
        
        mensaje = f"""
Estimado/a {ticket.nombre_usuario},

Hemos recibido su consulta de soporte con el número de ticket: #{ticket.numero_ticket}

Detalles de su consulta:
- Asunto: {ticket.asunto}
- Categoría: {ticket.get_categoria_display()}
- Prioridad: {ticket.get_prioridad_display()}
- Fecha: {ticket.fecha_creacion.strftime('%d/%m/%Y %H:%M')}

Nuestro equipo de soporte revisará su consulta y le responderemos a la brevedad según la prioridad indicada.

Puede dar seguimiento a su ticket desde su cuenta en el sistema.

Saludos,
Equipo de Soporte de Global Exchange
        """
        
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[ticket.email_usuario],
            fail_silently=False
        )
        
        logger.info(f"Email de confirmación de ticket enviado para el ticket {id_ticket}")
        return f"Email de confirmación de ticket enviado para el ticket {id_ticket}"
        
    except Exception as e:
        logger.error(f"Error al enviar el email de confirmación del ticket: {e}")
        return f"Error al enviar el email de confirmación del ticket: {e}"


def enviar_notificacion_respuesta_ticket(id_mensaje):
    """
    Envía una notificación cuando alguien responde a un ticket.
    """
    try:
        from .models import MensajeTicket
        
        mensaje = MensajeTicket.objects.select_related('ticket', 'autor').get(id=id_mensaje)
        ticket = mensaje.ticket
        
        # Determinar el destinatario
        if mensaje.autor == ticket.usuario:
            # El usuario respondió, notificar al equipo de soporte
            emails_destinatarios = []
            if ticket.asignado_a:
                emails_destinatarios.append(ticket.asignado_a.email)
            else:
                # Enviar a todos los usuarios del personal
                from cuentas.models import Usuario
                emails_staff = Usuario.objects.filter(is_staff=True).values_list('email', flat=True)
                emails_destinatarios.extend(emails_staff)
        else:
            # El soporte respondió, notificar al usuario
            emails_destinatarios = [ticket.email_usuario]
        
        if not emails_destinatarios:
            return "No se encontraron destinatarios"
        
        asunto = f"Ticket #{ticket.numero_ticket} - Nueva respuesta"
        
        contenido_mensaje = f"""
Ticket #{ticket.numero_ticket} - {ticket.asunto}

Nueva respuesta de: {mensaje.autor.nombre_completo}
Fecha: {mensaje.fecha_creacion.strftime('%d/%m/%Y %H:%M')}

Mensaje:
{mensaje.mensaje}

---
Puede ver el ticket completo en el sistema.

Saludos,
Equipo de Global Exchange
        """
        
        send_mail(
            subject=asunto,
            message=contenido_mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=emails_destinatarios,
            fail_silently=False
        )
        
        logger.info(f"Notificación de respuesta de ticket enviada para el mensaje {id_mensaje}")
        return f"Notificación de respuesta de ticket enviada para el mensaje {id_mensaje}"
        
    except Exception as e:
        logger.error(f"Error al enviar la notificación de respuesta del ticket: {e}")
        return f"Error al enviar la notificación de respuesta del ticket: {e}"


def enviar_notificacion_cambio_tasa(codigo_moneda, tasa_anterior, tasa_nueva, cambio_porcentual):
    """
    Envía una notificación cuando las tasas de cambio cambian significativamente.
    """
    try:
        from .models import PreferenciaNotificacion, Notificacion, PlantillaNotificacion
        from cuentas.models import Usuario
        
        # Obtener usuarios que quieren alertas de tasas - asegurar que tengan preferencias
        todos_los_usuarios = Usuario.objects.filter(esta_activo=True)
        usuarios_quieren_alertas = []
        
        for usuario in todos_los_usuarios:
            preferencias = asegurar_preferencias_notificacion(usuario)
            if preferencias.email_alertas_tasa:
                usuarios_quieren_alertas.append(usuario)
        
        if not usuarios_quieren_alertas:
            return "Ningún usuario quiere alertas de tasas"
        
        # Obtener o crear plantilla de notificación
        plantilla, creado = PlantillaNotificacion.objects.get_or_create(
            tipo_plantilla='RATE_ALERT',
            defaults={
                'nombre': 'Alerta de Tasa de Cambio',
                'asunto_email': 'Alerta: Cambio significativo en {{codigo_moneda}}',
                'cuerpo_email_html': '''
                <h3>Alerta de Tasa de Cambio</h3>
                <p>La tasa de cambio para <strong>{{codigo_moneda}}</strong> ha cambiado significativamente:</p>
                <ul>
                    <li>Tasa anterior: {{tasa_anterior}}</li>
                    <li>Tasa actual: {{tasa_nueva}}</li>
                    <li>Cambio: {{cambio_porcentual}}%</li>
                </ul>
                <p>Puede ver las tasas actuales en nuestro sitio web.</p>
                <p>Saludos,<br/>Equipo de Global Exchange</p>
                ''',
                'cuerpo_email_texto': '''
Alerta de Tasa de Cambio

La tasa de cambio para {{codigo_moneda}} ha cambiado significativamente:

- Tasa anterior: {{tasa_anterior}}
- Tasa actual: {{tasa_nueva}}
- Cambio: {{cambio_porcentual}}%

Puede ver las tasas actuales en nuestro sitio web.

Saludos,
Equipo de Global Exchange
                '''
            }
        )
        
        # Crear notificaciones para cada usuario
        notificaciones_creadas = 0
        for usuario in usuarios_quieren_alertas:
            notificacion = Notificacion.objects.create(
                usuario=usuario,
                tipo_notificacion='EMAIL',
                plantilla=plantilla,
                asunto=f'Alerta: Cambio significativo en {codigo_moneda}',
                mensaje=f'La tasa de {codigo_moneda} cambió {cambio_porcentual}%',
                email_destinatario=usuario.email,
                datos_contexto={
                    'codigo_moneda': codigo_moneda,
                    'tasa_anterior': tasa_anterior,
                    'tasa_nueva': tasa_nueva,
                    'cambio_porcentual': cambio_porcentual
                }
            )
            
            # Enviar email
            llamar_tarea_con_fallback(enviar_notificacion_email, notificacion.id)
            notificaciones_creadas += 1
        
        logger.info(f"Notificaciones de cambio de tasa creadas: {notificaciones_creadas} para {codigo_moneda}")
        return f"Notificaciones de cambio de tasa creadas: {notificaciones_creadas} para {codigo_moneda}"
        
    except Exception as e:
        logger.error(f"Error al enviar notificaciones de cambio de tasa: {e}")
        return f"Error al enviar notificaciones de cambio de tasa: {e}"


def enviar_notificacion_actualizacion_tasa_manual(id_moneda, tasa_compra, tasa_venta, nombre_actualizador):
    """
    Envía una notificación cuando las tasas de cambio se actualizan manually.
    """
    try:
        from .models import PreferenciaNotificacion, Notificacion, PlantillaNotificacion
        from cuentas.models import Usuario
        from divisas.models import Moneda
        
        # Obtener información de la moneda
        moneda = Moneda.objects.get(id=id_moneda)
        
        # Obtener usuarios que quieren alertas de tasas - asegurar que tengan preferencias
        todos_los_usuarios = Usuario.objects.filter(esta_activo=True)
        usuarios_quieren_alertas = []
        
        for usuario in todos_los_usuarios:
            preferencias = asegurar_preferencias_notificacion(usuario)
            if preferencias.email_alertas_tasa:
                usuarios_quieren_alertas.append(usuario)
        
        if not usuarios_quieren_alertas:
            return "Ningún usuario quiere alertas de tasas"
        
        # Obtener o crear plantilla de notificación
        plantilla, creado = PlantillaNotificacion.objects.get_or_create(
            tipo_plantilla='RATE_ALERT',
            defaults={
                'nombre': 'Alerta de Actualización de Tasa',
                'asunto_email': 'Nueva tasa de cambio para {{nombre_moneda}}',
                'cuerpo_email_html': '''
                <h3>Actualización de Tasa de Cambio</h3>
                <p>Se ha actualizado la tasa de cambio para <strong>{{nombre_moneda}} ({{codigo_moneda}})</strong>:</p>
                <ul>
                    <li><strong>Tasa de Compra:</strong> {{tasa_compra}}</li>
                    <li><strong>Tasa de Venta:</strong> {{tasa_venta}}</li>
                    <li><strong>Actualizado por:</strong> {{actualizado_por}}</li>
                    <li><strong>Fecha:</strong> {{fecha_actualizacion}}</li>
                </ul>
                <p>Puede ver todas las tasas actuales en nuestro sitio web.</p>
                <p>Saludos,<br/>Equipo de Global Exchange</p>
                ''',
                'cuerpo_email_texto': '''
Actualización de Tasa de Cambio

Se ha actualizado la tasa de cambio para {{nombre_moneda}} ({{codigo_moneda}}):

- Tasa de Compra: {{tasa_compra}}
- Tasa de Venta: {{tasa_venta}}
- Actualizado por: {{actualizado_por}}
- Fecha: {{fecha_actualizacion}}

Puede ver todas las tasas actuales en nuestro sitio web.

Saludos,
Equipo de Global Exchange
                '''
            }
        )
        
        # Crear notificaciones para cada usuario
        notificaciones_creadas = 0
        hora_actualizacion = timezone.now()
        
        for usuario in usuarios_quieren_alertas:
            notificacion = Notificacion.objects.create(
                usuario=usuario,
                tipo_notificacion='EMAIL',
                plantilla=plantilla,
                asunto=f'Nueva tasa de cambio para {moneda.nombre}',
                mensaje=f'Se ha actualizado la tasa de {moneda.codigo}: Compra {tasa_compra}, Venta {tasa_venta}',
                email_destinatario=usuario.email,
                datos_contexto={
                    'nombre_moneda': moneda.nombre,
                    'codigo_moneda': moneda.codigo,
                    'tasa_compra': str(tasa_compra),
                    'tasa_venta': str(tasa_venta),
                    'actualizado_por': nombre_actualizador,
                    'fecha_actualizacion': hora_actualizacion.strftime('%d/%m/%Y %H:%M')
                }
            )
            
            # Enviar email
            llamar_tarea_con_fallback(enviar_notificacion_email, notificacion.id)
            notificaciones_creadas += 1
        
        logger.info(f"Notificaciones de actualización manual de tasa creadas: {notificaciones_creadas} para {moneda.codigo}")
        return f"Notificaciones de actualización manual de tasa creadas: {notificaciones_creadas} para {moneda.codigo}"
        
    except Exception as e:
        logger.error(f"Error al enviar notificaciones de actualización manual de tasa: {e}")
        return f"Error al enviar notificaciones de actualización manual de tasa: {e}"


def enviar_notificacion_transaccion(id_transaccion, tipo_notificacion='TRANSACTION_CREATED'):
    """
    Envía una notificación para eventos de transacción.
    """
    try:
        from transacciones.models import Transaccion
        from .models import Notificacion, PlantillaNotificacion
        
        transaccion = Transaccion.objects.select_related('cliente', 'moneda_origen', 'moneda_destino').get(id=id_transaccion)
        
        # Obtener usuarios asociados con el cliente y asegurar que tengan preferencias de notificación
        usuarios_cliente = transaccion.cliente.usuarios.filter(is_active=True)
        usuarios_a_notificar = []
        
        for usuario in usuarios_cliente:
            preferencias = asegurar_preferencias_notificacion(usuario)
            if preferencias.email_actualizaciones_transaccion:
                usuarios_a_notificar.append(usuario)
        
        if not usuarios_a_notificar:
            return "No hay usuarios para notificar (preferencias desactivadas)"
        
        # Obtener o crear la plantilla apropiada
        mapeo_plantillas = {
            'TRANSACTION_CREATED': 'TRANSACTION_CREATED',
            'TRANSACTION_COMPLETED': 'TRANSACTION_COMPLETED',
            'TRANSACTION_CANCELLED': 'TRANSACTION_CANCELLED'
        }
        
        tipo_plantilla = mapeo_plantillas.get(tipo_notificacion, 'TRANSACTION_CREATED')
        
        plantilla, creado = PlantillaNotificacion.objects.get_or_create(
            tipo_plantilla=tipo_plantilla,
            defaults={
                'nombre': 'Notificación de Transacción',
                'asunto_email': 'Transacción {{tipo_transaccion}} - {{moneda_origen}}/{{moneda_destino}}',
                'cuerpo_email_html': '''
                <h3>Notificación de Transacción</h3>
                <p>Su transacción ha sido {{accion_estado}}:</p>
                <ul>
                    <li>Tipo: {{tipo_transaccion}}</li>
                    <li>Moneda origen: {{moneda_origen}} - {{monto_origen}}</li>
                    <li>Moneda destino: {{moneda_destino}} - {{monto_destino}}</li>
                    <li>Estado: {{estado}}</li>
                    <li>Fecha: {{fecha_creacion}}</li>
                </ul>
                <p>Puede ver los detalles completos en su cuenta.</p>
                <p>Saludos,<br/>Equipo de Global Exchange</p>
                ''',
                'cuerpo_email_texto': '''
Notificación de Transacción

Su transacción ha sido {{accion_estado}}:

- Tipo: {{tipo_transaccion}}
- Moneda origen: {{moneda_origen}} - {{monto_origen}}
- Moneda destino: {{moneda_destino}} - {{monto_destino}}
- Estado: {{estado}}
- Fecha: {{fecha_creacion}}

Puede ver los detalles completos en su cuenta.

Saludos,
Equipo de Global Exchange
                '''
            }
        )
        
        # Determinar el texto de la acción del estado
        acciones_estado = {
            'TRANSACTION_CREATED': 'creada',
            'TRANSACTION_COMPLETED': 'completada',
            'TRANSACTION_CANCELLED': 'cancelada'
        }
        accion_estado = acciones_estado.get(tipo_notificacion, 'actualizada')
        
        # Crear notificaciones para cada usuario
        notificaciones_creadas = 0
        for usuario in usuarios_a_notificar:
            # Crear notificación por EMAIL
            notificacion_email = Notificacion.objects.create(
                usuario=usuario,
                tipo_notificacion='EMAIL',
                plantilla=plantilla,
                asunto=f'Transacción {transaccion.get_tipo_transaccion_display()} - {transaccion.moneda_origen.codigo}/{transaccion.moneda_destino.codigo}',
                mensaje=f'Su transacción ha sido {accion_estado}',
                email_destinatario=usuario.email,
                datos_contexto={
                    'numero_transaccion': transaccion.numero_transaccion,
                    'tipo_transaccion': transaccion.get_tipo_transaccion_display(),
                    'moneda_origen': transaccion.moneda_origen.codigo,
                    'moneda_destino': transaccion.moneda_destino.codigo,
                    'monto_origen': str(transaccion.monto_origen),
                    'monto_destino': str(transaccion.monto_destino),
                    'estado': transaccion.get_estado_display(),
                    'accion_estado': accion_estado,
                    'fecha_creacion': transaccion.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                    'id_transaccion': str(transaccion.id_transaccion)
                }
            )
            
            # Crear notificación IN_APP para mostrar en el sistema
            mensaje_in_app = f'Su transacción #{transaccion.numero_transaccion} de {transaccion.get_tipo_transaccion_display().lower()} de {transaccion.moneda_origen.codigo} ha sido {accion_estado}'
            if tipo_notificacion == 'TRANSACTION_CANCELLED' and transaccion.motivo_cancelacion:
                mensaje_in_app += f'. Motivo: {transaccion.motivo_cancelacion}'
            
            notificacion_in_app = Notificacion.objects.create(
                usuario=usuario,
                tipo_notificacion='IN_APP',
                plantilla=plantilla,
                asunto=f'Transacción {accion_estado.capitalize()}',
                mensaje=mensaje_in_app,
                estado='ENTREGADO',  # Las notificaciones in-app se marcan como entregadas inmediatamente
                datos_contexto={
                    'numero_transaccion': transaccion.numero_transaccion,
                    'tipo_transaccion': transaccion.get_tipo_transaccion_display(),
                    'moneda_origen': transaccion.moneda_origen.codigo,
                    'moneda_destino': transaccion.moneda_destino.codigo,
                    'monto_origen': str(transaccion.monto_origen),
                    'monto_destino': str(transaccion.monto_destino),
                    'estado': transaccion.get_estado_display(),
                    'accion_estado': accion_estado,
                    'fecha_creacion': transaccion.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                    'id_transaccion': str(transaccion.id_transaccion),
                    'url_detalle': f'/transacciones/detalle/{transaccion.id_transaccion}/'
                }
            )
            
            # Enviar email
            llamar_tarea_con_fallback(enviar_notificacion_email, notificacion_email.id)
            notificaciones_creadas += 2  # Email + IN_APP
        
        logger.info(f"Notificaciones de transacción creadas: {notificaciones_creadas} para la transacción {id_transaccion}")
        return f"Notificaciones de transacción creadas: {notificaciones_creadas} para la transacción {id_transaccion}"
        
    except Exception as e:
        logger.error(f"Error al enviar notificaciones de transacción: {e}")
        return f"Error al enviar notificaciones de transacción: {e}"


def enviar_notificacion_email(id_notificacion):
    """
    Envía una notificación por email.
    """
    try:
        from .models import Notificacion
        
        notificacion = Notificacion.objects.get(id=id_notificacion)
        
        # Comprobar preferencias del usuario - asegurar que existan
        preferencias = asegurar_preferencias_notificacion(notificacion.usuario)
        
        # Comprobar preferencia de frecuencia
        if preferencias.frecuencia_notificacion == 'NEVER':
            notificacion.estado = 'OMITIDO'
            notificacion.save()
            return "Email omitido debido a preferencias del usuario (NUNCA)"
        
        # Comprobar preferencias de tipo de notificación específico
        tipo_plantilla = notificacion.plantilla.tipo_plantilla if notificacion.plantilla else None
        
        if tipo_plantilla:
            mapeo_preferencias = {
                'TRANSACTION_CREATED': preferencias.email_actualizaciones_transaccion,
                'TRANSACTION_COMPLETED': preferencias.email_actualizaciones_transaccion,
                'TRANSACTION_CANCELLED': preferencias.email_actualizaciones_transaccion,
                'RATE_ALERT': preferencias.email_alertas_tasa,
                'REPORT_COMPLETED': preferencias.email_notificaciones_sistema,
                'EMAIL_VERIFICATION': preferencias.email_notificaciones_sistema,
                'PASSWORD_RESET': preferencias.email_notificaciones_sistema,
                'ACCOUNT_LOCKED': preferencias.email_alertas_seguridad,
                'LOGIN_NOTIFICATION': preferencias.email_alertas_seguridad,
            }
            
            if tipo_plantilla in mapeo_preferencias and not mapeo_preferencias[tipo_plantilla]:
                notificacion.estado = 'OMITIDO'
                notificacion.save()
                return f"Email omitido debido a preferencias del usuario ({tipo_plantilla})"
        
        # Renderizar plantilla
        if notificacion.plantilla:
            plantilla_asunto = Template(notificacion.plantilla.asunto_email)
            plantilla_cuerpo = Template(notificacion.plantilla.cuerpo_email_texto)
            
            contexto = Context(notificacion.datos_contexto)
            asunto = plantilla_asunto.render(contexto)
            mensaje = plantilla_cuerpo.render(contexto)
        else:
            asunto = notificacion.asunto
            mensaje = notificacion.mensaje
        
        # Enviar email
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@globalexchange.com',
            recipient_list=[notificacion.email_destinatario],
            fail_silently=False
        )
        
        notificacion.estado = 'ENVIADO'
        notificacion.fecha_envio = timezone.now()
        notificacion.save()
        
        logger.info(f"Notificación por email {id_notificacion} enviada exitosamente a {notificacion.email_destinatario}")
        return f"Notificación por email {id_notificacion} enviada exitosamente"
        
    except Exception as e:
        logger.error(f"Error al enviar la notificación por email {id_notificacion}: {e}")
        
        try:
            notificacion = Notificacion.objects.get(id=id_notificacion)
            notificacion.estado = 'FALLIDO'
            notificacion.mensaje_error = str(e)
            notificacion.conteo_reintentos += 1
            notificacion.save()
        except:
            pass
        
        return f"Error al enviar la notificación por email {id_notificacion}: {e}"


def limpiar_notificaciones_antiguas():
    """
    Limpia las notificaciones antiguas.
    """
    try:
        from datetime import timedelta
        from .models import Notificacion
        
        # Eliminar notificaciones con más de 6 meses de antigüedad
        fecha_corte = timezone.now() - timedelta(days=180)
        
        notificaciones_antiguas = Notificacion.objects.filter(
            fecha_creacion__lt=fecha_corte,
            estado__in=['ENVIADO', 'ENTREGADO', 'LEIDO', 'FALLIDO']
        )
        
        conteo = notificaciones_antiguas.count()
        notificaciones_antiguas.delete()
        
        logger.info(f"Se limpiaron {conteo} notificaciones antiguas")
        return f"Se limpiaron {conteo} notificaciones antiguas"
        
    except Exception as e:
        logger.error(f"Error al limpiar notificaciones antiguas: {e}")
        return f"Error al limpiar notificaciones antiguas: {e}"


def procesar_cola_notificaciones():
    """
    Procesa las notificaciones pendientes.
    """
    try:
        from .models import Notificacion
        
        notificaciones_pendientes = Notificacion.objects.filter(
            estado='PENDIENTE'
        ).order_by('fecha_creacion')[:50]  # Procesar en lotes
        
        procesadas = 0
        for notificacion in notificaciones_pendientes:
            if notificacion.tipo_notificacion == 'EMAIL':
                llamar_tarea_con_fallback(enviar_notificacion_email, notificacion.id)
                procesadas += 1
        
        logger.info(f"Se encolaron {procesadas} notificaciones para su procesamiento")
        return f"Se encolaron {procesadas} notificaciones para su procesamiento"
        
    except Exception as e:
        logger.error(f"Error al procesar la cola de notificaciones: {e}")
        return f"Error al procesar la cola de notificaciones: {e}"
