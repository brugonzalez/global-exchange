from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView, ListView, TemplateView

from clientes.models import Cliente
from clientes.views import MixinStaffRequerido
from cuentas.models import Usuario, RegistroAuditoria
from cuentas.views import MixinPermisosAdmin
from divisas.models import MetodoPago
from global_exchange import settings
from pagos.forms import FormularioMedioPago
from pagos.models import MedioPago
from pagos.services.stripe_service import StripeService


# Create your views here.
class MediosPago(LoginRequiredMixin, ListView):
    """
    Lista de medios de pago asociados a un cliente.
    Requiere que el usuario esté autenticado.
    Muestra los medios de pago activos del cliente identificado por id_cliente en la URL.

    Atributtes:
    ----------
        model : Modelo de MedioPago.
        template_name : str
            Nombre de la plantilla HTML a usar.
        context_object_name : str
            Nombre de la variable en el contexto que contendrá la lista de medios de pago.

    Métodos:
    -------
        get_queryset(self):
            Devuelve el queryset de medios de pago activos para el cliente dado por id_cliente.

        get_context_data(self, **kwargs):
            Agrega información extra al contexto, incluyendo el cliente y si tiene medios de pago.
    """
    model = MedioPago
    template_name = 'pagos/medios_pagos.html'
    context_object_name = 'pagos_usuario'

    def get_queryset(self):
        """
        Filtra los medios de pago activos del cliente identificado por id_cliente en la URL.
        Ordena los resultados por fecha de creación descendente.
        Si el cliente no existe, devuelve un queryset vacío.

        Atributtes:
        ----------
            id_cliente : int
                ID del cliente obtenido de los parámetros de la URL.

        Returns:
        -------
            QuerySet de medios de pago activos del cliente.

        """
        id_cliente = self.kwargs.get("id_cliente")
        return MedioPago.objects.filter(
            cliente_id=id_cliente, activo=True
        ).order_by("-fecha_creacion")

    def get_context_data(self, **kwargs):
        """
        Agrega información extra al contexto, incluyendo el cliente y si tiene medios de pago.

        Atributtes:
        ----------
            cliente : Cliente o None
                Instancia del cliente obtenido por id_cliente. None si no existe.
            tiene_pagos : bool
                Indica si el cliente tiene medios de pago activos.

        Returns:
        -------
            Diccionario con el contexto para la plantilla.
        """
        contexto = super().get_context_data(**kwargs)

        id_cliente = self.kwargs.get("id_cliente")
        try:
            cliente = Cliente.objects.get(pk=id_cliente)
            contexto["cliente"] = cliente
        except Usuario.DoesNotExist:
            contexto["cliente"] = None

        queryset = self.get_queryset()
        contexto["tiene_pagos"] = queryset.exists()

        return contexto


