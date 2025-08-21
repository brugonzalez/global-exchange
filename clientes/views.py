import builtins

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, View
)
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import get_token
from django.conf import settings

from .models import PreferenciaCliente
from .forms import FormularioPreferenciaCliente


from .models import Cliente, CategoriaCliente, ClienteUsuario, MonedaFavorita, SaldoCliente
from .forms import (
    FormularioCliente, FormularioClienteUsuario, FormularioBusquedaCliente, 
    FormularioAnadirMonedaFavorita, FormularioAsignarUsuarioACliente
)
from divisas.models import Moneda

Usuario = get_user_model()


class MixinStaffRequerido(UserPassesTestMixin):
    """Mixin para asegurar que solo usuarios del personal puedan acceder a la gestión de clientes"""
    
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, 'No tiene permisos para acceder a esta página.')
        return redirect('divisas:panel_de_control')


class VistaListaClientes(LoginRequiredMixin, MixinStaffRequerido, ListView):
    """
    Lista todos los clientes con capacidades de búsqueda y filtrado.
    """
    model = Cliente
    template_name = 'clientes/lista_clientes.html'
    context_object_name = 'clientes'
    paginate_by = 20

    def get_queryset(self):
        queryset = Cliente.objects.select_related('categoria').annotate(
            conteo_usuarios=Count('usuarios')
        ).order_by('-fecha_creacion')
        
        # Aplicar filtros de búsqueda
        formulario = FormularioBusquedaCliente(self.request.GET)
        if formulario.is_valid():
            busqueda = formulario.cleaned_data.get('busqueda')
            tipo_cliente = formulario.cleaned_data.get('tipo_cliente')
            estado = formulario.cleaned_data.get('estado')
            categoria = formulario.cleaned_data.get('categoria')
            
            if busqueda:
                queryset = queryset.filter(
                    Q(nombre__icontains=busqueda) |
                    Q(apellido__icontains=busqueda) |
                    Q(nombre_empresa__icontains=busqueda) |
                    Q(numero_identificacion__icontains=busqueda) |
                    Q(email__icontains=busqueda)
                )
            
            if tipo_cliente:
                queryset = queryset.filter(tipo_cliente=tipo_cliente)
            
            if estado:
                queryset = queryset.filter(estado=estado)
            
            if categoria:
                queryset = queryset.filter(categoria=categoria)
        
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['formulario_busqueda'] = FormularioBusquedaCliente(self.request.GET)
        contexto['total_clientes'] = Cliente.objects.count()
        contexto['clientes_activos'] = Cliente.objects.filter(estado='ACTIVO').count()
        return contexto


class VistaCrearCliente(LoginRequiredMixin, MixinStaffRequerido, CreateView):
    """
    Crea un nuevo cliente.
    """
    model = Cliente
    form_class = FormularioCliente
    template_name = 'clientes/formulario_cliente.html'
    success_url = reverse_lazy('clientes:lista_clientes')

    def form_valid(self, formulario):
        formulario.instance.creado_por = self.request.user
        messages.success(self.request, f'Cliente {formulario.instance.obtener_nombre_completo()} creado exitosamente.')
        return super().form_valid(formulario)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = 'Crear Cliente'
        contexto['texto_submit'] = 'Crear Cliente'
        # Agregar Formulario para la compatibilidad de la plantilla
        contexto['formulario'] = contexto.get('form')
        return contexto


class VistaDetalleCliente(LoginRequiredMixin, MixinStaffRequerido, DetailView):
    """
    Ve los detalles del cliente con usuarios y saldos asociados.
    """
    model = Cliente
    template_name = 'clientes/detalle_cliente.html'
    context_object_name = 'cliente'
    pk_url_kwarg = 'id_cliente'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # Obtener usuarios asociados
        contexto['cliente_usuarios'] = ClienteUsuario.objects.filter(
            cliente=self.object
        ).select_related('usuario').order_by('-fecha_asignacion')
        # Obtener monedas favoritas
        contexto['monedas_favoritas'] = MonedaFavorita.objects.filter(
            cliente=self.object
        ).select_related('moneda').order_by('orden', 'fecha_creacion')
        # Obtener saldos de moneda
        contexto['saldos_moneda'] = SaldoCliente.objects.filter(
            cliente=self.object
        ).select_related('moneda').order_by('moneda__codigo')
        # Obtener preferencias
        contexto['preferencias'] = getattr(self.object, 'preferencias', None)
        return contexto


class VistaEditarCliente(LoginRequiredMixin, MixinStaffRequerido, UpdateView):
    """
    Edita la información del cliente.
    """
    model = Cliente
    form_class = FormularioCliente
    template_name = 'clientes/formulario_cliente.html'
    pk_url_kwarg = 'id_cliente'

    def get_success_url(self):
        return reverse('clientes:detalle_cliente', kwargs={'id_cliente': self.object.pk})

    def form_valid(self, formulario):
        messages.success(self.request, f'Cliente {formulario.instance.obtener_nombre_completo()} actualizado exitosamente.')
        return super().form_valid(formulario)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = f'Editar Cliente: {self.object.obtener_nombre_completo()}'
        contexto['texto_submit'] = 'Actualizar Cliente'
        contexto['formulario'] = contexto.get('form')
        # Obtener o crear preferencias
        preferencias = getattr(self.object, 'preferencias', None)
        if not preferencias:
            preferencias = PreferenciaCliente.objects.create(
                cliente=self.object,
                limite_compra=0,
                limite_venta=0,
                frecuencia_maxima=0,
                preferencia_tipo_cambio=''
            )
        contexto['preferencias'] = preferencias
        # Agregar el formulario de preferencias al contexto
        if self.request.method == 'POST':
            contexto['formulario_preferencias'] = FormularioPreferenciaCliente(self.request.POST, instance=preferencias)
        else:
            contexto['formulario_preferencias'] = FormularioPreferenciaCliente(instance=preferencias)
        return contexto


class VistaGestionarUsuariosCliente(LoginRequiredMixin, MixinStaffRequerido, DetailView):
    """
    Gestiona los usuarios asociados a un cliente.
    """
    model = Cliente
    template_name = 'clientes/gestionar_usuarios_cliente.html'
    context_object_name = 'cliente'
    pk_url_kwarg = 'id_cliente'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener las asociaciones cliente-usuario actuales
        contexto['cliente_usuarios'] = ClienteUsuario.objects.filter(
            cliente=self.object
        ).select_related('usuario', 'asignado_por').order_by('-fecha_asignacion')
        
        # Obtener usuarios disponibles para asignación
        ids_usuarios_asignados = self.object.usuarios.values_list('id', flat=True)
        contexto['usuarios_disponibles'] = Usuario.objects.filter(
            is_active=True
        ).exclude(id__in=ids_usuarios_asignados).order_by('nombre_completo', 'email')
        
        return contexto


