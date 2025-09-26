import builtins

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, View, TemplateView
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

from .models import LimiteTransaccionCliente, PreferenciaCliente
from .forms import FormularioPreferenciaCliente, FormularioEditarCategoriaCliente, FormularioLimiteCliente

from .models import Cliente, CategoriaCliente, ClienteUsuario, MonedaFavorita, SaldoCliente
from .forms import (
    FormularioCliente, FormularioClienteUsuario, FormularioBusquedaCliente, 
    FormularioAnadirMonedaFavorita, FormularioAsignarUsuarioACliente
)
from divisas.models import Moneda

Usuario = get_user_model()


class MixinStaffRequerido(UserPassesTestMixin):
    """
    Mixin para asegurar que solo usuarios del personal puedan acceder a la gestión de clientes (`is_staff=True`).

    Notes
    -----
    - Si el usuario no es staff, se le redirige automáticamente al panel de control principal.
        y se muestra un mensaje de error.
    """
    
    def test_func(self):
        """
        Verifica si el usuario que hace la petición es staff.

        Returns
        -------
        bool
            `True` si el usuario tiene el flag `is_staff=True`,
            `False` en caso contrario.
        """
        return self.request.user.is_staff

    def handle_no_permission(self):
        """
        Maneja el caso en que un usuario no tiene permisos para acceder a la vista.
        Al no tener permisos, se genera un mensaje de error y se redirige al panel de control.

        Returns
        -------
        HttpResponseRedirect
            Redirección al panel de control.

        """
        messages.error(self.request, 'No tiene permisos para acceder a esta página.')
        return redirect('divisas:panel_de_control')


class VistaListaClientes(LoginRequiredMixin, MixinStaffRequerido, ListView):
    """
    Lista paginada de todos los clientes con capacidades de búsqueda y filtrado.

    Muestra información básica de cada cliente, incluyendo nombre, apellido y estado.

    Attributes
    ----------
    model : Model
        Modelo :class:`Cliente`
    paginate_by : int
        Número de clientes a mostrar por página.

    Notes
    -----
    - Los filtros se toman del queryset y se validan con :class:`FormularioBusquedaCliente`
    - Orden por defecto: fecha de creación (más reciente primero).
    """
    model = Cliente
    template_name = 'clientes/lista_clientes.html'
    context_object_name = 'clientes'
    paginate_by = 20

    def get_queryset(self):
        """
        Construye el queryset de clientes con información relacionada y filtros.

        Filtros soportados (si el formulario es válido):
            - **busqueda**: coincidencia parcial (`icontains`) sobre nombre, apellido,
            empresa, identificación y email.
            - **tipo_cliente**: igualdad exacta.
            - **estado**: igualdad exacta.
            - **categoria**: igualdad exacta contra instancia de :class:`CategoriaCliente`.

        Returns
        -------
        QuerySet
            El queryset filtrado y ordenado de clientes (recientes primero).
        """
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
        """
        Agrega información adicional al contexto de la vista.
        Incluye el formulario ligado al queryset para mantener los filtros para la cabecera.

        Returns
        -------
        dict
            Diccionario de contexto con:
            - `formulario_busqueda`: instancia de :class:`FormularioBusquedaCliente`
            - `total_clientes`: El número total de clientes en la base de datos.
            - `clientes_activos`: El número de clientes activos (`is_active=True`).
        """
        contexto = super().get_context_data(**kwargs)
        contexto['formulario_busqueda'] = FormularioBusquedaCliente(self.request.GET)
        contexto['total_clientes'] = Cliente.objects.count()
        contexto['clientes_activos'] = Cliente.objects.filter(estado='ACTIVO').count()
        return contexto