class VistaAsociarMedioPago(LoginRequiredMixin, TemplateView):
    """
    Vista para asociar un nuevo medio de pago a un cliente.
    Requiere que el usuario esté autenticado.
    Muestra un formulario para ingresar los datos del medio de pago y lo asocia al cliente
    seleccionado por el usuario.

    Atributtes:
    ----------
        template_name : str
            Nombre de la plantilla HTML a usar.

    """
    template_name = 'pagos/asociar_medio_pago.html'

    def get_context_data(self, **kwargs):
        """
        Agrega información extra al contexto, incluyendo el formulario y datos de Stripe.

        Atributtes:
        ----------
            formulario : FormularioMedioPago
                Instancia del formulario para ingresar datos del medio de pago.
            cliente_activo : Cliente
                Instancia del cliente seleccionado por el usuario.
            tipos_medio_pago : list
                Lista de tipos de medios de pago disponibles.
            stripe_clave_publicable : str
                Clave pública de Stripe para integrar pagos con tarjeta.

        Returns:
        -------
            Diccionario con el contexto para la plantilla.
        """
        contexto = super().get_context_data(**kwargs)

        # Verificar si el usuario tiene un cliente seleccionado
        if not self.request.user.ultimo_cliente_seleccionado and not self.request.user.clientes.exists():
            contexto['advertencia_sin_cliente'] = True
            contexto['formulario'] = None
        else:
            contexto['formulario'] = FormularioMedioPago()
            contexto['cliente_activo'] = self.request.user.ultimo_cliente_seleccionado
            # Tipos de medios de pago disponibles
            contexto['tipos_medio_pago'] = MedioPago.TIPOS
            # Clave pública de Stripe para tarjetas
            contexto['stripe_clave_publicable'] = settings.STRIPE_CLAVE_PUBLICABLE

        return contexto

    def post(self, request, *args, **kwargs):
        """
        Maneja la lógica para procesar el formulario de asociación de medio de pago.
        Valida el formulario, crea el cliente en Stripe si es necesario, crea y asocia
        el metodo de pago, y guarda el medio de pago en la base de datos.
        Muestra mensajes de éxito o error según corresponda.

        Atributtes:
        ----------
            formulario : FormularioMedioPago
                Instancia del formulario con los datos enviados por el usuario.
            cliente : Cliente
                Instancia del cliente seleccionado por el usuario.
            usuario_creacion : Usuario
                Usuario que está realizando la acción.
            stripe_service : StripeService
                Servicio para interactuar con la API de Stripe.
            id_customer : str
                ID del cliente en Stripe.
            stripe_token : str
                Token de Stripe recibido del formulario.
            payment_method : dict
                Detalles del método de pago creado en Stripe.
            datos_tarjeta : dict
                Información de la tarjeta obtenida desde Stripe.
            medio_pago : MedioPago
                Instancia del medio de pago que se guarda en la base de datos.

        Returns:
        -------
            Redirige a la lista de medios de pago del cliente en caso de éxito.
            Si hay errores, vuelve a renderizar la plantilla con los mensajes correspondientes.
        """

        formulario = FormularioMedioPago(request.POST)

        # Verificar acceso a clientes
        if not request.user.ultimo_cliente_seleccionado and not request.user.clientes.exists():
            messages.error(
                request,
                'Debe tener un cliente asignado para asociar medios de pago.'
            )
            return redirect('clientes:lista_clientes')


        if formulario.is_valid():
            # Obtener el cliente activo
            cliente = request.user.ultimo_cliente_seleccionado
            usuario_creacion = request.user
            nombre_titular = request.POST.get('titular')
            stripe_service = StripeService()

            if not cliente:
                messages.error(request, 'No se pudo determinar el cliente para asociar el medio de pago.')
                return self.render_to_response(self.get_context_data(formulario=formulario))

            # Crear customer en Stripe si no existe
            if not cliente.stripe_customer_id:

                customer = stripe_service.crear_customer(
                    email=cliente.email,
                    name=cliente.nombre
                )
                cliente.stripe_customer_id = customer.id
                cliente.save()
                id_customer = customer.id
            else:
                id_customer = cliente.stripe_customer_id

            stripe_token = request.POST.get('stripe_token')
            if not stripe_token:
                messages.error(request, "No se recibió token de Stripe.")
                return self.render_to_response(self.get_context_data(formulario=formulario))

            # Crear PaymentMethod usando el token
            payment_method = stripe_service.crear_y_asociar_payment_method(
                stripe_token=stripe_token,
                customer_id=id_customer
            )

            #datos de la tarjeta
            datos_tarjeta = stripe_service.datos_tarjeta(payment_method.id)

            # Guardamos en la DB
            medio_pago = formulario.save(commit=False)
            medio_pago.activo = True
            medio_pago.cliente = cliente
            medio_pago.stripe_payment_method_id = payment_method.id
            medio_pago.usuario_creacion = usuario_creacion
            medio_pago.nombre_titular = nombre_titular
            medio_pago.ultimos_digitos = datos_tarjeta.get('ultimos_digitos', '')
            medio_pago.marca = datos_tarjeta.get('marca', '')
            medio_pago.save()

            #realizamos el registro de auditoría
            RegistroAuditoria.objects.create(
                usuario=usuario_creacion,
                accion='MEDIO_PAGO_CREATE',
                descripcion=f'Se asoció un medio de pago al cliente: {cliente.obtener_nombre_completo()}',
                agente_usuario='N/A',
                datos_adicionales={
                    'usuario_id': usuario_creacion.id,
                    'medio_pago_id': medio_pago.id,
                }
            )

            messages.success(request, f"Tarjeta asociada correctamente al cliente {cliente.nombre}.")
            return redirect('pagos:medios_pago', id_cliente=cliente.id)


        # Si el formulario no es válido, mostrar errores
        contexto = self.get_context_data(**kwargs)
        contexto['formulario'] = formulario
        return self.render_to_response(contexto)


def desvincular_medio_pago(request, pk):
    """
    Vista para desactivar (no eliminar) un medio de pago asociado a un cliente.
    Requiere que el usuario esté autenticado.
    Cambia el estado del medio de pago a inactivo y registra la acción en el log de auditoría.

    Arguments:
    ---------
        request : HttpRequest
            Objeto de solicitud HTTP.
        pk : int
            ID del medio de pago a desactivar.

    Atributtes:
    ----------
        medio_pago : MedioPago
            Instancia del medio de pago a desactivar.

    Returns:
    -------
        Redirige a la lista de medios de pago del cliente.
    """
    medio_pago = get_object_or_404(MedioPago, pk=pk)

    if request.method == "POST":
        medio_pago.activo = False
        medio_pago.save()

        # realizamos el registro de auditoría
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='MEDIO_PAGO_DELETED',
            descripcion=f'Se asoció un medio de pago al cliente: {request.user.ultimo_cliente_seleccionado.obtener_nombre_completo()}',
            agente_usuario='N/A',
            datos_adicionales={
                'usuario_id': request.user.id,
                'estado_anterior': True,
                'estado_nuevo': False
            }
        )

        messages.success(request, "Tarjeta desactivada correctamente.")

    return redirect('pagos:medios_pago', id_cliente=request.user.ultimo_cliente_seleccionado.id)


class VistaGestionMetodosPago(MixinStaffRequerido, TemplateView):
    """
    Vista para gestionar los métodos de pago disponibles en el sistema.
    Requiere que el usuario sea staff.
    Muestra una lista de todos los métodos de pago con opciones para activar o desactivar cada uno.

    Atributtes:
    ----------
        template_name : str
            Nombre de la plantilla HTML a usar.
    """
    template_name = 'pagos/gestion_metodos_pago.html'

    def get_context_data(self, **kwargs):
        """
        Agrega información extra al contexto, incluyendo la lista de métodos de pago
        y estadísticas sobre ellos.

        Arguments:
        ---------
            kwargs : dict
                Argumentos adicionales para el contexto.

        Atributtes:
        ----------
            metodos_pago : QuerySet
                Lista de todos los métodos de pago ordenados por nombre.
            total_metodos : int
                Total de métodos de pago.
            metodos_activos : int
                Número de métodos de pago activos.
            metodos_inactivos : int
                Número de métodos de pago inactivos.

        Returns:
        -------
            Diccionario con el contexto para la plantilla.

        """
        contexto = super().get_context_data(**kwargs)

        # Obtener todos los métodos de pago ordenados por nombre
        metodos_pago = MetodoPago.objects.all().order_by('nombre')

        contexto.update({
            'metodos_pago': metodos_pago,
            'total_metodos': metodos_pago.count(),
            'metodos_activos': metodos_pago.filter(esta_activo=True).count(),
            'metodos_inactivos': metodos_pago.filter(esta_activo=False).count(),
        })

        return contexto


class VistaToggleMetodoPago(MixinStaffRequerido, TemplateView):
    """
    Vista para cambiar el estado activo/inactivo de un método de pago.
    Requiere que el usuario sea staff.
    Recibe el ID del método de pago en la URL y cambia su estado.
    Responde con JSON indicando el nuevo estado y un mensaje de éxito.

    """

    def post(self, request, metodo_id):
        """
        Cambia el estado activo/inactivo del método de pago identificado por metodo_id.
        Registra la acción en el log de auditoría y responde con JSON.

        Arguments:
        ---------
            request : HttpRequest
                Objeto de solicitud HTTP.
            metodo_id : int
                ID del método de pago a modificar.

        Atributtes:
        ----------
            metodo : MetodoPago
                Instancia del método de pago a modificar.
            estado_anterior : bool
                Estado anterior del método de pago.

        Returns:
        -------
            JsonResponse con el nuevo estado, mensaje de éxito y detalles para actualizar la interfaz.

        """
        metodo = get_object_or_404(MetodoPago, id=metodo_id)

        # Cambiar el estado
        estado_anterior = metodo.esta_activo
        metodo.esta_activo = not metodo.esta_activo
        metodo.save()

        # Preparar respuesta con mensajes más específicos
        if metodo.esta_activo:
            mensaje = f'Método de pago "{metodo.nombre}" habilitado correctamente.'
            accion_contraria = 'Deshabilitar'
            clase_boton = 'btn-warning'
            icono = 'fa-eye-slash'
        else:
            mensaje = f'Método de pago "{metodo.nombre}" deshabilitado correctamente.'
            accion_contraria = 'Habilitar'
            clase_boton = 'btn-success'
            icono = 'fa-eye'

        return JsonResponse({
            'success': True,
            'nuevo_estado': metodo.esta_activo,
            'mensaje': mensaje,
            'accion_contraria': accion_contraria,
            'clase_boton': clase_boton,
            'icono': icono
        })