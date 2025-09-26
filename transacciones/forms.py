from django import forms

from divisas.models import Moneda
from pagos.models import MedioPago
from .models import Transaccion, SimulacionTransaccion


class FormularioCancelarTransaccion(forms.Form):
    """
    Formulario para cancelar una transacción con un motivo.
    """
    MOTIVOS = [
        ('SOLICITUD_USUARIO', 'Solicitud del usuario'),
        ('FALLO_PAGO', 'Fallo en el pago'),
        ('CAMBIO_TASA', 'Cambio en la tasa de cambio'),
        ('ERROR_TECNICO', 'Error técnico'),
        ('SOSPECHA_FRAUDE', 'Sospecha de fraude'),
        ('OTRO', 'Otro'),
    ]
    
    codigo_motivo = forms.ChoiceField(
        choices=MOTIVOS,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Motivo de cancelación'
    )
    
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describa detalladamente el motivo de la cancelación...',
            'required': True
        }),
        label='Descripción detallada',
        max_length=1000,
        help_text='Proporcione una descripción detallada del motivo de cancelación'
    )
    
    confirmar_cancelacion = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True
        }),
        label='Confirmo que deseo cancelar esta transacción',
        help_text='Esta acción no se puede deshacer'
    )
    
    def clean_motivo(self):
        motivo = self.cleaned_data['motivo']
        if len(motivo.strip()) < 10:
            raise forms.ValidationError(
                'La descripción debe tener al menos 10 caracteres'
            )
        return motivo.strip()