class VistaCrearCliente(LoginRequiredMixin, MixinStaffRequerido, CreateView):
    """
    Vista para crear un nuevo cliente.

    Muestra un formulario donde se cargan los datos del cliente.

    Attributes
    ----------
    model : Model
        Modelo :class:`Cliente`
    form_class : Form
        :class:`FormularioCliente

    Notes
    -----
    - Asigna 'creado_por' al usuario que crea el cliente.
    - Muestra mensaje de éxito al crear el cliente y redirige a la lista de clientes.

    """
    model = Cliente
    form_class = FormularioCliente
    template_name = 'clientes/formulario_cliente.html'
    success_url = reverse_lazy('clientes:lista_clientes')

    def form_valid(self, formulario):
        """Guarda el cliente y procesa (opcionalmente) los límites personalizados.

        Lógica espejo de :class:`VistaEditarCliente` para mantener consistencia:

        - El checkbox visible ``chk_limites_personalizados`` invierte el valor real
          de ``usa_limites_default`` (marcado => usa_limites_default False).
        - Si el cliente usa límites default se asegura que exista (o se cree)
          un registro de límites con montos en 0 (actúa como ilimitado y/o
          delega en configuración global) y se ignoran valores enviados.
        - Si NO usa límites default se valida y guarda el formulario de límites.

        Parameters
        ----------
        formulario : Form
            FormularioCliente validado.

        Returns
        -------
        HttpResponseRedirect
            Redirección al success_url.
        """
        # Interpretar checkbox visible (plantilla nueva / antigua)
        chk_personalizados = self.request.POST.get('chk_limites_personalizados')
        if chk_personalizados is not None:
            formulario.instance.usa_limites_default = not (chk_personalizados == 'on')

        # Asignar usuario creador antes de guardar
        formulario.instance.creado_por = self.request.user

        # Guardar el cliente primero para disponer de self.object
        respuesta = super().form_valid(formulario)

        usa_default = formulario.instance.usa_limites_default

        # Obtener límites existentes (aún no debería haber, pero por seguridad)
        try:
            limites = self.object.limites  # type: ignore[attr-defined]
        except LimiteTransaccionCliente.DoesNotExist:
            limites = None

        if usa_default:
            # Crear (o asegurar) registro con montos en 0 para facilitar futura edición
            if limites is None:
                # Estrategia de selección de moneda: base -> activa -> primera
                moneda = None
                if hasattr(Moneda, 'es_moneda_base'):
                    moneda = Moneda.objects.filter(es_moneda_base=True).first()
                if moneda is None and hasattr(Moneda, 'esta_activa'):
                    moneda = Moneda.objects.filter(esta_activa=True).first()
                if moneda is None:
                    moneda = Moneda.objects.order_by('id').first()
                if moneda is not None:
                    LimiteTransaccionCliente.objects.get_or_create(
                        cliente=self.object,
                        defaults={
                            'moneda_limite': moneda,
                            'monto_limite_diario': 0,
                            'monto_limite_mensual': 0,
                        }
                    )
            else:
                cambios = []
                if limites.monto_limite_diario != 0:
                    limites.monto_limite_diario = 0
                    cambios.append('monto_limite_diario')
                if limites.monto_limite_mensual != 0:
                    limites.monto_limite_mensual = 0
                    cambios.append('monto_limite_mensual')
                if cambios:
                    limites.save(update_fields=cambios)
        else:
            # Procesar formulario de límites personalizados
            form_limites = FormularioLimiteCliente(self.request.POST, instance=limites)
            if form_limites.is_valid():
                limites_obj = form_limites.save(commit=False)
                limites_obj.cliente = self.object
                limites_obj.save()
            else:
                for campo, lista in form_limites.errors.items():
                    for err in lista:
                        messages.warning(self.request, f'Error en límite ({campo}): {err}')

        messages.success(
            self.request,
            f'Cliente {formulario.instance.obtener_nombre_completo()} creado exitosamente.'
        )
        return respuesta

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto de la vista.

        Incluye el título de la vista, el texto del botón de envío y el formulario mismo.

        Returns
        -------
        dict
            Diccionario con datos extra para la plantilla.
        """
        contexto = super().get_context_data(**kwargs)
        contexto['titulo_accion'] = 'Crear Cliente'
        contexto['texto_submit'] = 'Crear Cliente'
        if 'form' in contexto:
            contexto['formulario'] = contexto['form']
        else:
            contexto['formulario'] = self.get_form()

        # Para creación aún no existe instancia de límites; se provee formulario vacío
        if self.request.method == 'POST':
            contexto['formulario_limites'] = FormularioLimiteCliente(self.request.POST)
        else:
            contexto['formulario_limites'] = FormularioLimiteCliente()
        contexto['limites'] = None
        return contexto


class VistaDetalleCliente(LoginRequiredMixin, MixinStaffRequerido, DetailView):
    """
    Vista para mostrar los detalles de un cliente.

    Muestra información detallada sobre un cliente específico, incluyendo:
        - Datos personales
        - Preferencias
        - Relaciones con otros modelos
        - usuarios relacionados

    Attributes
    ----------
    model : Model
        Modelo :class:`Cliente`

    """
    model = Cliente
    template_name = 'clientes/detalle_cliente.html'
    context_object_name = 'cliente'
    pk_url_kwarg = 'id_cliente'

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto de la vista.

        Incluye:
        - Usuarios asignados al cliente
        - Monedas favoritas
        - Saldos disponibles por moneda
        - Preferencias específicas del cliente si existen

        Returns
        -------
        dict
            Contexto adicional con 'cliente_usuarios', 'monedas_favoritas', 'saldos_moneda' y 'preferencias'.
        """
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
    Vista para editar la información de un cliente existente.

    Muestra el formulario con los datos cargados del cliente y permite
    modificarlos. Además, se asegura de que el cliente tenga siempre
    un registro de preferencias (si no lo tiene, se crea automáticamente).

    Attributes
    ----------
    model : Model
        Modelo :class:`Cliente`
    form_class : Form
        FormularioCliente

    Notes
    -----
    - Si el cliente no tiene preferencias, se crean con valores por defecto.
    - se inyecta tambien el formulario de preferencias en el contexto.
    """
    model = Cliente
    form_class = FormularioCliente
    template_name = 'clientes/formulario_cliente.html'
    pk_url_kwarg = 'id_cliente'

    def get_success_url(self):
        """
        Define a donde redirigir despues de actualizar el cliente.

        Returns
        -------
        str
            URL a 'clientes:detalle_cliente' del objeto actualizado.
        """
        return reverse('clientes:detalle_cliente', kwargs={'id_cliente': self.object.pk})

    def form_valid(self, formulario):
        """
        Además de guardar el cliente, procesa el formulario de límites.

        La plantilla invierte la lógica: el checkbox visible (chk_limites_personalizados)
        marca límites personalizados => backend debe recibir usa_limites_default = False.
        El campo real ``usa_limites_default`` se envía ya invertido, pero aquí
        decidimos si persistir cambios en los límites o ignorarlos.

        Reglas:
        - Si ``usa_limites_default`` es True => se ignoran valores enviados de límites y se ponen en 0.
        - Si ``usa_limites_default`` es False => se valida y guarda el formulario de límites.
        """
        # Sincronizar valor de usa_limites_default con el checkbox visible si viene en POST
        chk_personalizados = self.request.POST.get('chk_limites_personalizados')
        if chk_personalizados is not None:
            formulario.instance.usa_limites_default = not (chk_personalizados == 'on')
        # Guardar primero el cliente
        respuesta = super().form_valid(formulario)
        usa_default = formulario.instance.usa_limites_default  # usar el valor posiblemente actualizado
        try:
            limites = self.object.limites  # type: ignore[attr-defined]
        except LimiteTransaccionCliente.DoesNotExist:
            limites = None
        if usa_default:
            if limites:
                cambios = []
                if limites.monto_limite_diario != 0:
                    limites.monto_limite_diario = 0
                    cambios.append('monto_limite_diario')
                if limites.monto_limite_mensual != 0:
                    limites.monto_limite_mensual = 0
                    cambios.append('monto_limite_mensual')
                if cambios:
                    limites.save(update_fields=cambios)
        else:
            form_limites = FormularioLimiteCliente(self.request.POST, instance=limites)
            if form_limites.is_valid():
                limites_obj = form_limites.save(commit=False)
                limites_obj.cliente = self.object
                limites_obj.save()
            else:
                for campo, lista in form_limites.errors.items():
                    for err in lista:
                        messages.warning(self.request, f'Error en límite ({campo}): {err}')
        messages.success(self.request, f'Cliente {formulario.instance.obtener_nombre_completo()} actualizado exitosamente.')
        return respuesta

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto de la vista.

        Incluye:
        - Formulario de preferencias
        - Preferencias específicas del cliente
        - Títulos y texto del boton para la interfaz
        - Formulario principal

        Returns
        -------
        dict
            Diccionario con los elementos extra para el contexto.
        """
        contexto = super().get_context_data(**kwargs)
        contexto['titulo_accion'] = 'Editar Cliente'
        contexto['titulo_cliente'] = self.object.obtener_nombre_completo()
        contexto['texto_submit'] = 'Actualizar Cliente'
        #contexto['formulario'] = contexto.get('form')
        if 'form' in contexto:
            contexto['formulario'] = contexto['form']
        else:
            # Si no hay 'form', crear uno vacío o manejar el caso
            contexto['formulario'] = self.get_form()
        # Obtener o crear límites
        # Debido a OneToOneField, acceder a self.object.limites puede lanzar LimiteTransaccionCliente.DoesNotExist
        try:
            limites = self.object.limites  # type: ignore[attr-defined]
        except LimiteTransaccionCliente.DoesNotExist:
            limites = None

        if limites is None:
            # Estrategia de selección de moneda: base -> activa -> primera
            moneda = None
            # es_moneda_base si existe
            if hasattr(Moneda, 'es_moneda_base'):
                moneda = Moneda.objects.filter(es_moneda_base=True).first()
            # esta_activa si no se encontró base
            if moneda is None and hasattr(Moneda, 'esta_activa'):
                moneda = Moneda.objects.filter(esta_activa=True).first()
            # fallback cualquier moneda
            if moneda is None:
                moneda = Moneda.objects.order_by('id').first()
            if moneda is not None:
                limites, _creado = LimiteTransaccionCliente.objects.get_or_create(
                    cliente=self.object,
                    defaults={
                        'moneda_limite': moneda,
                        'monto_limite_diario': 0,
                        'monto_limite_mensual': 0,
                    }
                )
        contexto['limites'] = limites
        # Agregar el formulario de límites al contexto
        if self.request.method == 'POST':
            contexto['formulario_limites'] = FormularioLimiteCliente(self.request.POST, instance=limites)
        else:
            contexto['formulario_limites'] = FormularioLimiteCliente(instance=limites)
        return contexto



