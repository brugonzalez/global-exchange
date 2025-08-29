from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, CreateView, DetailView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
import json

from .models import (
    Notificacion, PreferenciaNotificacion, TicketSoporte, 
    MensajeTicket, PlantillaNotificacion
)
from .forms import (
    FormularioTicketSoporte, FormularioRespuestaTicket, FormularioPreferenciasNotificacion
)


class VistaListaNotificaciones(LoginRequiredMixin, ListView):
    """
    Lista las notificaciones del usuario.
    """
    model = Notificacion
    template_name = 'notificaciones/lista_notificaciones.html'
    context_object_name = 'notificaciones'
    paginate_by = 20

    def get_queryset(self):
        consulta = Notificacion.objects.filter(
            usuario=self.request.user
        ).select_related('plantilla').order_by('-fecha_creacion')
        
        # Aplicar filtros basados en los parámetros de la URL
        tipo_filtro = self.request.GET.get('filtro', 'todas')
        
        if tipo_filtro == 'no_leidas':
            consulta = consulta.filter(estado__in=['ENVIADO', 'ENTREGADO'])
        elif tipo_filtro == 'transacciones':
            consulta = consulta.filter(
                plantilla__tipo_plantilla__icontains='TRANSACTION'
            )
        elif tipo_filtro == 'tasas':
            consulta = consulta.filter(
                plantilla__tipo_plantilla='RATE_ALERT'
            )
        # 'todas' no necesita filtrado adicional
        
        return consulta
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['filtro_actual'] = self.request.GET.get('filtro', 'todas')
        return contexto


class VistaMarcarComoLeido(LoginRequiredMixin, TemplateView):
    """
    Marca una notificación como leída.
    """
    def post(self, solicitud, *args, **kwargs):
        try:
            id_notificacion = kwargs.get('id_notificacion')
            notificacion = get_object_or_404(
                Notificacion, 
                id=id_notificacion, 
                usuario=solicitud.user
            )
            
            notificacion.marcar_como_leida()
            
            return JsonResponse({
                'success': True,
                'message': 'Notificación marcada como leída'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class VistaPreferenciasNotificacion(LoginRequiredMixin, FormView):
    """
    Gestiona las preferencias de notificación.
    """
    template_name = 'notificaciones/preferencias.html'
    form_class = FormularioPreferenciasNotificacion
    success_url = reverse_lazy('notificaciones:preferencias')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        # Obtener o crear preferencias
        preferencias, creado = PreferenciaNotificacion.objects.get_or_create(
            usuario=self.request.user
        )
        kwargs['instance'] = preferencias
        
        return kwargs

    def form_valid(self, formulario):
        formulario.save()
        messages.success(self.request, 'Preferencias de notificación actualizadas.')
        return super().form_valid(formulario)


class VistaActualizarPreferencias(LoginRequiredMixin, TemplateView):
    """
    Endpoint de API para actualizar las preferencias.
    """
    def post(self, solicitud, *args, **kwargs):
        try:
            datos = json.loads(solicitud.body)
            
            preferencias, creado = PreferenciaNotificacion.objects.get_or_create(
                usuario=solicitud.user
            )
            
            # Actualizar preferencias basadas en los datos
            for clave, valor in datos.items():
                if hasattr(preferencias, clave):
                    setattr(preferencias, clave, valor)
            
            preferencias.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Preferencias actualizadas'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


# Vistas del Sistema de Soporte

class VistaSoporte(TemplateView):
    """
    Página principal de soporte con recursos de ayuda.
    """
    template_name = 'notificaciones/soporte.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Añadir datos de preguntas frecuentes
        contexto['preguntas_frecuentes'] = [
            {
                'pregunta': '¿Cómo registro una cuenta?',
                'respuesta': 'Para registrar una cuenta, haga clic en "Registrarse" en la parte superior de la página y complete el formulario con sus datos. Recibirá un email de verificación para activar su cuenta.'
            },
            {
                'pregunta': '¿Cómo realizo una transacción?',
                'respuesta': 'Para realizar transacciones debe tener una cuenta verificada y estar asociado a un cliente. Vaya a la sección de transacciones y seleccione comprar o vender divisas.'
            },
            {
                'pregunta': '¿Qué métodos de pago aceptan?',
                'respuesta': 'Aceptamos transferencias bancarias, billeteras digitales (MercadoPago) y tarjetas de débito. Los métodos disponibles pueden variar según su tipo de cliente.'
            },
            {
                'pregunta': '¿Cómo activo la autenticación de dos factores?',
                'respuesta': 'Vaya a su perfil de usuario, sección "Seguridad", y haga clic en "Configurar 2FA". Necesitará una aplicación autenticadora como Google Authenticator.'
            },
            {
                'pregunta': '¿Las tasas de cambio se actualizan en tiempo real?',
                'respuesta': 'Sí, nuestras tasas de cambio se actualizan manualmente por nuestros administradores durante el horario de operación.'
            },
            {
                'pregunta': '¿Cómo genero un reporte de mis transacciones?',
                'respuesta': 'Vaya a la sección "Reportes" en su panel de usuario. Puede generar reportes en PDF o Excel con diferentes filtros de fecha y moneda.'
            }
        ]
        
        # Añadir guías de solución de problemas
        contexto['solucion_problemas'] = [
            {
                'problema': 'No puedo iniciar sesión',
                'soluciones': [
                    'Verifique que su email esté correctamente escrito',
                    'Asegúrese de que su cuenta esté verificada (revise su email)',
                    'Si olvidó su contraseña, use la opción "Recuperar contraseña"',
                    'Su cuenta puede estar bloqueada temporalmente por intentos fallidos'
                ]
            },
            {
                'problema': 'No recibo emails de verificación',
                'soluciones': [
                    'Revise su carpeta de spam/correo no deseado',
                    'Verifique que el email esté correctamente escrito',
                    'Agregue noreply@globalexchange.com a sus contactos',
                    'Contacte soporte si no recibe el email en 24 horas'
                ]
            },
            {
                'problema': 'Error al realizar transacciones',
                'soluciones': [
                    'Verifique que esté asociado a un cliente',
                    'Confirme que los montos estén dentro de sus límites',
                    'Asegúrese de tener saldo suficiente',
                    'Revise que el método de pago esté disponible'
                ]
            }
        ]
        
        return contexto


class VistaCrearTicket(CreateView):
    """
    Crea un ticket de soporte.
    """
    model = TicketSoporte
    form_class = FormularioTicketSoporte
    template_name = 'notificaciones/crear_ticket.html'
    success_url = reverse_lazy('notificaciones:lista_tickets')

    def form_valid(self, formulario):
        # Establecer información del usuario
        if self.request.user.is_authenticated:
            formulario.instance.usuario = self.request.user
            formulario.instance.email_usuario = self.request.user.email
            formulario.instance.nombre_usuario = self.request.user.nombre_completo
        
        respuesta = super().form_valid(formulario)
        
        messages.success(
            self.request, 
            f'Ticket #{self.object.numero_ticket} creado exitosamente. '
            'Recibirá una respuesta por email.'
        )
        
        # Enviar email de confirmación
        try:
            from .tasks import enviar_email_confirmacion_ticket, llamar_tarea_con_fallback
            llamar_tarea_con_fallback(enviar_email_confirmacion_ticket, self.object.id)
        except Exception:
            pass  # Fallar silenciosamente si el sistema de notificaciones no está disponible
        
        return respuesta

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user if self.request.user.is_authenticated else None
        return kwargs


class VistaListaTickets(LoginRequiredMixin, ListView):
    """
    Lista los tickets de soporte del usuario.
    """
    model = TicketSoporte
    template_name = 'notificaciones/lista_tickets.html'
    context_object_name = 'tickets'
    paginate_by = 20

    def get_queryset(self):
        return TicketSoporte.objects.filter(
            usuario=self.request.user
        ).prefetch_related('mensajes').order_by('-fecha_creacion')


class VistaDetalleTicket(LoginRequiredMixin, DetailView):
    """
    Ve los detalles de un ticket de soporte.
    """
    model = TicketSoporte
    template_name = 'notificaciones/detalle_ticket.html'
    context_object_name = 'ticket'

    def get_object(self, queryset=None):
        return get_object_or_404(
            self.get_queryset(),
            numero_ticket=self.kwargs.get('numero_ticket')
        )

    def get_queryset(self):
        return TicketSoporte.objects.filter(usuario=self.request.user)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener mensajes del ticket
        contexto['mensajes'] = self.object.mensajes.filter(
            es_interno=False
        ).select_related('autor').order_by('fecha_creacion')
        
        # Añadir formulario de respuesta
        contexto['formulario_respuesta'] = FormularioRespuestaTicket()
        
        return contexto


class VistaResponderTicket(LoginRequiredMixin, FormView):
    """
    Responde a un ticket de soporte.
    """
    form_class = FormularioRespuestaTicket
    
    def dispatch(self, solicitud, *args, **kwargs):
        self.ticket = get_object_or_404(
            TicketSoporte,
            numero_ticket=kwargs.get('numero_ticket'),
            usuario=solicitud.user
        )
        return super().dispatch(solicitud, *args, **kwargs)
    
    def form_valid(self, formulario):
        # Crear mensaje del ticket
        mensaje = MensajeTicket.objects.create(
            ticket=self.ticket,
            autor=self.request.user,
            mensaje=formulario.cleaned_data['mensaje'],
            es_interno=False
        )
        
        # Actualizar el estado del ticket si estaba resuelto
        if self.ticket.estado == 'RESUELTO':
            self.ticket.estado = 'ABIERTO'
            self.ticket.save()
        
        messages.success(self.request, 'Respuesta enviada correctamente.')
        
        # Enviar notificación al equipo de soporte
        try:
            from .tasks import enviar_notificacion_respuesta_ticket, llamar_tarea_con_fallback
            llamar_tarea_con_fallback(enviar_notificacion_respuesta_ticket, mensaje.id)
        except Exception:
            pass  # Fallar silenciosamente si el sistema de notificaciones no está disponible
        
        return redirect('notificaciones:detalle_ticket', numero_ticket=self.ticket.numero_ticket)
    
    def form_invalid(self, formulario):
        messages.error(self.request, 'Error al enviar la respuesta.')
        return redirect('notificaciones:detalle_ticket', numero_ticket=self.ticket.numero_ticket)


class APIVistaConteoNoLeidas(LoginRequiredMixin, TemplateView):
    """
    Endpoint de API para el conteo de notificaciones no leídas.
    """
    def get(self, solicitud, *args, **kwargs):
        try:
            conteo_no_leidas = Notificacion.objects.filter(
                usuario=solicitud.user,
                estado__in=['ENVIADO', 'ENTREGADO']
            ).count()
            
            # También contar tickets abiertos
            tickets_abiertos = TicketSoporte.objects.filter(
                usuario=solicitud.user,
                estado__in=['ABIERTO', 'EN_PROGRESO']
            ).count()
            
            return JsonResponse({
                'success': True,
                'notificaciones_no_leidas': conteo_no_leidas,
                'tickets_abiertos': tickets_abiertos,
                'total': conteo_no_leidas + tickets_abiertos
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


# Vistas de administración para la gestión de soporte

class VistaAdminListaTickets(LoginRequiredMixin, ListView):
    """
    Vista de administración para gestionar todos los tickets.
    """
    model = TicketSoporte
    template_name = 'notificaciones/admin_lista_tickets.html'
    context_object_name = 'tickets'
    paginate_by = 50

    def dispatch(self, solicitud, *args, **kwargs):
        if not solicitud.user.is_staff:
            raise Http404("Página no encontrada")
        return super().dispatch(solicitud, *args, **kwargs)

    def get_queryset(self):
        consulta = TicketSoporte.objects.all().select_related(
            'usuario', 'asignado_a', 'resuelto_por'
        ).prefetch_related('mensajes')
        
        # Aplicar filtros
        estado = self.request.GET.get('estado')
        if estado:
            consulta = consulta.filter(estado=estado)
        
        categoria = self.request.GET.get('categoria')
        if categoria:
            consulta = consulta.filter(categoria=categoria)
        
        prioridad = self.request.GET.get('prioridad')
        if prioridad:
            consulta = consulta.filter(prioridad=prioridad)
        
        return consulta.order_by('-fecha_creacion')

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Añadir opciones de filtro
        contexto['opciones_estado'] = TicketSoporte.ESTADOS
        contexto['opciones_categoria'] = TicketSoporte.CATEGORIAS
        contexto['opciones_prioridad'] = TicketSoporte.PRIORIDADES
        
        # Añadir filtros actuales
        contexto['filtros_actuales'] = {
            'estado': self.request.GET.get('estado', ''),
            'categoria': self.request.GET.get('categoria', ''),
            'prioridad': self.request.GET.get('prioridad', ''),
        }
        
        return contexto