class FormularioFiltroTransaccion(forms.Form):
    """
    Formulario para filtrar la lista de transacciones.
    """
    # Excluir 'ANULADA' de las opciones de estado disponibles
    ESTADOS_FILTRO = [estado for estado in Transaccion.ESTADOS if estado[0] != 'ANULADA']
    OPCIONES_ESTADO = [('', 'Todos los estados')] + ESTADOS_FILTRO
    OPCIONES_TIPO = [('', 'Todos los tipos')] + Transaccion.TIPOS_TRANSACCION
    
    estado = forms.ChoiceField(
        choices=OPCIONES_ESTADO,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_transaccion = forms.ChoiceField(
        choices=OPCIONES_TIPO,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class FormularioSimulacion(forms.ModelForm):
    """
    Formulario para la simulación de conversión de moneda.
    """
    class Meta:
        model = SimulacionTransaccion
        fields = ['tipo_transaccion', 'moneda_origen', 'moneda_destino', 'monto_origen']
        widgets = {
            'tipo_transaccion': forms.Select(attrs={'class': 'form-select'}),
            'moneda_origen': forms.Select(attrs={'class': 'form-select'}),
            'moneda_destino': forms.Select(attrs={'class': 'form-select'}),
            'monto_origen': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar monedas activas
        from divisas.models import Moneda
        monedas_activas = Moneda.objects.filter(esta_activa=True).order_by('codigo')
        
        self.fields['moneda_origen'].queryset = monedas_activas
        self.fields['moneda_destino'].queryset = monedas_activas
        
        # Establecer etiquetas
        self.fields['tipo_transaccion'].label = 'Tipo de operación'
        self.fields['moneda_origen'].label = 'Moneda origen'
        self.fields['moneda_destino'].label = 'Moneda destino'
        self.fields['monto_origen'].label = 'Cantidad'


class FormularioTransaccion(forms.Form):
    """
    Formulario para crear transacciones de compra/venta.
    """
    moneda_origen = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Moneda origen',
        #help_text='Moneda que entrega'
    )
    
    moneda_destino = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Moneda destino',
        #help_text='Moneda que recibe'
    )
    
    monto_origen = forms.DecimalField(
        max_digits=20,
        decimal_places=8,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'placeholder': '0.00'
        }),
        label='Cantidad',
        #help_text='Cantidad en moneda origen'
    )
    
    cliente = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Cliente',
        help_text='Seleccione el cliente para esta transacción',
        required=False  # Se establecerá como requerido condicionalmente
    )
    
    metodo_pago = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_metodo_pago'
        }),
        label='Método de pago',
        #help_text='Método de pago para esta transacción'
    )
    
    metodo_cobro = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_metodo_cobro',
        }),
        label='Método de cobro',
        #help_text='Método por el cual el usuario recibirá el dinero',
        required=True
    )

    referencia_cobro = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Referencia del cobro (opcional)'
        }),
        label='Referencia de cobro',
        required=False
    )

    notas = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notas adicionales sobre la transacción...'
        }),
        label='Notas',
        required=False,
        help_text='Información adicional (opcional)'
    )
    
    # Campos específicos de Stripe
    id_metodo_pago_stripe = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_tarjetas',
        }),
        label='Tarjetas Asociadas',
        # help_text='Método por el cual el usuario recibirá el dinero',
        required=False
    )
    
    # Campos de billetera digital
    cuenta_sipap = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de cuenta SIPAP'
        }),
        label='Cuenta SIPAP',
        required=False,
        help_text='Su número de cuenta en SIPAP'
    )
    
    destinatario_western_union = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre del destinatario'
        }),
        label='Destinatario Western Union',
        required=False
    )

    tausers = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_tausers',
        }),
        label='Tausers',
        help_text='Método por el cual el usuario recibirá el dinero',
        required=False
    )
    
    # Campos de retiro en efectivo
    lugar_retiro = forms.ChoiceField(
        choices=[
            ('', 'Seleccione ubicación'),
            ('santiago_centro', 'Santiago Centro'),
            ('providencia', 'Providencia'),
            ('las_condes', 'Las Condes'),
            ('valparaiso', 'Valparaíso'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Ubicación de retiro',
        required=False
    )
    
    identificacion_retiro = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'RUT o Cédula'
        }),
        label='Documento de identidad',
        required=False,
        help_text='Para retiro en caja'
    )
    
    def __init__(self, *args, **kwargs):
        tipo_transaccion = kwargs.pop('transaction_type', 'COMPRA')
        usuario = kwargs.pop('user', None)
        moneda_origen = kwargs.pop('moneda_base', None)
        super().__init__(*args, **kwargs)
        
        # Importar aquí para evitar importaciones circulares
        from divisas.models import Moneda, MetodoPago, MetodoCobro
        from clientes.models import Cliente
        from tauser.models import Tauser

        # Agregar Tausers activos al formulario
        tausers_activos = Tauser.objects.filter(
            estado='ACTIVO'
        ).order_by('nombre')

        self.fields['tausers'].queryset = tausers_activos

        cliente = usuario.ultimo_cliente_seleccionado
        #cambiamos el filtro por moneda base directamente
        moneda_base = Moneda.objects.filter(es_moneda_base=True)
        # Filtrar métodos de pago según el tipo de transacción
        if tipo_transaccion == 'COMPRA':
            monedas_activas = Moneda.objects.filter(esta_activa=True, es_moneda_base=False, disponible_para_compra=True).order_by('codigo')
            self.fields['moneda_origen'].queryset = moneda_base
            self.fields['moneda_destino'].queryset = monedas_activas
            # Cargar métodos de pago (tarjetas) solo si existe un cliente seleccionado
            if cliente is not None:
                tarjetas_clientes_qs = MedioPago.objects.filter(activo=True, cliente_id=cliente.id).order_by('id')
            else:
                tarjetas_clientes_qs = MedioPago.objects.none()
            self.fields['id_metodo_pago_stripe'].queryset = tarjetas_clientes_qs
            metodos_pago = MetodoPago.objects.filter(
                esta_activo=True, 
                soporta_compra=True
            ).order_by('grupo_metodo', 'nombre')
            metodos_cobro = MetodoCobro.objects.filter(
                esta_activo=True,
                soporta_compra=True
            ).order_by('grupo_metodo', 'nombre')
        else:
            monedas_activas = Moneda.objects.filter(esta_activa=True, es_moneda_base=False,
                                                    disponible_para_venta=True).order_by('codigo')
            self.fields['moneda_origen'].queryset = monedas_activas
            self.fields['moneda_destino'].queryset = moneda_base
            metodos_pago = MetodoPago.objects.filter(
                esta_activo=True, 
                soporta_venta=True
            ).order_by('grupo_metodo', 'nombre')
            metodos_cobro = MetodoCobro.objects.filter(
                esta_activo=True,
                soporta_venta=True
            ).order_by('grupo_metodo', 'nombre')
        self.fields['metodo_pago'].queryset = metodos_pago
        self.fields['metodo_cobro'].queryset = metodos_cobro

        # Manejar el campo de cliente - siempre oculto ya que el cliente se selecciona desde el selector superior
        self.fields['cliente'].widget = forms.HiddenInput()
        self.fields['cliente'].required = False
        if usuario and usuario.ultimo_cliente_seleccionado:
            # El usuario tiene un cliente activo seleccionado, usarlo
            self.fields['cliente'].initial = usuario.ultimo_cliente_seleccionado.pk
            self.fields['cliente'].queryset = Cliente.objects.filter(pk=usuario.ultimo_cliente_seleccionado.pk)
        else:
            # No hay cliente seleccionado, será manejado por la validación de la vista
            self.fields['cliente'].queryset = Cliente.objects.none()
    
    def clean(self):
        datos_limpios = super().clean()
        #moneda_origen = Moneda.objects.get(es_moneda_base=True)
        moneda_origen = datos_limpios.get('moneda_origen')
        moneda_destino = datos_limpios.get('moneda_destino')
        metodo_pago = datos_limpios.get('metodo_pago')

        if self.errors:
            return datos_limpios

        if moneda_origen and moneda_destino:
            if moneda_origen == moneda_destino:
                raise forms.ValidationError(
                    'La moneda origen y destino deben ser diferentes'
                )
        
        # Validar campos específicos del método de pago
        if metodo_pago:
            self._validar_campos_metodo_pago(datos_limpios, metodo_pago)
        
        return datos_limpios

    def clean_moneda_origen(self):
        moneda_origen = self.cleaned_data.get('moneda_origen')
        if isinstance(moneda_origen, str):  # Si el valor es un string (por ejemplo, un ID)
            from divisas.models import Moneda
            try:
                moneda_origen = Moneda.objects.get(pk=moneda_origen)  # Busca el objeto por ID
            except Moneda.DoesNotExist:
                raise forms.ValidationError('La moneda origen seleccionada no es válida.')
        return moneda_origen

    def _validar_campos_metodo_pago(self, datos_limpios, metodo_pago):
        """Valida los campos específicos de cada método de pago"""
        
        if 'SIPAP' in metodo_pago.nombre:
            if not datos_limpios.get('cuenta_sipap'):
                raise forms.ValidationError('Debe proporcionar su cuenta SIPAP')
        
        elif 'Western Union' in metodo_pago.nombre:
            if not datos_limpios.get('destinatario_western_union'):
                raise forms.ValidationError('Debe proporcionar el nombre del destinatario para Western Union')
        
        elif metodo_pago.tipo_metodo == 'CASH':
            if not datos_limpios.get('lugar_retiro'):
                raise forms.ValidationError('Debe seleccionar una ubicación de retiro')
            if not datos_limpios.get('identificacion_retiro'):
                raise forms.ValidationError('Debe proporcionar su documento de identidad')
        
        elif 'Stripe' in metodo_pago.nombre:
            if not datos_limpios.get('id_metodo_pago_stripe'):
                raise forms.ValidationError('Error en el procesamiento de la tarjeta. Intente nuevamente.')


class FormularioPagoStripe(forms.Form):
    """
    Formulario para el procesamiento de pagos con Stripe.
    """
    id_metodo_pago = forms.CharField(widget=forms.HiddenInput())
    id_intento_pago = forms.CharField(widget=forms.HiddenInput(), required=False)