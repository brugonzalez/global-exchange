from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator


from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
import requests
from clientes.models import CategoriaCliente
from django.utils.formats import number_format
from django.template.loader import render_to_string

from .models import Moneda, TasaCambio, HistorialTasaCambio, PrecioBase, MetodoPago, AlertaTasa
from transacciones.models import SimulacionTransaccion
from .forms import FormularioSimulacion, FormularioActualizacionTasa, FormularioAlerta


class VistaPanelControl(TemplateView):
    """
    Vista del panel de control principal - accesible para todos los usuarios.
    """
    template_name = 'divisas/panel_de_control.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener monedas activas y sus tasas actuales
        monedas = Moneda.objects.filter(esta_activa=True).order_by('codigo')
        datos_tasas = []
        
        
        if self.request.user.is_authenticated and hasattr(self.request.user, 'ultimo_cliente_seleccionado') and self.request.user.ultimo_cliente_seleccionado:
            categoria = self.request.user.ultimo_cliente_seleccionado.categoria
        else:
            categoria = CategoriaCliente.objects.get(nombre='RETAIL')

        for moneda in monedas:
            tasa = moneda.obtener_tasa_actual(categoria)
            if tasa:
                datos_tasas.append({
                    'moneda': moneda,
                    'tasa_compra': tasa.tasa_compra,
                    'tasa_venta': tasa.tasa_venta,
                    'ultima_actualizacion': tasa.fecha_actualizacion,
                })
        
        contexto.update({
            'datos_tasas': datos_tasas,
            'puede_operar': self.request.user.is_authenticated and self.request.user.puede_operar_transacciones(),
            'cliente_seleccionado': getattr(self.request.user, 'ultimo_cliente_seleccionado', None) if self.request.user.is_authenticated else None,
        })
        
        return contexto


class VistaTasasCambio(ListView):
    """
    Vista detallada de tasas de cambio con datos históricos.
    """
    model = Moneda
    template_name = 'divisas/tasas.html'
    context_object_name = 'monedas'
    
    def get_queryset(self):
        return Moneda.objects.filter(esta_activa=True).order_by('codigo')
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener monedas activas y sus tasas actuales (igual que en el panel de control)
        monedas = Moneda.objects.filter(esta_activa=True).order_by('codigo')
        datos_tasas = []

        if self.request.user.is_authenticated and hasattr(self.request.user, 'ultimo_cliente_seleccionado') and self.request.user.ultimo_cliente_seleccionado:
            categoria = self.request.user.ultimo_cliente_seleccionado.categoria
        else:
            categoria = CategoriaCliente.objects.get(nombre='RETAIL')

        for moneda in monedas:
            tasa = moneda.obtener_tasa_actual(categoria)
            if tasa:
                datos_tasas.append({
                    'moneda': moneda,
                    'tasa_compra': tasa.tasa_compra,
                    'tasa_venta': tasa.tasa_venta,
                    'ultima_actualizacion': tasa.fecha_actualizacion,
                })
        
        contexto['datos_tasas'] = datos_tasas
        
        # Obtener historial de tasas para los gráficos
        moneda_seleccionada = self.request.GET.get('currency')
        if moneda_seleccionada:
            moneda = get_object_or_404(Moneda, codigo=moneda_seleccionada)
            historial = HistorialTasaCambio.objects.filter(
                moneda=moneda
            ).order_by('-marca_de_tiempo')[:30]  # Últimos 30 registros
            
            contexto.update({
                'moneda_seleccionada': moneda,
                'historial_tasa': historial,
            })
        
        # Añadir contexto puede_operar para los botones de simulación
        contexto['puede_operar'] = self.request.user.is_authenticated and self.request.user.puede_operar_transacciones()
        
        return contexto


class VistaHistorialTasa(TemplateView):
    """
    Vista del historial de tasas para una moneda específica.
    """
    template_name = 'divisas/historial_tasa.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        codigo_moneda = kwargs.get('codigo_moneda')
        
        moneda = get_object_or_404(Moneda, codigo=codigo_moneda, esta_activa=True)
        
        # Obtener historial basado en el período
        periodo = self.request.GET.get('periodo', '7')  # Por defecto 7 días
        
        if periodo == '1':
            # Últimas 24 horas
            from datetime import timedelta
            fecha_inicio = timezone.now() - timedelta(days=1)
        elif periodo == '7':
            # Últimos 7 días
            from datetime import timedelta
            fecha_inicio = timezone.now() - timedelta(days=7)
        elif periodo == '30':
            # Últimos 30 días
            from datetime import timedelta
            fecha_inicio = timezone.now() - timedelta(days=30)
        else:
            # Todo el tiempo
            fecha_inicio = None
        
        consulta_historial = HistorialTasaCambio.objects.filter(moneda=moneda)
        if fecha_inicio:
            consulta_historial = consulta_historial.filter(marca_de_tiempo__gte=fecha_inicio)
        
        historial = consulta_historial.order_by('marca_de_tiempo')
        
        contexto.update({
            'moneda': moneda,
            'historial_tasa': historial,
            'periodo_seleccionado': periodo,
        })
        
        return contexto


class VistaSimularTransaccion(TemplateView):
    """
    Vista de simulación de transacción.
    """
    template_name = 'divisas/simular.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['formulario'] = FormularioSimulacion()
        contexto['monedas'] = Moneda.objects.filter(esta_activa=True).order_by('codigo')
        return contexto
    
    def post(self, solicitud, *args, **kwargs):
        formulario = FormularioSimulacion(solicitud.POST)
        
        if formulario.is_valid():
            # Obtener la tasa de cambio y calcular la conversión
            moneda_origen = formulario.cleaned_data['moneda_origen']
            moneda_destino = formulario.cleaned_data['moneda_destino']
            monto = formulario.cleaned_data['monto']
            tipo_operacion = formulario.cleaned_data['tipo_operacion']
            
            # Calcular la tasa de conversión
            tasa = self.obtener_tasa_conversion(moneda_origen, moneda_destino, tipo_operacion)
            
            if tasa:
                monto_convertido = monto * tasa
                
                # Guardar simulación si el usuario está autenticado
                if solicitud.user.is_authenticated:
                    simulacion = SimulacionTransaccion.objects.create(
                        usuario=solicitud.user,
                        cliente=getattr(solicitud.user, 'ultimo_cliente_seleccionado', None),
                        tipo_transaccion=tipo_operacion,
                        moneda_origen=moneda_origen,
                        moneda_destino=moneda_destino,
                        monto_origen=monto,
                        monto_destino=monto_convertido,
                        tasa_cambio=tasa,
                        session_key=solicitud.session.session_key,
                        direccion_ip=solicitud.META.get('REMOTE_ADDR')
                    )
                
                return JsonResponse({
                    'success': True,
                    'monto_convertido': float(monto_convertido),
                    'tasa': float(tasa),
                    'puede_proceder': solicitud.user.is_authenticated and solicitud.user.puede_operar_transacciones(),
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No se encontró tasa de cambio para esta conversión'
                })
        
        return JsonResponse({
            'success': False,
            'errors': formulario.errors
        })

    def obtener_tasa_conversion(self, moneda_origen, moneda_destino, tipo_operacion):
        """
        Obtiene la tasa de conversión para moneda_origen -> moneda_destino.
        Devuelve la tasa donde: monto_convertido = monto * tasa.
        """
        
        # Obtener moneda base
        try:
            moneda_base = Moneda.objects.get(es_moneda_base=True)
        except Moneda.DoesNotExist:
            return None
        
        # Caso 1: Conversión directa involucrando la moneda base
        if moneda_origen == moneda_base:
            # Convirtiendo de la moneda base a la moneda objetivo
            objeto_tasa = TasaCambio.objects.filter(
                moneda=moneda_destino,
                moneda_base=moneda_base,
                esta_activa=True
            ).first()
            if objeto_tasa:
                if tipo_operacion == 'BUY':
                    return 1 / objeto_tasa.tasa_venta
                else:
                    return 1 / objeto_tasa.tasa_compra
                    
        elif moneda_destino == moneda_base:
            # Convirtiendo de la moneda origen a la moneda base
            objeto_tasa = TasaCambio.objects.filter(
                moneda=moneda_origen,
                moneda_base=moneda_base,
                esta_activa=True
            ).first()
            if objeto_tasa:
                if tipo_operacion == 'BUY':
                    # Cliente compra moneda base con moneda origen
                    return objeto_tasa.tasa_compra
                else:
                    # Cliente vende moneda_origen por moneda base
                    return objeto_tasa.tasa_venta
                    
        else:
            # Caso 2: Conversión de moneda cruzada a través de la moneda base
            tasa_origen_a_base = TasaCambio.objects.filter(
                moneda=moneda_origen,
                moneda_base=moneda_base,
                esta_activa=True
            ).first()
            
            tasa_base_a_destino = TasaCambio.objects.filter(
                moneda=moneda_destino,
                moneda_base=moneda_base,
                esta_activa=True
            ).first()
            
            if tasa_origen_a_base and tasa_base_a_destino:
                # Para moneda cruzada: el cliente vende moneda_origen, compra moneda_destino
                # Siempre usar: tasa_venta para moneda_origen, tasa_compra para moneda_destino
                return tasa_origen_a_base.tasa_venta / tasa_base_a_destino.tasa_compra
        
        return None


class APIVistaTasasActuales(TemplateView):
    """
    Endpoint de API para obtener las tasas de cambio actuales.
    """
    
    def get(self, solicitud, *args, **kwargs):
        from clientes.models import CategoriaCliente
        # Determinar la categoría a usar
        if solicitud.user.is_authenticated and hasattr(solicitud.user, 'ultimo_cliente_seleccionado') and solicitud.user.ultimo_cliente_seleccionado:
            categoria = solicitud.user.ultimo_cliente_seleccionado.categoria
        else:
            categoria = CategoriaCliente.objects.get(nombre='RETAIL')

        codigo_moneda = solicitud.GET.get('currency')

        if codigo_moneda:
            moneda = get_object_or_404(Moneda, codigo=codigo_moneda, esta_activa=True)
            tasa = moneda.obtener_tasa_actual(categoria)

            if tasa:
                return JsonResponse({
                    'moneda': moneda.codigo,
                    'nombre': moneda.nombre,
                    'tasa_compra': float(tasa.tasa_compra),
                    'tasa_venta': float(tasa.tasa_venta),
                    'ultima_actualizacion': tasa.fecha_actualizacion.isoformat(),
                    'lugares_decimales': tasa.moneda.lugares_decimales
                })
            else:
                return JsonResponse({'error': 'No se encontró tasa'}, status=404)
        else:
            # Devolver todas las tasas
            tasas = []
            monedas = Moneda.objects.filter(esta_activa=True)

            for moneda in monedas:
                tasa = moneda.obtener_tasa_actual(categoria)
                if tasa:
                    tasas.append({
                        'moneda': moneda.codigo,
                        'nombre': moneda.nombre,
                        'tasa_compra': float(tasa.tasa_compra),
                        'tasa_venta': float(tasa.tasa_venta),
                        'ultima_actualizacion': tasa.fecha_actualizacion.isoformat(),
                        'lugares_decimales': tasa.moneda.lugares_decimales
                    })

            return JsonResponse({'tasas': tasas})