class VistaGestionarUsuariosCliente(LoginRequiredMixin, MixinStaffRequerido, DetailView):
    """
    Vista para gestionar los usuarios asociados a un cliente en concreto.

    Attributes
    ----------
    model : Model
        Modelo :class:`Cliente`

    Notes
    -----
    - La vista no asigna usuarios directamente al cliente, solo muestra las listas de los ya
        asignados y los que están disponibles.
    """
    model = Cliente
    template_name = 'clientes/gestionar_usuarios_cliente.html'
    context_object_name = 'cliente'
    pk_url_kwarg = 'id_cliente'

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto de la vista.

        Incluye:
        - Lista de usuarios asignados al cliente
        - Lista de usuarios disponibles para asignación

        Returns
        -------
        dict
            Contexto adicional con el cliente y las listas de usuarios actuales y disponibles.
        """
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
    Vista para asociar un usuario existente a un cliente.

    Muestra un formulario para seleccionar el usuario, y al confirmar se crea la asociación
    entre ese usuario y el cliente indicado en la URL.

    Attributes
    ----------
    form_class : Form
        FormularioClienteUsuario.

    Notes
    -----
    - La relacion se guarda en el modelo `ClienteUsuario`.

    """
    form_class = FormularioClienteUsuario
    template_name = 'clientes/anadir_usuario_cliente.html'

    def dispatch(self, solicitud, *args, **kwargs):
        """
        Sobrescribe el método dispatch para obtener el cliente desde la URL
        antes de procesar la vista

        Parameters
        ----------
        solicitud : HttpRequest
            La petición que llega a la vista

        Returns
        -------
        HttpResponse
            Respuesta de la superclase con el flujo normal
        """
        self.cliente = get_object_or_404(Cliente, pk=kwargs['id_cliente'])
        return super().dispatch(solicitud, *args, **kwargs)

    def get_form_kwargs(self):
        """
        Agrega el cliente a los argumentos del formulario para que pueda ser utilizado en la validación.

        Returns
        -------
        dict
            Diccionario de argumentos para inicializar el formulario con el cliente incluido.
        """
        kwargs = super().get_form_kwargs()
        kwargs['cliente'] = self.cliente
        return kwargs

    def form_valid(self, formulario):
        """
        Si el formulario es válido, se crea la asociación 'ClienteUsuario',
        se registra quien hizo la asignacion y muestra un mensaje de éxito.

        Parameters
        ----------
        formulario : Form
            Formulario validado con el usuario a asociar.

        Returns
        -------
        HttpResponseRedirect
            Redirección tras asociar el usuario hacia la vista de gestión de usuarios del cliente.

        Raises
        -------
        Exception
            Si ocurre un error al crear la asociación.
        """
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
        """
        Maneja el caso en el que el formulario no es válido y regenera el token CSRF
        para permitir

        Parameters
        ----------
        formulario : Form
            Instancia el formulario inválido.

        Returns
        -------
        HttpResponse
            Respuesta de la superclase con los errores del formulario.
        """
        # Asegurar que el token CSRF esté disponible para el reintento
        get_token(self.request)
        return super().form_invalid(formulario)

    def get_context_data(self, **kwargs):
        """
        Agrega cliente y token CSRF al contexto.

        Returns
        -------
        dict
            Contexto extendido con cliente y token CSRF.
        """
        contexto = super().get_context_data(**kwargs)
        contexto['cliente'] = self.cliente
        # Asegurar que el token CSRF siempre esté disponible
        contexto['csrf_token'] = get_token(self.request)
        return contexto
    
    
