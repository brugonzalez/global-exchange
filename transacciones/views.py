from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, Http404, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db import models
from django.urls import reverse
from decimal import Decimal
from django.conf import settings
import csv
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .models import Transaccion, SimulacionTransaccion, Factura
from .forms import FormularioCancelarTransaccion, FormularioTransaccion, FormularioPagoStripe
from .payments import ProcesadorPagos, crear_intento_pago_stripe
from divisas.models import Moneda, TasaCambio
from cuentas.views import MixinPermisosAdmin

class VistaTransaccionCompra(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Vista para crear transacciones de compra.
    """
    template_name = 'transacciones/transaccion_compra.html'
    permiso_requerido = 'solicitar_cambio_compra'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Comprobar si el usuario tiene un cliente seleccionado
        if not self.request.user.ultimo_cliente_seleccionado and not self.request.user.clientes.exists():
            contexto['advertencia_sin_cliente'] = True
            contexto['formulario'] = None
        else:
            contexto['formulario'] = FormularioTransaccion(transaction_type='COMPRA', user=self.request.user)
            contexto['cliente_activo'] = self.request.user.ultimo_cliente_seleccionado
            # Añadir clave pública de Stripe para el frontend
            contexto['stripe_clave_publicable'] = settings.STRIPE_CLAVE_PUBLICABLE
            contexto['moneda_base'] = Moneda.objects.get(es_moneda_base=True)
            
        return contexto
    
    def post(self, solicitud, *args, **kwargs):
        # Comprobar si el usuario tiene acceso a clientes
        if not solicitud.user.ultimo_cliente_seleccionado and not solicitud.user.clientes.exists():
            messages.error(
                solicitud, 
                'Debe tener un cliente asignado para realizar transacciones.'
            )
            return redirect('clientes:lista_clientes')
        
        formulario = FormularioTransaccion(solicitud.POST, transaction_type='COMPRA', user=solicitud.user)
        
        if formulario.is_valid():
            # Obtener el cliente - ya sea del formulario o del cliente seleccionado por el usuario
            cliente = formulario.cleaned_data.get('cliente') or solicitud.user.ultimo_cliente_seleccionado
            
            if not cliente:
                messages.error(solicitud, 'No se pudo determinar el cliente para la transacción.')
                contexto = self.get_context_data(**kwargs)
                contexto['formulario'] = formulario
                return self.render_to_response(contexto)
            
            # Obtener tasa de cambio (implementación de ejemplo)
            # En una implementación real, esto se obtendría del modelo TasaCambio
            from decimal import Decimal
            tasa_ejemplo = Decimal('7500.00')  # Tasa de ejemplo
            
            # Calcular monto de destino
            monto_destino = formulario.cleaned_data['monto_origen'] * tasa_ejemplo
            
            # Crear transacción usando método seguro
            objeto_transaccion = Transaccion.objects.create_safe(
                tipo_transaccion='COMPRA',
                cliente=cliente,
                usuario=solicitud.user,
                moneda_origen=formulario.cleaned_data['moneda_origen'],
                moneda_destino=formulario.cleaned_data['moneda_destino'],
                monto_origen=formulario.cleaned_data['monto_origen'],
                monto_destino=monto_destino,
                tasa_cambio=tasa_ejemplo,
                metodo_pago=formulario.cleaned_data['metodo_pago'],
                notas=formulario.cleaned_data['notas'] or '',
                estado='PENDIENTE'
            )
            
            # Procesar pago según el método
            procesador_pago = ProcesadorPagos(
                formulario.cleaned_data['metodo_pago'], 
                objeto_transaccion
            )
            
            # Preparar datos de pago
            datos_pago = {
                'id_metodo_pago_stripe': formulario.cleaned_data.get('id_metodo_pago_stripe'),
                'cuenta_sipap': formulario.cleaned_data.get('cuenta_sipap'),
                'info_destinatario': {
                    'nombre': formulario.cleaned_data.get('destinatario_western_union')
                },
                'lugar_retiro': formulario.cleaned_data.get('lugar_retiro'),
                'identificacion': formulario.cleaned_data.get('identificacion_retiro'),
                'return_url': solicitud.build_absolute_uri(
                    reverse('transacciones:detalle_transaccion', 
                           kwargs={'id_transaccion': objeto_transaccion.id_transaccion})
                )
            }
            
            # Procesar el pago
            resultado_pago = procesador_pago.procesar_pago(datos_pago)
            
            if resultado_pago.get('success'):
                # Actualizar transacción con información de pago
                objeto_transaccion.referencia_pago = resultado_pago.get('id_pago', '')
                if resultado_pago.get('estado') == 'succeeded':
                    objeto_transaccion.estado = 'PAGADA'
                objeto_transaccion.save()
                
                # Añadir mensaje de éxito con instrucciones de pago
                mensaje_exito = f'Transacción de compra #{objeto_transaccion.numero_transaccion} creada exitosamente. '
                if resultado_pago.get('instructions'):
                    mensaje_exito += resultado_pago['instructions']
                
                messages.success(solicitud, mensaje_exito)
                
                # Manejar respuestas específicas de Stripe
                if resultado_pago.get('requiere_accion'):
                    # Guardar información del intento de pago en la sesión para manejo en el frontend
                    solicitud.session['pago_pendiente'] = {
                        'id_transaccion': str(objeto_transaccion.id_transaccion),
                        'secreto_cliente': resultado_pago.get('secreto_cliente'),
                        'id_intento_pago': resultado_pago.get('id_intento_pago')
                    }
                    
                return redirect('transacciones:detalle_transaccion', id_transaccion=objeto_transaccion.id_transaccion)
            else:
                # El pago falló
                objeto_transaccion.estado = 'FALLIDA'
                objeto_transaccion.save()
                messages.error(solicitud, f"Error en el pago: {resultado_pago.get('message', 'Error desconocido')}")
        
        contexto = self.get_context_data(**kwargs)
        contexto['formulario'] = formulario
        return self.render_to_response(contexto)

class VistaTransaccionVenta(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Vista para crear transacciones de venta.
    """
    template_name = 'transacciones/transaccion_venta.html'
    permiso_requerido = 'solicitar_cambio_venta'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Comprobar si el usuario tiene un cliente seleccionado
        if not self.request.user.ultimo_cliente_seleccionado and not self.request.user.clientes.exists():
            contexto['advertencia_sin_cliente'] = True
            contexto['formulario'] = None
        else:
            contexto['formulario'] = FormularioTransaccion(transaction_type='VENTA', user=self.request.user)
            contexto['cliente_activo'] = self.request.user.ultimo_cliente_seleccionado
            # Añadir clave pública de Stripe para el frontend
            contexto['stripe_clave_publicable'] = settings.STRIPE_CLAVE_PUBLICABLE
            contexto['moneda_base'] = Moneda.objects.get(es_moneda_base=True)
            
        return contexto
    
    def post(self, solicitud, *args, **kwargs):
        # Comprobar si el usuario tiene acceso a clientes
        if not solicitud.user.ultimo_cliente_seleccionado and not solicitud.user.clientes.exists():
            messages.error(
                solicitud, 
                'Debe tener un cliente asignado para realizar transacciones.'
            )
            return redirect('clientes:lista_clientes')
        
        formulario = FormularioTransaccion(solicitud.POST, transaction_type='VENTA', user=solicitud.user)
        
        if formulario.is_valid():
            # Obtener el cliente - ya sea del formulario o del cliente seleccionado por el usuario
            cliente = formulario.cleaned_data.get('cliente') or solicitud.user.ultimo_cliente_seleccionado
            
            if not cliente:
                messages.error(solicitud, 'No se pudo determinar el cliente para la transacción.')
                contexto = self.get_context_data(**kwargs)
                contexto['formulario'] = formulario
                return self.render_to_response(contexto)
            
            # Obtener tasa de cambio (implementación de ejemplo)
            # En una implementación real, esto se obtendría del modelo TasaCambio
            from decimal import Decimal
            tasa_ejemplo = Decimal('7450.00')  # Tasa de venta de ejemplo (menor que la de compra)
            
            # Calcular monto de destino
            monto_destino = formulario.cleaned_data['monto_origen'] * tasa_ejemplo
            
            # Crear transacción usando método seguro
            objeto_transaccion = Transaccion.objects.create_safe(
                tipo_transaccion='VENTA',
                cliente=cliente,
                usuario=solicitud.user,
                moneda_origen=formulario.cleaned_data['moneda_origen'],
                moneda_destino=formulario.cleaned_data['moneda_destino'],
                monto_origen=formulario.cleaned_data['monto_origen'],
                monto_destino=monto_destino,
                tasa_cambio=tasa_ejemplo,
                metodo_pago=formulario.cleaned_data['metodo_pago'],
                notas=formulario.cleaned_data['notas'] or '',
                estado='PENDIENTE'
            )
            
            # Procesar pago según el método
            procesador_pago = ProcesadorPagos(
                formulario.cleaned_data['metodo_pago'], 
                objeto_transaccion
            )
            
            # Preparar datos de pago
            datos_pago = {
                'id_metodo_pago_stripe': formulario.cleaned_data.get('id_metodo_pago_stripe'),
                'cuenta_sipap': formulario.cleaned_data.get('cuenta_sipap'),
                'info_destinatario': {
                    'nombre': formulario.cleaned_data.get('destinatario_western_union')
                },
                'lugar_retiro': formulario.cleaned_data.get('lugar_retiro'),
                'identificacion': formulario.cleaned_data.get('identificacion_retiro'),
                'return_url': solicitud.build_absolute_uri(
                    reverse('transacciones:detalle_transaccion', 
                           kwargs={'id_transaccion': objeto_transaccion.id_transaccion})
                )
            }
            
            # Procesar el pago
            resultado_pago = procesador_pago.procesar_pago(datos_pago)
            
            if resultado_pago.get('success'):
                # Actualizar transacción con información de pago
                objeto_transaccion.referencia_pago = resultado_pago.get('id_pago', '')
                if resultado_pago.get('estado') == 'succeeded':
                    objeto_transaccion.estado = 'PAGADA'
                objeto_transaccion.save()
                
                # Añadir mensaje de éxito con instrucciones de pago
                mensaje_exito = f'Transacción de venta #{objeto_transaccion.numero_transaccion} creada exitosamente. '
                if resultado_pago.get('instructions'):
                    mensaje_exito += resultado_pago['instructions']
                
                messages.success(solicitud, mensaje_exito)
                
                # Manejar respuestas específicas de Stripe
                if resultado_pago.get('requiere_accion'):
                    # Guardar información del intento de pago en la sesión para manejo en el frontend
                    solicitud.session['pago_pendiente'] = {
                        'id_transaccion': str(objeto_transaccion.id_transaccion),
                        'secreto_cliente': resultado_pago.get('secreto_cliente'),
                        'id_intento_pago': resultado_pago.get('id_intento_pago')
                    }
                    
                return redirect('transacciones:detalle_transaccion', id_transaccion=objeto_transaccion.id_transaccion)
            else:
                # El pago falló
                objeto_transaccion.estado = 'FALLIDA'
                objeto_transaccion.save()
                messages.error(solicitud, f"Error en el pago: {resultado_pago.get('message', 'Error desconocido')}")
        
        contexto = self.get_context_data(**kwargs)
        contexto['formulario'] = formulario
        return self.render_to_response(contexto)

class VistaDetalleTransaccion(LoginRequiredMixin, DetailView):
    """
    Vista detallada de una transacción.
    """
    model = Transaccion
    template_name = 'transacciones/detalle_transaccion.html'
    context_object_name = 'transaccion'
    slug_field = 'id_transaccion'
    slug_url_kwarg = 'id_transaccion'
    
    def get_object(self):
        transaccion = get_object_or_404(
            Transaccion, 
            id_transaccion=self.kwargs['id_transaccion'],
            usuario=self.request.user
        )
        return transaccion
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        transaccion = self.object
        
        contexto.update({
            'puede_cancelar': transaccion.puede_ser_cancelada(),
            'formulario_cancelacion': FormularioCancelarTransaccion(),
            'facturas_relacionadas': transaccion.factura if hasattr(transaccion, 'factura') else None,
        })
        
        return contexto

class VistaCancelarTransaccion(LoginRequiredMixin, TemplateView):
    """
    Cancela una transacción con un motivo.
    """
    template_name = 'transacciones/cancelar_transaccion.html'
    
    def obtener_transaccion(self):
        return get_object_or_404(
            Transaccion,
            id_transaccion=self.kwargs['id_transaccion'],
            usuario=self.request.user
        )
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        transaccion = self.obtener_transaccion()
        
        if not transaccion.puede_ser_cancelada():
            raise Http404("Esta transacción no puede ser cancelada")
        
        contexto.update({
            'transaccion': transaccion,
            'formulario_cancelacion': FormularioCancelarTransaccion(),
        })
        
        return contexto
    
    def post(self, solicitud, *args, **kwargs):
        transaccion = self.obtener_transaccion()
        
        if not transaccion.puede_ser_cancelada():
            messages.error(solicitud, "Esta transacción no puede ser cancelada")
            return redirect('transacciones:detalle_transaccion', id_transaccion=transaccion.id_transaccion)
        
        formulario = FormularioCancelarTransaccion(solicitud.POST)
        if formulario.is_valid():
            motivo_cancelacion = formulario.cleaned_data['motivo']
            
            # Cancelar la transacción
            exito = transaccion.cancelar(
                motivo=motivo_cancelacion,
                cancelado_por=solicitud.user
            )
            
            if exito:
                messages.success(
                    solicitud, 
                    f"Transacción #{transaccion.numero_transaccion} cancelada exitosamente"
                )
                
                # Registrar la cancelación para auditoría
                from django.contrib.admin.models import LogEntry, CHANGE
                from django.contrib.contenttypes.models import ContentType
                
                LogEntry.objects.log_action(
                    user_id=solicitud.user.id,
                    content_type_id=ContentType.objects.get_for_model(Transaccion).pk,
                    object_id=transaccion.id,
                    object_repr=str(transaccion),
                    action_flag=CHANGE,
                    change_message=f"Transacción cancelada. Motivo: {motivo_cancelacion}"
                )
                
                return redirect('transacciones:detalle_transaccion', id_transaccion=transaccion.id_transaccion)
            else:
                messages.error(solicitud, "No se pudo cancelar la transacción")
        else:
            messages.error(solicitud, "Por favor corrija los errores en el formulario")
        
        return self.get(solicitud, *args, **kwargs)

class VistaListaFacturas(LoginRequiredMixin, ListView):
    """
    Lista las facturas del usuario autenticado.
    """
    model = Factura
    template_name = 'transacciones/lista_facturas.html'
    context_object_name = 'facturas'
    paginate_by = 20
    
    def get_queryset(self):
        return Factura.objects.filter(
            transaccion__usuario=self.request.user
        ).order_by('-fecha_emision')

class VistaDetalleFactura(LoginRequiredMixin, DetailView):
    """
    Vista detallada de una factura.
    """
    model = Factura
    template_name = 'transacciones/detalle_factura.html'
    context_object_name = 'factura'
    slug_field = 'numero_factura'
    slug_url_kwarg = 'numero_factura'
    
    def get_object(self):
        factura = get_object_or_404(
            Factura, 
            numero_factura=self.kwargs['numero_factura'],
            transaccion__usuario=self.request.user
        )
        return factura

class VistaPDFFactura(LoginRequiredMixin, TemplateView):
    """
    Genera y descarga el PDF de una factura.
    """
    template_name = 'en_construccion.html'
    
    def get(self, solicitud, *args, **kwargs):
        # Esto se implementará cuando añadamos la generación de PDF
        messages.info(solicitud, "Funcionalidad de PDF en desarrollo")
        numero_factura = kwargs.get('numero_factura')
        return redirect('transacciones:detalle_factura', numero_factura=numero_factura)

class VistaHistorialTransacciones(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Historial de transacciones con opciones avanzadas de filtrado y exportación.
    """
    template_name = 'transacciones/lista_transacciones.html'
    permiso_requerido = 'consultar_transacciones'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener las transacciones - para administradores mostrar todas, para usuarios normales solo las suyas
        # Excluir transacciones anuladas de la visualización
        try:
            if self.request.user.is_superuser or self.request.user.roles.filter(nombre_rol='Administrador').exists():
                # Admin puede ver todas las transacciones excepto anuladas
                transacciones = Transaccion.objects.safe_all().exclude(estado='ANULADA')
            else:
                # Usuario normal solo ve sus transacciones excepto anuladas
                transacciones = Transaccion.objects.safe_all().filter(usuario=self.request.user).exclude(estado='ANULADA')
        except Exception:
            # Si hay error con safe_all, intentar método alternativo
            if self.request.user.is_superuser or self.request.user.roles.filter(nombre_rol='Administrador').exists():
                transacciones = Transaccion.objects.all().exclude(estado='ANULADA')
            else:
                transacciones = Transaccion.objects.filter(usuario=self.request.user).exclude(estado='ANULADA')
            # Filtrar solo las válidas usando el queryset personalizado
            try:
                transacciones = transacciones.filter_valid_decimals()
            except:
                pass  # Si no existe el método, continuar sin él
        
        # Aplicar filtro de fecha
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        
        if fecha_desde:
            transacciones = transacciones.filter(fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            transacciones = transacciones.filter(fecha_creacion__date__lte=fecha_hasta)
        
        # Aplicar otros filtros
        estado = self.request.GET.get('estado')
        if estado:
            transacciones = transacciones.filter(estado=estado)
            
        tipo_transaccion = self.request.GET.get('tipo')
        if tipo_transaccion:
            transacciones = transacciones.filter(tipo_transaccion=tipo_transaccion)
        
        moneda = self.request.GET.get('moneda')
        if moneda:
            transacciones = transacciones.filter(
                models.Q(moneda_origen__codigo=moneda) | 
                models.Q(moneda_destino__codigo=moneda)
            )
        
        # Filtros adicionales para administradores
        cliente_filtro = self.request.GET.get('cliente')
        if cliente_filtro:
            # Permitir búsqueda por nombre, correo o ID del cliente
            if cliente_filtro.isdigit():
                # Si es numérico, buscar por ID
                transacciones = transacciones.filter(cliente__id=cliente_filtro)
            else:
                # Si es texto, buscar por nombre o email
                transacciones = transacciones.filter(
                    models.Q(cliente__nombre__icontains=cliente_filtro) |
                    models.Q(cliente__apellido__icontains=cliente_filtro) |
                    models.Q(cliente__nombre_empresa__icontains=cliente_filtro) |
                    models.Q(cliente__email__icontains=cliente_filtro)
                )
        
        usuario_filtro = self.request.GET.get('usuario')
        if usuario_filtro:
            # Permitir búsqueda por nombre o email del usuario
            if usuario_filtro.isdigit():
                # Si es numérico, buscar por ID
                transacciones = transacciones.filter(usuario__id=usuario_filtro)
            else:
                # Si es texto, buscar por nombre o email
                transacciones = transacciones.filter(
                    models.Q(usuario__first_name__icontains=usuario_filtro) |
                    models.Q(usuario__last_name__icontains=usuario_filtro) |
                    models.Q(usuario__email__icontains=usuario_filtro)
                )
        
        # Ordenar por fecha
        transacciones = transacciones.order_by('-fecha_creacion')
        
        # Calcular estadísticas de resumen
        from django.db.models import Sum, Count, Avg
        total_transacciones = transacciones.count()
        volumen_total = transacciones.aggregate(Sum('monto_origen'))['monto_origen__sum'] or Decimal('0')
        transaccion_promedio = transacciones.aggregate(Avg('monto_origen'))['monto_origen__avg'] or Decimal('0')
        
        # Conteo por estado (excluyendo ANULADA)
        conteo_estados = {}
        for codigo_estado, etiqueta_estado in Transaccion.ESTADOS:
            if codigo_estado != 'ANULADA':  # Excluir ANULADA del conteo
                conteo = transacciones.filter(estado=codigo_estado).count()
                if conteo > 0:
                    conteo_estados[etiqueta_estado] = conteo
        
        contexto.update({
            'transacciones': transacciones[:100],  # Limitar para rendimiento
            'total_transacciones': total_transacciones,
            'volumen_total': volumen_total,
            'transaccion_promedio': transaccion_promedio,
            'conteo_estados': conteo_estados,
            'filtros': {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
                'estado': estado,
                'tipo': tipo_transaccion,
                'moneda': moneda,
                'cliente': cliente_filtro,
                'usuario': usuario_filtro,
            },
            'opciones_estado': [estado for estado in Transaccion.ESTADOS if estado[0] != 'ANULADA'],  # Excluir ANULADA
            'opciones_tipo': Transaccion.TIPOS_TRANSACCION,
            'monedas': Moneda.objects.filter(esta_activa=True).order_by('codigo'),
            'es_administrador': self.request.user.is_superuser or self.request.user.roles.filter(nombre_rol='Administrador').exists(),
        })
        
        return contexto

class VistaExportarHistorial(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Exporta el historial de transacciones a varios formatos.
    """
    permiso_requerido = 'consultar_transacciones'
    
    def get(self, solicitud, *args, **kwargs):
        formato = solicitud.GET.get('formato', 'csv')
        
        # Usar la misma lógica de filtrado que VistaHistorialTransacciones
        # Excluir transacciones anuladas de la exportación
        if solicitud.user.is_superuser or solicitud.user.roles.filter(nombre_rol='Administrador').exists():
            transacciones = Transaccion.objects.all().exclude(estado='ANULADA')
        else:
            transacciones = Transaccion.objects.filter(usuario=solicitud.user).exclude(estado='ANULADA')
        
        # Aplicar los mismos filtros
        fecha_desde = solicitud.GET.get('fecha_desde')
        fecha_hasta = solicitud.GET.get('fecha_hasta')
        estado = solicitud.GET.get('estado')
        tipo_transaccion = solicitud.GET.get('tipo')
        moneda = solicitud.GET.get('moneda')
        cliente_filtro = solicitud.GET.get('cliente')
        usuario_filtro = solicitud.GET.get('usuario')
        
        if fecha_desde:
            transacciones = transacciones.filter(fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            transacciones = transacciones.filter(fecha_creacion__date__lte=fecha_hasta)
        if estado:
            transacciones = transacciones.filter(estado=estado)
        if tipo_transaccion:
            transacciones = transacciones.filter(tipo_transaccion=tipo_transaccion)
        if moneda:
            transacciones = transacciones.filter(
                models.Q(moneda_origen__codigo=moneda) | 
                models.Q(moneda_destino__codigo=moneda)
            )
        if cliente_filtro:
            if cliente_filtro.isdigit():
                transacciones = transacciones.filter(cliente__id=cliente_filtro)
            else:
                transacciones = transacciones.filter(
                    models.Q(cliente__nombre__icontains=cliente_filtro) |
                    models.Q(cliente__apellido__icontains=cliente_filtro) |
                    models.Q(cliente__nombre_empresa__icontains=cliente_filtro) |
                    models.Q(cliente__email__icontains=cliente_filtro)
                )
        if usuario_filtro:
            if usuario_filtro.isdigit():
                transacciones = transacciones.filter(usuario__id=usuario_filtro)
            else:
                transacciones = transacciones.filter(
                    models.Q(usuario__first_name__icontains=usuario_filtro) |
                    models.Q(usuario__last_name__icontains=usuario_filtro) |
                    models.Q(usuario__email__icontains=usuario_filtro)
                )
        
        transacciones = transacciones.order_by('-fecha_creacion')
        
        if formato == 'csv':
            return self._exportar_csv(transacciones)
        elif formato == 'pdf':
            return self._exportar_pdf(transacciones)
        else:
            messages.error(solicitud, "Formato de exportación no válido")
            return redirect('transacciones:lista_transacciones')
    
    def _exportar_csv(self, transacciones):
        """Exporta las transacciones a formato CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="historial_transacciones_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        response.write('\ufeff')  # BOM para UTF-8
        
        writer = csv.writer(response)
        writer.writerow([
            'Fecha',
            'Número Transacción', 
            'Tipo',
            'Moneda Origen',
            'Moneda Destino',
            'Monto Origen',
            'Monto Destino',
            'Tasa Aplicada',
            'Estado',
            'Cliente',
            'Email Cliente',
            'Usuario',
            'Email Usuario'
        ])
        
        for transaccion in transacciones:
            writer.writerow([
                transaccion.fecha_creacion.strftime('%d/%m/%Y %H:%M:%S'),
                transaccion.numero_transaccion,
                transaccion.get_tipo_transaccion_display(),
                transaccion.moneda_origen.codigo,
                transaccion.moneda_destino.codigo,
                str(transaccion.monto_origen),
                str(transaccion.monto_destino),
                str(transaccion.tasa_cambio),
                transaccion.get_estado_display(),
                transaccion.cliente.obtener_nombre_completo(),
                transaccion.cliente.email,
                f"{transaccion.usuario.first_name} {transaccion.usuario.last_name}".strip() or transaccion.usuario.email,
                transaccion.usuario.email,
            ])
        
        return response
    
    def _exportar_pdf(self, transacciones):
        """Exporta las transacciones a formato PDF"""
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="historial_transacciones_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
        
        # Elementos del PDF
        elementos = []
        estilos = getSampleStyleSheet()
        
        # Título
        titulo_estilo = ParagraphStyle(
            'TituloCustom',
            parent=estilos['Heading1'],
            fontSize=16,
            textColor=colors.darkblue,
            alignment=1  # Centro
        )
        titulo = Paragraph("Historial de Transacciones - Global Exchange", titulo_estilo)
        elementos.append(titulo)
        elementos.append(Spacer(1, 0.2*inch))
        
        # Información adicional
        info_estilo = ParagraphStyle(
            'InfoCustom',
            parent=estilos['Normal'],
            fontSize=10,
            alignment=1  # Centro
        )
        fecha_generacion = Paragraph(f"Generado el: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}", info_estilo)
        total_registros = Paragraph(f"Total de registros: {transacciones.count()}", info_estilo)
        elementos.append(fecha_generacion)
        elementos.append(total_registros)
        elementos.append(Spacer(1, 0.3*inch))
        
        # Tabla de datos
        datos_tabla = [
            ['Fecha', 'Número', 'Tipo', 'Monedas', 'Monto Origen', 'Tasa', 'Estado', 'Cliente']
        ]
        
        for transaccion in transacciones[:50]:  # Limitar a 50 para no sobrecargar el PDF
            datos_tabla.append([
                transaccion.fecha_creacion.strftime('%d/%m/%Y'),
                transaccion.numero_transaccion,
                transaccion.get_tipo_transaccion_display()[:6],
                f"{transaccion.moneda_origen.codigo}→{transaccion.moneda_destino.codigo}",
                f"{transaccion.monto_origen:,.2f}",
                f"{transaccion.tasa_cambio:,.4f}",
                transaccion.get_estado_display()[:8],
                transaccion.cliente.obtener_nombre_completo()[:20],
            ])
        
        tabla = Table(datos_tabla, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elementos.append(tabla)
        
        # Nota al pie
        if transacciones.count() > 50:
            nota = Paragraph(f"<i>Nota: Se muestran los primeros 50 registros de {transacciones.count()} transacciones totales.</i>", info_estilo)
            elementos.append(Spacer(1, 0.2*inch))
            elementos.append(nota)
        
        doc.build(elementos)
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response

class APIVistaCrearTransaccion(LoginRequiredMixin, TemplateView):
    """
    Endpoint de API para crear transacciones.
    """
    def post(self, solicitud, *args, **kwargs):
        # Esto se implementaría para la creación de transacciones con AJAX
        return JsonResponse({
            'success': False,
            'message': 'API en desarrollo'
        })


class VistaConfirmarPagoStripe(LoginRequiredMixin, TemplateView):
    """
    Endpoint de API para confirmar pagos de Stripe.
    """
    def post(self, solicitud, *args, **kwargs):
        import json
        try:
            datos = json.loads(solicitud.body)
            id_intento_pago = datos.get('id_intento_pago')
            id_transaccion = datos.get('id_transaccion')
            
            if not id_intento_pago or not id_transaccion:
                return JsonResponse({
                    'success': False,
                    'error': 'Faltan parámetros requeridos'
                })
            
            # Obtener la transacción
            objeto_transaccion = get_object_or_404(
                Transaccion,
                id_transaccion=id_transaccion,
                usuario=solicitud.user
            )
            
            # Confirmar pago con Stripe
            from .payments import confirmar_pago_stripe
            resultado = confirmar_pago_stripe(id_intento_pago)
            
            if resultado.get('success'):
                if resultado.get('estado') == 'succeeded':
                    objeto_transaccion.estado = 'PAGADA'
                    objeto_transaccion.referencia_pago = id_intento_pago
                    objeto_transaccion.save()
                    
                    return JsonResponse({
                        'success': True,
                        'estado': 'succeeded',
                        'message': 'Pago procesado exitosamente'
                    })
                elif resultado.get('requiere_accion'):
                    return JsonResponse({
                        'success': True,
                        'estado': 'requires_action',
                        'message': 'Se requiere acción adicional del usuario'
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'estado': resultado.get('estado'),
                        'message': 'Pago en proceso'
                    })
            else:
                # El pago falló
                objeto_transaccion.estado = 'FALLIDA'
                objeto_transaccion.save()
                return JsonResponse({
                    'success': False,
                    'error': resultado.get('error'),
                    'message': 'Error procesando el pago'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'message': 'Error inesperado'
            })

class APIVistaEstadoTransaccion(LoginRequiredMixin, TemplateView):
    """
    Endpoint de API para comprobar el estado de una transacción.
    """
    def get(self, solicitud, *args, **kwargs):
        id_transaccion = kwargs.get('id_transaccion')
        try:
            transaccion = get_object_or_404(
                Transaccion,
                id_transaccion=id_transaccion,
                usuario=solicitud.user
            )
            
            return JsonResponse({
                'success': True,
                'estado': transaccion.estado,
                'estado_display': transaccion.get_estado_display(),
                'puede_cancelar': transaccion.puede_ser_cancelada(),
                'fecha_actualizacion': transaccion.fecha_actualizacion.isoformat(),
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

def obtenerTasasMonedas():
    tasas = TasaCambio.objects.select_related('moneda_origen', 'moneda_destino').all()
    resultado = []
    for tasa in tasas:
        resultado.append({
            'moneda_origen': tasa.moneda_origen.codigo,
            'moneda_destino': tasa.moneda_destino.codigo,
            'tasa': str(tasa.tasa),
            'ultima_actualizacion': tasa.ultima_actualizacion.isoformat() if tasa.ultima_actualizacion else None
        })
    return resultado