class APIVistaActualizarTasas(LoginRequiredMixin, TemplateView):
    """
    Endpoint de API para actualizar las tasas de cambio (solo admin).
    """
    
    def post(self, solicitud, *args, **kwargs):
        if not solicitud.user.is_staff:
            return JsonResponse({'error': 'Permiso denegado'}, status=403)
        
        # Actualizar tasas desde API externa o entrada manual
        tipo_actualizacion = solicitud.POST.get('type', 'manual')
        
        if tipo_actualizacion == 'api':
            # Actualizar desde API externa
            try:
                conteo_actualizados = self.actualizar_desde_api_externa()
                return JsonResponse({
                    'success': True,
                    'message': f'Se actualizaron {conteo_actualizados} tasas de cambio'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error actualizando desde API: {str(e)}'
                })
        else:
            # Actualización manual
            id_moneda = solicitud.POST.get('currency_id')
            tasa_compra = solicitud.POST.get('buy_rate')
            tasa_venta = solicitud.POST.get('sell_rate')
            
            # Validar campos requeridos
            if not id_moneda:
                return JsonResponse({
                    'success': False,
                    'error': 'ID de moneda es requerido'
                })
            
            if not tasa_compra or not tasa_venta:
                return JsonResponse({
                    'success': False,
                    'error': 'Las tasas de compra y venta son requeridas'
                })
            
            try:
                # Obtener moneda de forma segura
                try:
                    moneda = Moneda.objects.get(id=id_moneda, esta_activa=True)
                except Moneda.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': f'La moneda con ID {id_moneda} no existe o no está activa'
                    })
                
                # Obtener moneda base de forma segura
                try:
                    moneda_base = Moneda.objects.get(es_moneda_base=True)
                except Moneda.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'No se encontró una moneda base configurada en el sistema'
                    })
                
                try:
                    tasa_compra_decimal = Decimal(tasa_compra)
                    tasa_venta_decimal = Decimal(tasa_venta)
                    
                    if tasa_compra_decimal <= 0 or tasa_venta_decimal <= 0:
                        return JsonResponse({
                            'success': False,
                            'error': 'Las tasas deben ser mayores que cero'
                        })
                        
                    if tasa_venta_decimal <= tasa_compra_decimal:
                        return JsonResponse({
                            'success': False,
                            'error': 'La tasa de venta debe ser mayor que la tasa de compra'
                        })
                        
                except (ValueError, TypeError):
                    return JsonResponse({
                        'success': False,
                        'error': 'Las tasas ingresadas no son válidas'
                    })
                
                # Comprobar si existe una tasa activa para este par de monedas
                tasa_existente = TasaCambio.objects.filter(
                    moneda=moneda,
                    moneda_base=moneda_base,
                    esta_activa=True
                ).first()
                
                if tasa_existente:
                    # Actualizar la tasa existente en lugar de crear una nueva
                    tasa_existente.tasa_compra = tasa_compra_decimal
                    tasa_existente.tasa_venta = tasa_venta_decimal
                    tasa_existente.fuente = 'MANUAL'
                    tasa_existente.actualizado_por = solicitud.user
                    tasa_existente.save()
                    
                    # Guardar en el historial
                    HistorialTasaCambio.objects.create(
                        moneda=moneda,
                        moneda_base=moneda_base,
                        tasa_compra=tasa_compra_decimal,
                        tasa_venta=tasa_venta_decimal
                    )
                    
                    # Enviar notificaciones de actualización de tasa
                    try:
                        from notificaciones.tasks import enviar_notificacion_actualizacion_tasa_manual, llamar_tarea_con_fallback
                        llamar_tarea_con_fallback(
                            enviar_notificacion_actualizacion_tasa_manual,
                            moneda.id,
                            tasa_compra_decimal,
                            tasa_venta_decimal,
                            solicitud.user.nombre_completo or solicitud.user.username
                        )
                    except Exception:
                        pass  # Fallar silenciosamente si el sistema de notificaciones no está disponible
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Tasa actualizada correctamente'
                    })
                else:
                    # Crear nueva tasa solo si no existe una tasa activa
                    TasaCambio.objects.create(
                        moneda=moneda,
                        moneda_base=moneda_base,
                        tasa_compra=tasa_compra_decimal,
                        tasa_venta=tasa_venta_decimal,
                        fuente='MANUAL',
                        actualizado_por=solicitud.user
                    )
                    
                    # Guardar en el historial
                    HistorialTasaCambio.objects.create(
                        moneda=moneda,
                        moneda_base=moneda_base,
                        tasa_compra=tasa_compra_decimal,
                        tasa_venta=tasa_venta_decimal
                    )
                    
                    # Enviar notificaciones de actualización de tasa
                    try:
                        from notificaciones.tasks import enviar_notificacion_actualizacion_tasa_manual, llamar_tarea_con_fallback
                        llamar_tarea_con_fallback(
                            enviar_notificacion_actualizacion_tasa_manual,
                            moneda.id,
                            tasa_compra_decimal,
                            tasa_venta_decimal,
                            solicitud.user.nombre_completo or solicitud.user.username
                        )
                    except Exception:
                        pass  # Fallar silenciosamente si el sistema de notificaciones no está disponible
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Tasa creada correctamente'
                    })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error interno del servidor: {str(e)}'
                })
    
    def actualizar_desde_api_externa(self):
        """Actualiza las tasas desde una API externa."""
        # Esto se integraría con una API de tasas de cambio real
        # Por ahora, simularemos la actualización
        conteo_actualizados = 0
        
        # Obtener moneda base de forma segura
        try:
            moneda_base = Moneda.objects.get(es_moneda_base=True)
        except Moneda.DoesNotExist:
            raise Exception('No se encontró una moneda base configurada en el sistema')
        
        # Simular datos de la API (en producción, llamarías a una API real)
        tasas_api = {
            'USD': {'buy': 1.0, 'sell': 1.02},
            'EUR': {'buy': 0.85, 'sell': 0.87},
            'PYG': {'buy': 7200, 'sell': 7300},
            'BRL': {'buy': 5.2, 'sell': 5.4},
        }
        
        for codigo, tasas in tasas_api.items():
            try:
                moneda = Moneda.objects.get(codigo=codigo, esta_activa=True)
                
                # Desactivar tasas existentes para este par de monedas
                TasaCambio.objects.filter(
                    moneda=moneda,
                    moneda_base=moneda_base,
                    esta_activa=True
                ).update(esta_activa=False)
                
                # Crear nueva tasa
                TasaCambio.objects.create(
                    moneda=moneda,
                    moneda_base=moneda_base,
                    tasa_compra=Decimal(str(tasas['buy'])),
                    tasa_venta=Decimal(str(tasas['sell'])),
                    fuente='API'
                )
                
                # Guardar en el historial
                HistorialTasaCambio.objects.create(
                    moneda=moneda,
                    moneda_base=moneda_base,
                    tasa_compra=Decimal(str(tasas['buy'])),
                    tasa_venta=Decimal(str(tasas['sell']))
                )
                
                conteo_actualizados += 1
                
            except Moneda.DoesNotExist:
                # Omitir monedas que no existen, esto es esperado
                continue
            except Exception as e:
                # Registrar el error pero continuar con otras monedas
                print(f"Error actualizando {codigo}: {str(e)}")
                continue
        
        return conteo_actualizados


class APIVistaSimulacion(TemplateView):
    """
    Endpoint de API para simulaciones rápidas.
    """
    
    def post(self, solicitud, *args, **kwargs):
        try:
            datos = solicitud.POST
            
            # Validar IDs de moneda y obtener objetos de moneda de forma segura
            # Soportar tanto los nombres en inglés como en español para compatibilidad
            id_moneda_origen = datos.get('currency_from') or datos.get('moneda_origen')
            id_moneda_destino = datos.get('currency_to') or datos.get('moneda_destino')
            
            if not id_moneda_origen:
                return JsonResponse({
                    'success': False,
                    'error': 'Moneda origen es requerida'
                })
            
            if not id_moneda_destino:
                return JsonResponse({
                    'success': False,
                    'error': 'Moneda destino es requerida'
                })
            
            try:
                moneda_origen = Moneda.objects.get(id=id_moneda_origen, esta_activa=True)
            except Moneda.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'La moneda origen con ID {id_moneda_origen} no existe o no está activa'
                })
            
            try:
                moneda_destino = Moneda.objects.get(id=id_moneda_destino, esta_activa=True)
            except Moneda.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'La moneda destino con ID {id_moneda_destino} no existe o no está activa'
                })
            
            # Validar monto - soportar tanto 'amount' como 'monto'
            try:
                monto_str = datos.get('amount') or datos.get('monto', '0')
                monto = Decimal(monto_str)
                if monto <= 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'El monto debe ser mayor que cero'
                    })
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'error': 'El monto ingresado no es válido'
                })
            
            # Soportar tanto 'transaction_type' como 'tipo_transaccion'
            tipo_operacion = datos.get('transaction_type') or datos.get('tipo_transaccion', 'BUY')
            
            # Calcular la tasa de conversión
            tasa = self.obtener_tasa_conversion(moneda_origen, moneda_destino, tipo_operacion)
            
            if tasa:
                monto_convertido = monto * tasa
                return JsonResponse({
                    'success': True,
                    'monto_convertido': float(monto_convertido),
                    'tasa': float(tasa),
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'No se encontró tasa de cambio activa para {moneda_origen.codigo} a {moneda_destino.codigo}'
                })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error interno del servidor: {str(e)}'
            })

    def obtener_tasa_conversion(self, moneda_origen, moneda_destino, tipo_operacion):
        """
        Obtiene la tasa de conversión para moneda_origen -> moneda_destino.
        Devuelve la tasa donde: monto_convertido = monto * tasa.
        """
        
        # Obtener moneda base
        try:
            moneda_base = Moneda.objects.get(es_moneda_base=True)
        except Moneda.DoesNotExist:
            return None
        
        # Caso 1: Conversión directa involucrando la moneda base
        if moneda_origen == moneda_base:
            # Convirtiendo de la moneda base a la moneda objetivo
            objeto_tasa = TasaCambio.objects.filter(
                moneda=moneda_destino,
                moneda_base=moneda_base,
                esta_activa=True
            ).first()
            if objeto_tasa:
                if tipo_operacion == 'BUY':
                    return 1 / objeto_tasa.tasa_venta
                else:
                    return 1 / objeto_tasa.tasa_compra
                    
        elif moneda_destino == moneda_base:
            # Convirtiendo de la moneda origen a la moneda base
            objeto_tasa = TasaCambio.objects.filter(
                moneda=moneda_origen,
                moneda_base=moneda_base,
                esta_activa=True
            ).first()
            if objeto_tasa:
                if tipo_operacion == 'BUY':
                    # Cliente compra moneda base con moneda origen
                    return objeto_tasa.tasa_compra
                else:
                    # Cliente vende moneda_origen por moneda base
                    return objeto_tasa.tasa_venta
                    
        else:
            # Caso 2: Conversión de moneda cruzada a través de la moneda base
            tasa_origen_a_base = TasaCambio.objects.filter(
                moneda=moneda_origen,
                moneda_base=moneda_base,
                esta_activa=True
            ).first()
            
            tasa_base_a_destino = TasaCambio.objects.filter(
                moneda=moneda_destino,
                moneda_base=moneda_base,
                esta_activa=True
            ).first()
            
            if tasa_origen_a_base and tasa_base_a_destino:
                # Para moneda cruzada: el cliente vende moneda_origen, compra moneda_destino
                # Siempre usar: tasa_venta para moneda_origen, tasa_compra para moneda_destino
                return tasa_origen_a_base.tasa_venta / tasa_base_a_destino.tasa_compra
        
        return None


class VistaGestionarFavoritos(LoginRequiredMixin, TemplateView):
    """
    Vista para gestionar las monedas favoritas del usuario.
    """
    template_name = 'divisas/favoritos.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener el cliente actual del usuario
        usuario = self.request.user
        cliente_actual = usuario.ultimo_cliente_seleccionado
        
        if not cliente_actual:
            # Si el usuario tiene clientes, obtener el primero
            if usuario.clientes.exists():
                cliente_actual = usuario.clientes.first()
                usuario.ultimo_cliente_seleccionado = cliente_actual
                usuario.save()
        
        # Obtener todas las monedas activas
        todas_las_monedas = Moneda.objects.filter(esta_activa=True).order_by('codigo')
        
        # Obtener las monedas favoritas para el cliente actual
        monedas_favoritas = []
        if cliente_actual:
            from clientes.models import MonedaFavorita
            favoritos = MonedaFavorita.objects.filter(
                cliente=cliente_actual
            ).select_related('moneda').order_by('orden', 'fecha_creacion')
            monedas_favoritas = [fav.moneda for fav in favoritos]
        
        contexto.update({
            'cliente_actual': cliente_actual,
            'todas_las_monedas': todas_las_monedas,
            'monedas_favoritas': monedas_favoritas,
            'puede_gestionar': cliente_actual is not None,
        })
        
        return contexto