class VistaEditarPreferenciasCliente(LoginRequiredMixin, MixinStaffRequerido, UpdateView):
    """
    Vista para editar las preferencias de un cliente.

    Muestra un formulario con los límites y configuraciones personales del cliente.
    Una vez guardadas, se muestra un mensaje de éxito y se redirige a la vista de detalle del cliente.

    Attributes
    ----------
    model : Model
       :class:`PreferenciaCliente`
    form_class : Form
        :class:`FormularioPreferenciaCliente`.

    Notes
    -----
    - Redirige a la vista de detalle del cliente al guardar.

    """
    model = PreferenciaCliente
    form_class = FormularioPreferenciaCliente
    template_name = 'clientes/formulario_preferencia_cliente.html'
    pk_url_kwarg = 'id_preferencia'

    def get_success_url(self):
        """
        Define a donde redirigir tras guardar las preferencias.

        Returns
        -------
        str
            URL de detalle del cliente al que pertenecen las preferencias.
        """
        return reverse('clientes:detalle_cliente', kwargs={'id_cliente': self.object.cliente.pk})

    def form_valid(self, form):
        """
        Se llama cuando el formulario es válido.
        Muestra mensaje de éxito y guarda los cambios usando la logica de
        la superclase.

        Parameters
        ----------
        form : Form
            Formulario validado con las preferencias del cliente

        Returns
        -------
        HttpResponseRedirect
            Redirección tras guardar las preferencias.
        """
        messages.success(self.request, 'Preferencias del cliente actualizadas exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto.

        Incluye:
        - Titulo dinamico con el nombre completo del cliente
        - Formulario para editar preferencias
        - Botón para guardar cambios
        - URL de redirección tras guardar

        Returns
        -------
        dict
            Contexto adicional para la plantilla.
        """
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = f'Editar Preferencias de {self.object.cliente.obtener_nombre_completo()}'
        contexto['texto_submit'] = 'Guardar Preferencias'
        if 'form' in contexto:
            contexto['formulario'] = contexto['form']
        else:
            contexto['formulario'] = self.get_form()
        contexto['redirect_url'] = reverse('clientes:detalle_cliente', kwargs={'id_cliente': self.object.cliente.pk})
        return contexto


class VistaEliminarUsuarioCliente(LoginRequiredMixin, MixinStaffRequerido, DeleteView):
    """
    Vista para desasociar un usuario de un cliente

    Attributes
    ----------
    model : Model
        :class:`ClienteUsuario`

    Notes
    -----
    - Si el usuario tiene este cliente como su último cliente seleccionado, se limpiará esa asociación.
    - Muestra mensaje de éxito y redirige a la vista de gestión de usuarios del cliente.

    """
    model = ClienteUsuario
    template_name = 'clientes/confirmar_eliminar_usuario.html'

    def get_object(self):
        """
        Recupera la instancia de ClienteUsuario por IDs indicados en la URL.

        Returns
        -------
        ClienteUsuario
            Instancia de la relación cliente-usuario.
        """
        return get_object_or_404(
            ClienteUsuario,
            cliente_id=self.kwargs['id_cliente'],
            usuario_id=self.kwargs['id_usuario']
        )

    def get_success_url(self):
        """
        Devuelve la URL de retorno tras eliminar la relacion.

        Returns
        -------
        str
            URL de gestión de usuarios del cliente.
        """
        return reverse('clientes:gestionar_usuarios_cliente', kwargs={'id_cliente': self.kwargs['id_cliente']})

    def delete(self, solicitud, *args, **kwargs):
        """
        Elimina la asociación cliente-usuario.

        Parameters
        ----------
        solicitud : HttpRequest
            Solicitud entrante.

        Returns
        -------
        HttpResponseRedirect
            Redirección tras eliminar la asociación a la gestión de usuarios del cliente.
        
        Notes
        -----
        - Si el cliente eliminado era el último seleccionado por el usuario,
        limpia esa referencia. Luego muestra un mensaje de éxito.
        """
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
        """
        Agrega el cliente y el usuario al contexto.

        Returns
        -------
        dict
            Diccionario con cliente y usuario para mostrarlos en la plantilla.
        """
        contexto = super().get_context_data(**kwargs)
        contexto['cliente'] = self.object.cliente
        contexto['usuario'] = self.object.usuario
        return contexto


class VistaGestionarFavoritos(LoginRequiredMixin, MixinStaffRequerido, DetailView):
    """
    Gestiona las monedas favoritas de un cliente.

    Attributes
    ----------
    model : Model
        Modelo Cliente.
    template_name : str
        Plantilla a usar.
    context_object_name : str
        Nombre del contexto para el cliente.
    pk_url_kwarg : str
        Nombre del parámetro de URL para el pk.

    Methods
    -------
    get_context_data(**kwargs)
        Agrega monedas favoritas y disponibles al contexto.
    """
    model = Cliente
    template_name = 'clientes/gestionar_favoritos.html'
    context_object_name = 'cliente'
    pk_url_kwarg = 'id_cliente'

    def get_context_data(self, **kwargs):
        """
        Agrega monedas favoritas y disponibles al contexto.

        Returns
        -------
        dict
            Contexto adicional para la plantilla.
        """
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

    Attributes
    ----------
    form_class : Form
        FormularioAnadirMonedaFavorita.
    template_name : str
        Plantilla a usar.

    Methods
    -------
    dispatch(solicitud, *args, **kwargs)
        Obtiene el cliente objetivo.
    get_form_kwargs()
        Pasa el cliente al formulario.
    form_valid(formulario)
        Lógica al añadir moneda favorita.
    get_context_data(**kwargs)
        Agrega cliente al contexto.
    """
    form_class = FormularioAnadirMonedaFavorita
    template_name = 'clientes/anadir_favorito.html'

    def dispatch(self, solicitud, *args, **kwargs):
        """
        Obtiene el cliente objetivo desde la URL y despacha la solicitud.

        Parameters
        ----------
        solicitud : HttpRequest
            Solicitud entrante.
        *args
            Argumentos posicionales.
        **kwargs
            Argumentos de palabra clave.

        Returns
        -------
        HttpResponse
            Respuesta de la superclase.
        """
        self.cliente = get_object_or_404(Cliente, pk=kwargs['id_cliente'])
        return super().dispatch(solicitud, *args, **kwargs)

    def get_form_kwargs(self):
        """
        Inyecta el cliente en los argumentos del formulario.

        Returns
        -------
        dict
            Argumentos del formulario con el cliente incluido.
        """
        kwargs = super().get_form_kwargs()
        kwargs['cliente'] = self.cliente
        return kwargs

    def form_valid(self, formulario):
        """
        Añade una moneda favorita al cliente al validar el formulario.

        Parameters
        ----------
        formulario : Form
            Formulario validado.

        Returns
        -------
        HttpResponseRedirect
            Redirección tras añadir la moneda favorita.
        """
        favorito = formulario.save(commit=False)
        favorito.cliente = self.cliente
        favorito.save()
        messages.success(
            self.request,
            f'Moneda {favorito.moneda.nombre} agregada a favoritas del cliente {self.cliente.obtener_nombre_completo()}.'
        )
        return redirect('clientes:gestionar_favoritos', id_cliente=self.cliente.pk)

    def get_context_data(self, **kwargs):
        """
        Agrega el cliente al contexto.

        Returns
        -------
        dict
            Contexto adicional para la plantilla.
        """
        contexto = super().get_context_data(**kwargs)
        contexto['cliente'] = self.cliente
        return contexto


class VistaEliminarFavorito(LoginRequiredMixin, MixinStaffRequerido, DeleteView):
    """
    Elimina una moneda favorita de un cliente.

    Attributes
    ----------
    model : Model
        Modelo MonedaFavorita.
    template_name : str
        Plantilla a usar.
    pk_url_kwarg : str
        Nombre del parámetro de URL para el pk.

    Methods
    -------
    get_object()
        Obtiene la instancia MonedaFavorita.
    delete(solicitud, *args, **kwargs)
        Lógica de eliminación y mensaje.
    get_context_data(**kwargs)
        Agrega cliente y moneda al contexto.
    """
    model = MonedaFavorita
    template_name = 'clientes/confirmar_eliminar_favorito.html'
    pk_url_kwarg = 'id_favorito'

    def get_object(self):
        """
        Obtiene la instancia MonedaFavorita por IDs de URL.

        Returns
        -------
        MonedaFavorita
            Instancia de moneda favorita.
        """
        return get_object_or_404(
            MonedaFavorita,
            pk=self.kwargs['id_favorito'],
            cliente_id=self.kwargs['id_cliente']
        )

    def delete(self, solicitud, *args, **kwargs):
        """
        Elimina la moneda favorita del cliente.

        Parameters
        ----------
        solicitud : HttpRequest
            Solicitud entrante.
        *args
            Argumentos posicionales.
        **kwargs
            Argumentos de palabra clave.

        Returns
        -------
        HttpResponseRedirect
            Redirección tras eliminar la moneda favorita.
        """
        self.object = self.get_object()
        cliente = self.object.cliente
        moneda = self.object.moneda
        mensaje_exito = f'Moneda {moneda.nombre} removida de favoritas del cliente {cliente.obtener_nombre_completo()}.'
        self.object.delete()
        messages.success(solicitud, mensaje_exito)
        return redirect('clientes:gestionar_favoritos', id_cliente=cliente.pk)

    def get_context_data(self, **kwargs):
        """
        Agrega cliente y moneda al contexto.

        Returns
        -------
        dict
            Contexto adicional para la plantilla.
        """
        contexto = super().get_context_data(**kwargs)
        contexto['cliente'] = self.object.cliente
        contexto['moneda'] = self.object.moneda
        return contexto


class VistaSaldosCliente(LoginRequiredMixin, MixinStaffRequerido, DetailView):
    """
    Vista para ver los saldos del cliente por moneda.

    Attributes
    ----------
    model : Model
        Modelo Cliente.

    """
    model = Cliente
    template_name = 'clientes/saldos_cliente.html'
    context_object_name = 'cliente'
    pk_url_kwarg = 'id_cliente'

    def get_context_data(self, **kwargs):
        """
        Agrega saldos y saldo total al contexto.

        Returns
        -------
        dict
            Contexto adicional para la plantilla.
        """
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

    Attributes
    ----------
    form_class : Form
        :class:`FormularioAsignarUsuarioACliente

    Notas
    -----
    Request (POST):
        - user_id: ID del usuario a asociar.
        - cliente: Cliente al que se asignará el usuario.
    Response (JSON):
        - success (bool): Indica si la operación fue exitosa.
        - message (str): Mensaje descriptivo de la operación.
        - errors (dict): Errores de validación si los hay.
    """
    form_class = FormularioAsignarUsuarioACliente

    def form_valid(self, formulario):
        """
        Crea la asociación ClienteUsuario si no existe y devuelve JSON.

        Comprueba si el usuario ya está asociado con el cliente, y si no lo está,
        crea la relación.

        Parameters
        ----------
        formulario : Form
            :class:`FormularioAsignarUsuarioACliente` 

        Returns
        -------
        JsonResponse
            Respuesta JSON con el resultado de la operación.
        """
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
        """
        Responde con JSON de errores de validación para que la interfaz pueda mostrar al usuario.

        Parameters
        ----------
        formulario : Form
            Formulario inválido.

        Returns
        -------
        JsonResponse
            Respuesta JSON con el detalle de los errores
        """
        return JsonResponse({
            'success': False,
            'message': 'Datos inválidos.',
            'errors': formulario.errors
        })


def fallo_csrf(request, reason=""):
    """
    Vista de fallo CSRF personalizada que proporciona mensajes de error y orientaciones de solución.

    Determina la URL de retorno apropiada a la solicitud que falló.

    Parameters
    ----------
    request : HttpRequest
        Petición HTTP que generó error CSRF.
    reason : str, optional
        Razón del fallo CSRF.

    Returns
    -------
    TemplateResponse
        Respuesta que renderiza la plantilla ``clientes/fallo_csrf.html``
        con estado 403 (forbidden).
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
    Vista AJAX para devolver los detalles completos de un usuario asociado a un cliente.

    Se usa para cargar la información del usuario sin necesidad de recargar la página.

    Notes
    -----
    - Verifica que el cliente y el usuario existen y están asociados
    - Devuelve un JSON con datos básicos del usuario, su estado y la relación con el cliente.
    - En caso de error devuelve un JSON con código 500 (Error interno del servidor).
    """
    
    def get(self, solicitud, id_cliente, id_usuario):
        """
        Procesa una solicitud GET para obtener los detalles de un usuario.

        Parameters
        ----------
        solicitud : HttpRequest
            La solicitud GET.
        id_cliente : int
            ID del cliente.
        id_usuario : int
            ID del usuario.

        Returns
        -------
        JsonResponse
            Respuesta JSON con:
                - ``success``: True/False
                - ``detalles_usuario``: dict con información del usuario (si todo sale bien).
                - ``error``: mensaje descriptivo (si ocurre una excepción).
        """
        try:
            # Verificar que el cliente y el usuario existen y están asociados
            cliente = get_object_or_404(Cliente, pk=id_cliente)
            usuario = get_object_or_404(Usuario, pk=id_usuario)
            
            # Verificar que el usuario está asociado con este cliente
            cliente_usuario = get_object_or_404(ClienteUsuario, cliente=cliente, usuario=usuario)
            
            # Preparar detalles del usuario
            try:
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
                    }
                }
            except Exception as e:
                raise Exception(f'Error al preparar los detalles del usuario: {str(e)}')
            
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

class VistaConfiguracionCategorias(MixinStaffRequerido, TemplateView):
    """
    Vista para gestionar configuraciones del sistema.
    Sirve para ver y modificar diferentes parámetros globales relacionados con las categorías de clientes.
    """
    template_name = 'clientes/gestionar_categorias.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)

        # Agrupar configuraciones por categoría
        configuraciones = CategoriaCliente.objects.all().order_by('nombre')

        contexto.update({
            'configuraciones_por_categoria': configuraciones,
            'total_configuraciones': configuraciones.count(),
        })

        return contexto

def guardar_categoria(request, config_id, nuevo_valor):
    configuracion = get_object_or_404(CategoriaCliente, id=config_id)

    configuracion.margen_tasa_preferencial = nuevo_valor
    configuracion.save()

    return render('clientes/gestionar_categorias.html')


class VistaEditarCategoriaCliente(MixinStaffRequerido, View):
    """Vista para editar categoría de cliente."""

    def get(self, request, categoria_id):
        categoria = get_object_or_404(CategoriaCliente, id=categoria_id)
        formulario = FormularioEditarCategoriaCliente(instance=categoria)

        return render(request, 'clientes/editar_categoria.html', {
            'formulario': formulario,
            'categoria': categoria,
            'margen_porcentaje': categoria.margen_tasa_preferencial * 100
        })

    def post(self, request, categoria_id):
        categoria = get_object_or_404(CategoriaCliente, id=categoria_id)
        formulario = FormularioEditarCategoriaCliente(request.POST, instance=categoria)

        if formulario.is_valid():
            categoria_actualizada = formulario.save()

            # Calcular porcentaje para el mensaje
            porcentaje = categoria_actualizada.margen_tasa_preferencial * 100

            messages.success(
                request,
                f'Categoría "{categoria_actualizada.get_nombre_display()}" actualizada correctamente. '
                f'Nuevo margen: {porcentaje:.2f}%'
            )
            return redirect('clientes:lista_clientes')  # o la URL que uses para listar

        return render(request, 'clientes/editar_categoria.html', {
            'formulario': formulario,
            'categoria': categoria,
            'margen_porcentaje': categoria.margen_tasa_preferencial * 100
        })

from django.http import JsonResponse

class VistaActualizarMargenAjax(MixinStaffRequerido, View):
    """Vista AJAX para actualizar solo el margen."""

    def post(self, request, categoria_id):
        try:
            categoria = get_object_or_404(CategoriaCliente, id=categoria_id)
            nuevo_margen = Decimal(request.POST.get('margen', '0'))

            if nuevo_margen <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'El margen debe ser mayor a 0'
                })

            categoria.margen_tasa_preferencial = nuevo_margen
            categoria.save()

            return JsonResponse({
                'success': True,
                'nuevo_margen': float(nuevo_margen),
                'porcentaje': float(nuevo_margen * 100),
                'mensaje': f'Margen actualizado a {nuevo_margen * 100:.4f}%'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })