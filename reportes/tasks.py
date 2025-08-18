import threading
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
import logging
import os
import io
from decimal import Decimal, InvalidOperation

from .models import Reporte
from .views import APIVistaGenerarReporte

logger = logging.getLogger(__name__)


def generar_reporte_sincrono(id_reporte):
    """
    Versión síncrona de la generación de reportes
    """
    try:
        reporte = Reporte.objects.get(id=id_reporte)
        reporte.estado = 'GENERANDO'
        reporte.fecha_inicio = timezone.now()
        reporte.save()

        # Generar contenido del reporte basado en el tipo y formato
        from .views import APIVistaGenerarReporte
        generador = APIVistaGenerarReporte()
        
        if reporte.tipo_reporte == 'HISTORIAL_TRANSACCIONES':
            # Obtener transacciones para el reporte
            from transacciones.models import Transaccion
            
            transacciones = Transaccion.objects.filter(
                fecha_creacion__range=[reporte.fecha_desde, reporte.fecha_hasta]
            )
            
            # Aplicar filtro de cliente si se especifica
            if reporte.cliente:
                transacciones = transacciones.filter(cliente=reporte.cliente)
            
            # Aplicar filtros adicionales
            if reporte.filtros:
                if reporte.filtros.get('moneda'):
                    transacciones = transacciones.filter(
                        moneda_origen__codigo=reporte.filtros["moneda"]
                    )
                if reporte.filtros.get('estado'):
                    transacciones = transacciones.filter(
                        estado=reporte.filtros['estado']
                    )
            
            # Generar contenido basado en el formato
            if reporte.formato == 'PDF':
                contenido = generador._generar_pdf_transacciones(
                    transacciones, reporte.fecha_desde, reporte.fecha_hasta
                )
                nombre_archivo = f'{reporte.nombre_reporte}.pdf'
                
            elif reporte.formato == 'EXCEL':
                contenido = generador._generar_excel_transacciones(
                    transacciones, reporte.fecha_desde, reporte.fecha_hasta
                )
                nombre_archivo = f'{reporte.nombre_reporte}.xlsx'
                
            else:
                raise ValueError(f"Formato no soportado: {reporte.formato}")
            
            # Guardar archivo
            contenido_archivo = ContentFile(contenido)
            reporte.ruta_archivo.save(nombre_archivo, contenido_archivo, save=False)
            reporte.tamano_archivo = len(contenido)
            
        elif reporte.tipo_reporte == 'TASAS_CAMBIO':
            # Obtener tasas de cambio para el reporte
            from divisas.models import TasaCambio
            
            tasas = TasaCambio.objects.filter(
                fecha_creacion__range=[reporte.fecha_desde, reporte.fecha_hasta]
            ).select_related('moneda', 'moneda_base')
            
            # Aplicar filtros adicionales
            if reporte.filtros:
                if reporte.filtros.get('moneda'):
                    tasas = tasas.filter(
                        moneda__codigo=reporte.filtros["moneda"]
                    )
            
            # Generar contenido basado en el formato
            if reporte.formato == 'PDF':
                contenido = generador._generar_pdf_tasas_cambio(
                    tasas, reporte.fecha_desde, reporte.fecha_hasta
                )
                nombre_archivo = f'{reporte.nombre_reporte}.pdf'
                
            elif reporte.formato == 'EXCEL':
                contenido = generador._generar_excel_tasas_cambio(
                    tasas, reporte.fecha_desde, reporte.fecha_hasta
                )
                nombre_archivo = f'{reporte.nombre_reporte}.xlsx'
                
            else:
                raise ValueError(f"Formato no soportado: {reporte.formato}")
            
            # Guardar archivo
            contenido_archivo = ContentFile(contenido)
            reporte.ruta_archivo.save(nombre_archivo, contenido_archivo, save=False)
            reporte.tamano_archivo = len(contenido)
            
        else:
            raise ValueError(f"Tipo de reporte no soportado: {reporte.tipo_reporte}")
        
        # Marcar como completado
        reporte.estado = 'COMPLETADO'
        reporte.fecha_finalizacion = timezone.now()
        reporte.save()
        
        logger.info(f"Reporte {reporte.id} generado exitosamente (síncrono)")
        return f"Reporte {reporte.id} generado exitosamente (síncrono)"
        
    except Reporte.DoesNotExist:
        logger.error(f"Reporte {id_reporte} no encontrado")
        return f"Reporte {id_reporte} no encontrado"
        
    except (InvalidOperation, TypeError, ValueError) as e:
        logger.error(f"Error decimal al generar el reporte {id_reporte} (síncrono): {e}")
        
        # Marcar como fallido con mensaje específico
        try:
            reporte = Reporte.objects.get(id=id_reporte)
            reporte.estado = 'FALLIDO'
            reporte.mensaje_error = f"Error en operaciones decimales: {str(e)}"
            reporte.save()
        except:
            pass
        
        return f"Error decimal al generar el reporte {id_reporte} (síncrono): {e}"
        
    except Exception as e:
        logger.error(f"Error al generar el reporte {id_reporte} (síncrono): {e}")
        
        # Marcar como fallido
        try:
            reporte = Reporte.objects.get(id=id_reporte)
            reporte.estado = 'FALLIDO'
            reporte.mensaje_error = str(e)
            reporte.save()
        except:
            pass
        
        return f"Error al generar el reporte {id_reporte} (síncrono): {e}"


def tarea_generar_reporte(id_reporte):
    """
    Tarea asíncrona para generar reportes.
    """
    try:
        reporte = Reporte.objects.get(id=id_reporte)
        reporte.estado = 'GENERANDO'
        reporte.fecha_inicio = timezone.now()
        reporte.save()

        # Generar contenido del reporte basado en el tipo y formato
        generador = APIVistaGenerarReporte()
        
        if reporte.tipo_reporte == 'HISTORIAL_TRANSACCIONES':
            # Obtener transacciones para el reporte
            from transacciones.models import Transaccion
            
            transacciones = Transaccion.objects.filter(
                fecha_creacion__range=[reporte.fecha_desde, reporte.fecha_hasta]
            )
            
            # Aplicar filtro de cliente si se especifica
            if reporte.cliente:
                transacciones = transacciones.filter(cliente=reporte.cliente)
            
            # Aplicar filtros adicionales
            if reporte.filtros:
                if reporte.filtros.get('moneda'):
                    transacciones = transacciones.filter(
                        moneda_origen__codigo=reporte.filtros["moneda"]
                    )
                if reporte.filtros.get('estado'):
                    transacciones = transacciones.filter(
                        estado=reporte.filtros['estado']
                    )
            
            # Generar contenido basado en el formato
            if reporte.formato == 'PDF':
                contenido = generador._generar_pdf_transacciones(
                    transacciones, reporte.fecha_desde, reporte.fecha_hasta
                )
                nombre_archivo = f'{reporte.nombre_reporte}.pdf'
                
            elif reporte.formato == 'EXCEL':
                contenido = generador._generar_excel_transacciones(
                    transacciones, reporte.fecha_desde, reporte.fecha_hasta
                )
                nombre_archivo = f'{reporte.nombre_reporte}.xlsx'
                
            else:
                raise ValueError(f"Formato no soportado: {reporte.formato}")
            
            # Guardar archivo
            contenido_archivo = ContentFile(contenido)
            reporte.ruta_archivo.save(nombre_archivo, contenido_archivo, save=False)
            reporte.tamano_archivo = len(contenido)
            
        elif reporte.tipo_reporte == 'TASAS_CAMBIO':
            # Obtener tasas de cambio para el reporte
            from divisas.models import TasaCambio
            
            tasas = TasaCambio.objects.filter(
                fecha_creacion__range=[reporte.fecha_desde, reporte.fecha_hasta]
            ).select_related('moneda', 'moneda_base')
            
            # Aplicar filtros adicionales
            if reporte.filtros:
                if reporte.filtros.get('moneda'):
                    tasas = tasas.filter(
                        moneda__codigo=reporte.filtros["moneda"]
                    )
            
            # Generar contenido basado en el formato
            if reporte.formato == 'PDF':
                contenido = generador._generar_pdf_tasas_cambio(
                    tasas, reporte.fecha_desde, reporte.fecha_hasta
                )
                nombre_archivo = f'{reporte.nombre_reporte}.pdf'
                
            elif reporte.formato == 'EXCEL':
                contenido = generador._generar_excel_tasas_cambio(
                    tasas, reporte.fecha_desde, reporte.fecha_hasta
                )
                nombre_archivo = f'{reporte.nombre_reporte}.xlsx'
                
            else:
                raise ValueError(f"Formato no soportado: {reporte.formato}")
            
            # Guardar archivo
            contenido_archivo = ContentFile(contenido)
            reporte.ruta_archivo.save(nombre_archivo, contenido_archivo, save=False)
            reporte.tamano_archivo = len(contenido)
            
        else:
            raise ValueError(f"Tipo de reporte no soportado: {reporte.tipo_reporte}")
        
        # Marcar como completado
        reporte.estado = 'COMPLETADO'
        reporte.fecha_finalizacion = timezone.now()
        reporte.save()
        
        # Enviar notificación al usuario
        def notificar_finalizacion():
            try:
                enviar_notificacion_reporte_completado(reporte.id)
            except Exception as e:
                logger.error(f"Error al enviar la notificación de reporte completado: {e}")
        
        # Enviar notificación en un hilo separado
        hilo_notificacion = threading.Thread(target=notificar_finalizacion, daemon=True)
        hilo_notificacion.start()
        
        logger.info(f"Reporte {reporte.id} generado exitosamente")
        return f"Reporte {reporte.id} generado exitosamente"
        
    except Reporte.DoesNotExist:
        logger.error(f"Reporte {id_reporte} no encontrado")
        return f"Reporte {id_reporte} no encontrado"
        
    except (InvalidOperation, TypeError, ValueError) as e:
        logger.error(f"Error decimal al generar el reporte {id_reporte}: {e}")
        
        # Marcar como fallido con mensaje específico
        try:
            reporte = Reporte.objects.get(id=id_reporte)
            reporte.estado = 'FALLIDO'
            reporte.mensaje_error = f"Error en operaciones decimales: {str(e)}"
            reporte.save()
        except:
            pass
        
        return f"Error decimal al generar el reporte {id_reporte}: {e}"
        
    except Exception as e:
        logger.error(f"Error al generar el reporte {id_reporte}: {e}")
        
        # Marcar como fallido
        try:
            reporte = Reporte.objects.get(id=id_reporte)
            reporte.estado = 'FALLIDO'
            reporte.mensaje_error = str(e)
            reporte.save()
        except:
            pass
        
        return f"Error al generar el reporte {id_reporte}: {e}"


def enviar_notificacion_reporte_completado(id_reporte):
    """
    Envía una notificación cuando un reporte se completa.
    """
    try:
        reporte = Reporte.objects.get(id=id_reporte)
        
        # Importar aquí para evitar importaciones circulares
        from notificaciones.models import Notificacion, PlantillaNotificacion
        
        # Obtener o crear plantilla de notificación
        plantilla, creado = PlantillaNotificacion.objects.get_or_create(
            tipo_plantilla='REPORTE_COMPLETADO',
            defaults={
                'nombre': 'Reporte Completado',
                'asunto_email': 'Su reporte está listo para descargar',
                'cuerpo_email_html': '''
                <h2>Reporte Completado</h2>
                <p>Estimado/a {{nombre_usuario}},</p>
                <p>Su reporte "{{nombre_reporte}}" ha sido generado exitosamente.</p>
                <p><strong>Detalles del reporte:</strong></p>
                <ul>
                    <li>Tipo: {{tipo_reporte}}</li>
                    <li>Formato: {{formato}}</li>
                    <li>Período: {{fecha_desde}} - {{fecha_hasta}}</li>
                    <li>Tamaño: {{tamano_archivo}} bytes</li>
                </ul>
                <p>Puede descargar su reporte desde el panel de reportes.</p>
                <p>Saludos,<br/>Equipo de Global Exchange</p>
                ''',
                'cuerpo_email_texto': '''
Reporte Completado

Estimado/a {{nombre_usuario}},

Su reporte "{{nombre_reporte}}" ha sido generado exitosamente.

Detalles del reporte:
- Tipo: {{tipo_reporte}}
- Formato: {{formato}}
- Período: {{fecha_desde}} - {{fecha_hasta}}
- Tamaño: {{tamano_archivo}} bytes

Puede descargar su reporte desde el panel de reportes.

Saludos,
Equipo de Global Exchange
                '''
            }
        )
        
        # Crear notificación
        notificacion = Notificacion.objects.create(
            usuario=reporte.solicitado_por,
            tipo_notificacion='EMAIL',
            plantilla=plantilla,
            asunto=f'Reporte "{reporte.nombre_reporte}" completado',
            mensaje=f'Su reporte "{reporte.nombre_reporte}" está listo para descargar.',
            email_destinatario=reporte.solicitado_por.email,
            datos_contexto={
                'nombre_usuario': reporte.solicitado_por.nombre_completo,
                'nombre_reporte': reporte.nombre_reporte,
                'tipo_reporte': reporte.get_tipo_reporte_display(),
                'formato': reporte.formato,
                'fecha_desde': reporte.fecha_desde.strftime('%d/%m/%Y'),
                'fecha_hasta': reporte.fecha_hasta.strftime('%d/%m/%Y'),
                'tamano_archivo': reporte.tamano_archivo
            }
        )
        
        # Enviar notificación por email en un hilo separado
        def enviar_email():
            try:
                enviar_notificacion_email(notificacion.id)
            except Exception as e:
                logger.error(f"Error al enviar la notificación por email: {e}")
        
        hilo_email = threading.Thread(target=enviar_email, daemon=True)
        hilo_email.start()
        
        logger.info(f"Notificación de reporte completado enviada para el reporte {id_reporte}")
        
    except Exception as e:
        logger.error(f"Error al enviar la notificación de reporte completado: {e}")


def enviar_notificacion_email(id_notificacion):
    """
    Envía una notificación por email.
    """
    try:
        from notificaciones.models import Notificacion
        from django.core.mail import send_mail
        from django.template import Template, Context
        
        notificacion = Notificacion.objects.get(id=id_notificacion)
        
        # Comprobar preferencias del usuario
        if hasattr(notificacion.usuario, 'preferencias_notificacion'):
            preferencias = notificacion.usuario.preferencias_notificacion
            
            # Comprobar si el usuario quiere notificaciones por email para este tipo
            if notificacion.plantilla and notificacion.plantilla.tipo_plantilla == 'REPORTE_COMPLETADO':
                if not preferencias.email_notificaciones_sistema:
                    notificacion.estado = 'OMITIDO'
                    notificacion.save()
                    return "Email omitido debido a preferencias del usuario"
        
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
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notificacion.email_destinatario],
            fail_silently=False
        )
        
        notificacion.estado = 'ENVIADO'
        notificacion.fecha_envio = timezone.now()
        notificacion.save()
        
        logger.info(f"Notificación por email {id_notificacion} enviada exitosamente")
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


def limpiar_reportes_expirados():
    """
    Limpia los reportes expirados.
    """
    try:
        ahora = timezone.now()
        reportes_expirados = Reporte.objects.filter(
            fecha_expiracion__lt=ahora,
            estado='COMPLETADO'
        )
        
        conteo = 0
        for reporte in reportes_expirados:
            if reporte.ruta_archivo:
                try:
                    os.remove(reporte.ruta_archivo.path)
                except OSError:
                    pass
            
            reporte.delete()
            conteo += 1
        
        logger.info(f"Se limpiaron {conteo} reportes expirados")
        return f"Se limpiaron {conteo} reportes expirados"
        
    except Exception as e:
        logger.error(f"Error al limpiar reportes expirados: {e}")
        return f"Error al limpiar reportes expirados: {e}"