class APIVistaAlternarFavorito(LoginRequiredMixin, TemplateView):
    """
    Vista de API para alternar una moneda como favorita.
    """
    
    def post(self, solicitud, *args, **kwargs):
        try:
            from clientes.models import MonedaFavorita
            
            id_moneda = solicitud.POST.get('currency_id')
            usuario = solicitud.user
            cliente_actual = usuario.ultimo_cliente_seleccionado
            
            if not cliente_actual:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay cliente seleccionado'
                })
            
            moneda = get_object_or_404(Moneda, id=id_moneda, esta_activa=True)
            
            # Comprobar si ya es favorita
            favorito, creado = MonedaFavorita.objects.get_or_create(
                cliente=cliente_actual,
                moneda=moneda,
                defaults={'orden': 0}
            )
            
            if not creado:
                # Eliminar de favoritos
                favorito.delete()
                es_favorito = False
            else:
                # Añadido a favoritos
                es_favorito = True
            
            return JsonResponse({
                'success': True,
                'es_favorito': es_favorito,
                'codigo_moneda': moneda.codigo,
                'nombre_moneda': moneda.nombre
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class APIVistaReordenarFavoritos(LoginRequiredMixin, TemplateView):
    """
    Vista de API para reordenar las monedas favoritas.
    """
    
    def post(self, solicitud, *args, **kwargs):
        try:
            from clientes.models import MonedaFavorita
            import json
            
            usuario = solicitud.user
            cliente_actual = usuario.ultimo_cliente_seleccionado
            
            if not cliente_actual:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay cliente seleccionado'
                })
            
            datos_orden = json.loads(solicitud.body)
            ids_monedas = datos_orden.get('currency_ids', [])
            
            # Actualizar el orden para cada favorito
            for indice, id_moneda in enumerate(ids_monedas):
                MonedaFavorita.objects.filter(
                    cliente=cliente_actual,
                    moneda_id=id_moneda
                ).update(orden=indice)
            
            return JsonResponse({
                'success': True,
                'message': 'Orden actualizado correctamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


# Vistas de administración
class VistaGestionarTasas(LoginRequiredMixin, TemplateView):
    """
    Vista de administración para gestionar las tasas de cambio.
    """
    template_name = 'divisas/gestionar_tasas.html'
    
    def dispatch(self, solicitud, *args, **kwargs):
        # Asegurar que solo usuarios del personal puedan acceder a esta vista
        ajax = solicitud.headers.get('x-requested-with') == 'XMLHttpRequest'
        if not solicitud.user.is_staff:
            if ajax:
                return JsonResponse({'success': False, 'message': 'No tiene permisos para acceder a esta página.'}, status=403)
            messages.error(solicitud, 'No tiene permisos para acceder a esta página.')
            return redirect('divisas:panel_de_control')
        return super().dispatch(solicitud, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener todas las monedas activas
        monedas = Moneda.objects.filter(esta_activa=True).order_by('codigo')
        
        # Obtener datos de las tasas actuales
        datos_tasas = []
        for moneda in monedas:
            tasa_actual = moneda.obtener_precio_base()
            tasas_actuales = moneda.obtener_tasas_actuales()
            # Obtener historial reciente para esta moneda (últimos 7 días)
            from datetime import timedelta
            hace_una_semana = timezone.now() - timedelta(days=7)
            historial_reciente = HistorialTasaCambio.objects.filter(
                moneda=moneda,
                marca_de_tiempo__gte=hace_una_semana
            ).order_by('marca_de_tiempo')
            
            datos_tasas.append({
                'moneda': moneda,
                'precio_actual': tasa_actual.precio_base if tasa_actual else None,
                'fecha_actualizacion': tasa_actual.fecha_actualizacion if tasa_actual else None,
                'actualizado_por': tasa_actual.actualizado_por if tasa_actual else None,
                'historial_reciente': historial_reciente,
                'formulario': FormularioActualizacionTasa() if tasa_actual else None,
                'tasas_actuales': tasas_actuales
            })

        

        # Obtener moneda base
        moneda_base = Moneda.objects.filter(es_moneda_base=True).first()
        
        # Obtener todos los métodos de pago para el contexto
        metodos_pago = MetodoPago.objects.filter(esta_activo=True).order_by('nombre')
        
        # Calcular la última fecha de actualización entre todas las monedas
        fechas = [dt['fecha_actualizacion'] for dt in datos_tasas if dt.get('fecha_actualizacion')]
        ultima_actualizacion = max(fechas) if fechas else None

        contexto.update({
            'datos_tasas': datos_tasas,
            'monedas': monedas,
            'moneda_base': moneda_base,
            'metodos_pago': metodos_pago,
            'total_monedas': monedas.count(),
            'tasas_activas': TasaCambio.objects.filter(esta_activa=True).count(),
            'ultima_actualizacion': ultima_actualizacion,
        })
        
        return contexto
    
    def post(self, request, *args, **kwargs):
        from django.utils import timezone
        from django.http import JsonResponse
        ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        try:
            moneda_id = request.POST.get('moneda_id')
            form = FormularioActualizacionTasa(request.POST)
            if form.is_valid() and moneda_id:
                nuevo_precio_base = form.cleaned_data['precio_base']
                moneda = get_object_or_404(Moneda, id=moneda_id)
                # Guardar actualizado_por si el modelo lo soporta
                defaults = {'precio_base': nuevo_precio_base}
                if hasattr(PrecioBase, 'actualizado_por'):
                    defaults['actualizado_por'] = request.user
                    precio_base_obj, created = PrecioBase.objects.update_or_create(
                    moneda=moneda,
                    defaults=defaults
                )
                tasas_actuales = moneda.obtener_tasas_actuales()  # recomputadas a partir del precio base

                tbody_html = render_to_string(
                    'divisas/_tasas_activas_tbody.html',
                    {'tasas_actuales': tasas_actuales},
                    request=request
                )

                msg = 'Precio base actualizado correctamente.'
                if ajax:
                    fecha_str = ""
                    if hasattr(precio_base_obj, "fecha_actualizacion") and precio_base_obj.fecha_actualizacion:
                        fecha_str = timezone.localtime(precio_base_obj.fecha_actualizacion).strftime("%d/%m/%Y %H:%M")

                    # Construir fuente_actualizacion_str igual que en el template
                    fuente_actualizacion_str = ""
                    if getattr(precio_base_obj, "actualizado_por", None):
                        fuente_actualizacion_str = f"por {getattr(precio_base_obj.actualizado_por, 'nombre_completo', '') or getattr(precio_base_obj.actualizado_por, 'username', '')}"
                    return JsonResponse({
                        "success": True,
                        "message": "Precio base actualizado correctamente.",
                        "moneda_id": moneda.id,
                        "precio_base_raw": float(nuevo_precio_base),
                        "precio_base_html": f"{number_format(nuevo_precio_base, 0, use_l10n=True, force_grouping=True)} PYG",
                        "fecha_actualizacion_str": fecha_str,
                        "actualizado_por": (
                            getattr(request.user, "nombre_completo", None)
                            or request.user.get_full_name()
                            or request.user.username
                        ),
                        "tasas_tbody_html": tbody_html,
                    })
                else:
                    messages.success(request, msg)
                    return redirect('divisas:gestionar_tasas')
            else:
                msg = 'Error al actualizar el precio base.'
                if ajax:
                    return JsonResponse({'success': False, 'message': msg, 'errors': form.errors})
                else:
                    messages.error(request, msg)
                    return redirect('divisas:gestionar_tasas')
        except Exception as e:
            import traceback
            if ajax:
                return JsonResponse({'success': False, 'message': 'Error interno del servidor', 'error': str(e), 'trace': traceback.format_exc()}, status=500)
            else:
                messages.error(request, f'Error interno: {e}')
                return redirect('divisas:gestionar_tasas')

# Vista para actualizar comisiones de una moneda y recalcular tasas
@csrf_exempt
@require_POST
def actualizar_comisiones(request):
    from django.http import JsonResponse
    from django.template.loader import render_to_string
    from django.utils import timezone
    try:
        ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        moneda_id = request.POST.get('moneda_id')
        comision_compra = request.POST.get('comision_compra')
        comision_venta = request.POST.get('comision_venta')
        if not (moneda_id and comision_compra is not None and comision_venta is not None):
            return JsonResponse({'success': False, 'message': 'Datos incompletos.'}, status=400)
        moneda = get_object_or_404(Moneda, id=moneda_id)
        # Guardar comisiones
        moneda.comision_compra = Decimal(comision_compra)
        moneda.comision_venta = Decimal(comision_venta)
        moneda.save(update_fields=['comision_compra', 'comision_venta'])

        # Recalcular tasas de cambio activas para esa moneda
        tasas = TasaCambio.objects.filter(moneda=moneda, esta_activa=True)
        for tasa in tasas:
            # Recalcular usando la lógica actual del modelo
            precio_base = tasa.precio_base.precio_base
            categoria = tasa.categoria_cliente
            tasa.tasa_compra = precio_base + moneda.comision_compra - (categoria.margen_tasa_preferencial * moneda.comision_compra)
            tasa.tasa_venta = precio_base + moneda.comision_venta - (categoria.margen_tasa_preferencial * moneda.comision_venta)
            tasa.save(update_fields=['tasa_compra', 'tasa_venta', 'fecha_actualizacion'])

        # Renderizar tabla de tasas activas
        tasas_actuales = moneda.obtener_tasas_actuales()
        tbody_html = render_to_string('divisas/_tasas_activas_tbody.html', {'tasas_actuales': tasas_actuales}, request=request)

        return JsonResponse({
            'success': True,
            'message': 'Comisiones actualizadas correctamente.',
            'comision_compra_raw': float(moneda.comision_compra),
            'comision_venta_raw': float(moneda.comision_venta),
            'tasas_tbody_html': tbody_html,
        })
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'message': 'Error interno del servidor', 'error': str(e), 'trace': traceback.format_exc()}, status=500)

class VistaActualizarTasa(LoginRequiredMixin, TemplateView):
    template_name = 'en_construccion.html'


class VistaGestionarMonedas(LoginRequiredMixin, TemplateView):
    template_name = 'en_construccion.html'


class VistaGestionarMetodosPago(LoginRequiredMixin, TemplateView):
    template_name = 'en_construccion.html'


class VistaGestionarAlertas(LoginRequiredMixin, TemplateView):
    template_name = 'en_construccion.html'


class VistaCrearAlerta(LoginRequiredMixin, TemplateView):
    template_name = 'en_construccion.html'


class VistaEliminarAlerta(LoginRequiredMixin, TemplateView):
    template_name = 'en_construccion.html'