class VistaAnadirUsuarioCliente(LoginRequiredMixin, MixinStaffRequerido, FormView):
    """
    Añade un usuario a un cliente.
    """
    form_class = FormularioClienteUsuario
    template_name = 'clientes/anadir_usuario_cliente.html'

    def dispatch(self, solicitud, *args, **kwargs):
        self.cliente = get_object_or_404(Cliente, pk=kwargs['id_cliente'])
        return super().dispatch(solicitud, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['cliente'] = self.cliente
        return kwargs

    def form_valid(self, formulario):
        try:
            cliente_usuario = formulario.save(commit=False)
            cliente_usuario.cliente = self.cliente
            cliente_usuario.asignado_por = self.request.user
            cliente_usuario.save()
            
            messages.success(
                self.request, 
                f'Usuario {cliente_usuario.usuario.nombre_completo} asociado exitosamente al cliente {self.cliente.obtener_nombre_completo()}.'
            )
            return redirect('clientes:gestionar_usuarios_cliente', id_cliente=self.cliente.pk)
            
        except Exception as e:
            messages.error(
                self.request,
                f'Error al asociar el usuario: {str(e)}. Por favor, inténtelo nuevamente.'
            )
            # Regenerar token CSRF para el reintento
            get_token(self.request)
            return self.form_invalid(formulario)

    def form_invalid(self, formulario):
        # Asegurar que el token CSRF esté disponible para el reintento
        get_token(self.request)
        return super().form_invalid(formulario)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['cliente'] = self.cliente
        # Asegurar que el token CSRF siempre esté disponible
        contexto['csrf_token'] = get_token(self.request)
        return contexto
class VistaEditarPreferenciasCliente(LoginRequiredMixin, MixinStaffRequerido, UpdateView):
    model = PreferenciaCliente
    form_class = FormularioPreferenciaCliente
    template_name = 'clientes/formulario_preferencia_cliente.html'
    pk_url_kwarg = 'id_preferencia'

    def get_success_url(self):
        return reverse('clientes:detalle_cliente', kwargs={'id_cliente': self.object.cliente.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Preferencias del cliente actualizadas exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = f'Editar Preferencias de {self.object.cliente.obtener_nombre_completo()}'
        contexto['texto_submit'] = 'Guardar Preferencias'
        contexto['formulario'] = contexto.get('form')
        contexto['redirect_url'] = reverse('clientes:detalle_cliente', kwargs={'id_cliente': self.object.cliente.pk})
        return contexto


class VistaEliminarUsuarioCliente(LoginRequiredMixin, MixinStaffRequerido, DeleteView):
    """
    Elimina un usuario de un cliente.
    """
    model = ClienteUsuario
    template_name = 'clientes/confirmar_eliminar_usuario.html'

    def get_object(self):
        return get_object_or_404(
            ClienteUsuario,
            cliente_id=self.kwargs['id_cliente'],
            usuario_id=self.kwargs['id_usuario']
        )

    def get_success_url(self):
        return reverse('clientes:gestionar_usuarios_cliente', kwargs={'id_cliente': self.kwargs['id_cliente']})

    def delete(self, solicitud, *args, **kwargs):
        self.object = self.get_object()
        cliente = self.object.cliente
        usuario = self.object.usuario
        
        # Comprobar si el usuario tiene este cliente seleccionado y limpiarlo
        if usuario.ultimo_cliente_seleccionado == cliente:
            usuario.ultimo_cliente_seleccionado = None
            usuario.save(update_fields=['ultimo_cliente_seleccionado'])
        
        mensaje_exito = f'Usuario {usuario.nombre_completo} desasociado del cliente {cliente.obtener_nombre_completo()}.'
        messages.success(solicitud, mensaje_exito)
        
        return super().delete(solicitud, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['cliente'] = self.object.cliente
        contexto['usuario'] = self.object.usuario
        return contexto


class VistaGestionarFavoritos(LoginRequiredMixin, MixinStaffRequerido, DetailView):
    """
    Gestiona las monedas favoritas de un cliente.
    """
    model = Cliente
    template_name = 'clientes/gestionar_favoritos.html'
    context_object_name = 'cliente'
    pk_url_kwarg = 'id_cliente'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener las monedas favoritas actuales
        contexto['monedas_favoritas'] = MonedaFavorita.objects.filter(
            cliente=self.object
        ).select_related('moneda').order_by('orden', 'fecha_creacion')
        
        # Obtener las monedas disponibles para añadir como favoritas
        ids_monedas_favoritas = self.object.monedas_favoritas.values_list('moneda_id', flat=True)
        contexto['monedas_disponibles'] = Moneda.objects.filter(
            esta_activa=True
        ).exclude(id__in=ids_monedas_favoritas).order_by('nombre')
        
        return contexto


class VistaAnadirFavorito(LoginRequiredMixin, MixinStaffRequerido, FormView):
    """
    Añade una moneda favorita a un cliente.
    """
    form_class = FormularioAnadirMonedaFavorita
    template_name = 'clientes/anadir_favorito.html'

    def dispatch(self, solicitud, *args, **kwargs):
        self.cliente = get_object_or_404(Cliente, pk=kwargs['id_cliente'])
        return super().dispatch(solicitud, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['cliente'] = self.cliente
        return kwargs

    def form_valid(self, formulario):
        favorito = formulario.save(commit=False)
        favorito.cliente = self.cliente
        favorito.save()
        
        messages.success(
            self.request,
            f'Moneda {favorito.moneda.nombre} agregada a favoritas del cliente {self.cliente.obtener_nombre_completo()}.'
        )
        return redirect('clientes:gestionar_favoritos', id_cliente=self.cliente.pk)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['cliente'] = self.cliente
        return contexto


class VistaEliminarFavorito(LoginRequiredMixin, MixinStaffRequerido, DeleteView):
    """
    Elimina una moneda favorita de un cliente.
    """
    model = MonedaFavorita
    template_name = 'clientes/confirmar_eliminar_favorito.html'
    pk_url_kwarg = 'id_favorito'

    def get_object(self):
        return get_object_or_404(
            MonedaFavorita,
            pk=self.kwargs['id_favorito'],
            cliente_id=self.kwargs['id_cliente']
        )

    def delete(self, solicitud, *args, **kwargs):
        self.object = self.get_object()
        cliente = self.object.cliente
        moneda = self.object.moneda
        
        mensaje_exito = f'Moneda {moneda.nombre} removida de favoritas del cliente {cliente.obtener_nombre_completo()}.'
        self.object.delete()
        
        messages.success(solicitud, mensaje_exito)
        return redirect('clientes:gestionar_favoritos', id_cliente=cliente.pk)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['cliente'] = self.object.cliente
        contexto['moneda'] = self.object.moneda
        return contexto


class VistaSaldosCliente(LoginRequiredMixin, MixinStaffRequerido, DetailView):
    """
    Ve los saldos del cliente por moneda.
    """
    model = Cliente
    template_name = 'clientes/saldos_cliente.html'
    context_object_name = 'cliente'
    pk_url_kwarg = 'id_cliente'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener saldos de moneda
        contexto['saldos_moneda'] = SaldoCliente.objects.filter(
            cliente=self.object
        ).select_related('moneda').order_by('moneda__codigo')
        
        # Calcular saldo total en moneda base (asumiendo USD como base)
        # Esto necesitaría cálculos de tasa de cambio en una implementación real
        saldo_total = sum(
            saldo.saldo for saldo in contexto['saldos_moneda']
            if saldo.moneda.codigo == 'USD'
        )
        contexto['saldo_total_usd'] = saldo_total
        
        return contexto


@method_decorator(require_POST, name='post')
class VistaAsignarUsuarioAClienteAjax(LoginRequiredMixin, MixinStaffRequerido, FormView):
    """
    Vista AJAX para asignar rápidamente un usuario a un cliente.
    """
    form_class = FormularioAsignarUsuarioACliente

    def form_valid(self, formulario):
        try:
            id_usuario = self.request.POST.get('user_id')
            usuario = get_object_or_404(Usuario, pk=id_usuario)
            cliente = formulario.cleaned_data['cliente']
            rol = formulario.cleaned_data['rol']
            permisos = formulario.cleaned_data['permisos']

            # Comprobar si la asociación ya existe
            if ClienteUsuario.objects.filter(cliente=cliente, usuario=usuario).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'El usuario ya está asociado a este cliente.'
                })

            # Crear asociación
            ClienteUsuario.objects.create(
                cliente=cliente,
                usuario=usuario,
                rol=rol,
                permisos=permisos,
                asignado_por=self.request.user
            )

            return JsonResponse({
                'success': True,
                'message': f'Usuario {usuario.nombre_completo} asociado exitosamente al cliente {cliente.obtener_nombre_completo()}.'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al asociar usuario: {str(e)}'
            })

    def form_invalid(self, formulario):
        return JsonResponse({
            'success': False,
            'message': 'Datos inválidos.',
            'errors': formulario.errors
        })


def fallo_csrf(request, reason=""):
    """
    Vista de fallo CSRF personalizada que proporciona mensajes de error amigables
    y orientación para resolver problemas de CSRF.
    """
    from django.template.response import TemplateResponse
    from django.utils.translation import gettext as _
    
    # Determinar la URL de retorno apropiada
    url_retorno = request.META.get('HTTP_REFERER', '/')
    if '/usuarios/anadir/' in url_retorno:
        # Para el formulario de añadir usuario de cliente, volver a la gestión de clientes
        import re
        coincidencia = re.search(r'/clientes/(\d+)/usuarios/anadir/', url_retorno)
        if coincidencia:
            id_cliente = coincidencia.group(1)
            url_retorno = f'/clientes/{id_cliente}/usuarios/'
    
    contexto = {
        'reason': reason,
        'return_url': url_retorno,
        'DEBUG': settings.DEBUG,
        'title': 'Error de Verificación CSRF',
    }
    
    return TemplateResponse(request, 'clientes/fallo_csrf.html', contexto, status=403)


class VistaDetallesUsuario(LoginRequiredMixin, MixinStaffRequerido, View):
    """
    Vista AJAX para devolver los detalles del usuario para mostrar en un modal.
    """
    
    def get(self, solicitud, id_cliente, id_usuario):
        """
        Devuelve los detalles del usuario como respuesta JSON.
        """
        try:
            # Verificar que el cliente y el usuario existen y están asociados
            cliente = get_object_or_404(Cliente, pk=id_cliente)
            usuario = get_object_or_404(Usuario, pk=id_usuario)
            
            # Verificar que el usuario está asociado con este cliente
            cliente_usuario = get_object_or_404(ClienteUsuario, cliente=cliente, usuario=usuario)
            
            # Preparar detalles del usuario
            detalles_usuario = {
                'id': usuario.id,
                'nombre_completo': usuario.nombre_completo,
                'username': usuario.username,
                'email': usuario.email,
                'esta_activo': usuario.is_active,
                'es_staff': usuario.is_staff,
                'es_superuser': usuario.is_superuser,
                'fecha_registro': usuario.date_joined.strftime('%d/%m/%Y %H:%M') if usuario.date_joined else None,
                'ultimo_login': usuario.last_login.strftime('%d/%m/%Y %H:%M') if usuario.last_login else 'Nunca',
                'email_verificado': usuario.email_verificado,
                'autenticacion_dos_factores_activa': usuario.autenticacion_dos_factores_activa,
                'intentos_fallidos_login': usuario.intentos_fallidos_login,
                'cuenta_bloqueada': usuario.esta_cuenta_bloqueada(),
                'relacion_cliente': {
                    'rol': cliente_usuario.get_rol_display(),
                    'esta_activo': cliente_usuario.esta_activo,
                    'fecha_asignacion': cliente_usuario.fecha_asignacion.strftime('%d/%m/%Y %H:%M'),
                    'asignado_por': cliente_usuario.asignado_por.nombre_completo if cliente_usuario.asignado_por else 'Sistema',
                    'puede_realizar_transacciones': cliente_usuario.puede_realizar_transacciones(),
                }
            }
            
            # Obtener conteo de clientes asociados
            detalles_usuario['total_clientes'] = usuario.clientes.count()
            
            # Obtener último cliente seleccionado
            if usuario.ultimo_cliente_seleccionado:
                detalles_usuario['ultimo_cliente_seleccionado'] = {
                    'id': usuario.ultimo_cliente_seleccionado.id,
                    'nombre': usuario.ultimo_cliente_seleccionado.obtener_nombre_completo()
                }
            else:
                detalles_usuario['ultimo_cliente_seleccionado'] = None
            
            return JsonResponse({
                'success': True,
                'detalles_usuario': detalles_usuario
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al obtener los detalles del usuario: {str(e)}'
            }, status=500)
