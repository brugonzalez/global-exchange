"""
Formularios relacionados con la gestión de clientes.

Incluye:
- Preferencias de clientes
- Creación y edición de clientes
- Asignación de usuarios a clientes
- Búsqueda y filtrado de clientes
- Monedas favoritas
- Categorías de clientes
"""
from decimal import Decimal

from django import forms
from .models import PreferenciaCliente
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Cliente, CategoriaCliente, ClienteUsuario, MonedaFavorita, LimiteTransaccionCliente
from divisas.models import Moneda

Usuario = get_user_model()

class FormularioPreferenciaCliente(forms.ModelForm):
    """
    Formulario para la gestión de preferencias de clientes.
    Permite establecer límites y preferencias personalizadas que sobrescriben los valores por defecto.

    Attributes
    -------------
    limite_compra : NumberInput
        Límite de compra personalizado.
    limite_venta : NumberInput
        Límite de venta personalizado.
    frecuencia_maxima : NumberInput
        Frecuencia máxima de operaciones diarias.
    preferencia_tipo_cambio : TextInput
        Preferencia de tipo de cambio.
    """
    class Meta:
        model = PreferenciaCliente
        fields = ['limite_compra', 'limite_venta', 'frecuencia_maxima', 'preferencia_tipo_cambio']
        widgets = {
            'limite_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'limite_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'frecuencia_maxima': forms.NumberInput(attrs={'class': 'form-control'}),
            'preferencia_tipo_cambio': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FormularioLimiteCliente(forms.ModelForm):
    """
    Permite establecer límites personalizados para un cliente específico.

    Attributes
    -------------
    monto_limite_diario : IntegerField
        Límite diario de transacciones en PYG.
    monto_limite_mensual : IntegerField
        Límite mensual de transacciones en PYG.

    """
    class Meta:
        model = LimiteTransaccionCliente
        fields = ['monto_limite_diario', 'monto_limite_mensual']
        widgets = {
            'monto_limite_diario': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '1',
                'placeholder': '0',
                'help_text': 'El monto límite diario para transacciones en PYG'
            }),
            'monto_limite_mensual': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '1',
                'placeholder': '0',
                'help_text': 'El monto límite mensual para transacciones en PYG'
            }),
        }
        labels = {
            'monto_limite_diario': 'Límite Diario (PYG)',
            'monto_limite_mensual': 'Límite Mensual (PYG)',
        }

    def __init__(self, *args, **kwargs):
        """Hace que los campos de límites no sean obligatorios.

        Si el usuario deja un campo vacío, se interpretará como 0 (sin límite).
        """
        super().__init__(*args, **kwargs)
        # Reemplazar widgets y tipos para forzar enteros en la UI
        self.fields['monto_limite_diario'] = forms.IntegerField(
            required=False,
            min_value=0,
            label=self.fields['monto_limite_diario'].label,
            widget=forms.TextInput(attrs={
                'class': 'form-control numero-miles',
                'inputmode': 'numeric',
                'autocomplete': 'off',
                'placeholder': '0',
                'data-formato': 'miles'
            })
        )
        self.fields['monto_limite_mensual'] = forms.IntegerField(
            required=False,
            min_value=0,
            label=self.fields['monto_limite_mensual'].label,
            widget=forms.TextInput(attrs={
                'class': 'form-control numero-miles',
                'inputmode': 'numeric',
                'autocomplete': 'off',
                'placeholder': '0',
                'data-formato': 'miles'
            })
        )
        # Ajustar valores iniciales (remover decimales si vienen del modelo DecimalField)
        for campo in ['monto_limite_diario', 'monto_limite_mensual']:
            val = self.initial.get(campo)
            if val is not None:
                try:
                    self.initial[campo] = int(Decimal(val))
                except Exception:
                    pass

    def clean_monto_limite_diario(self):
        val = self.cleaned_data.get('monto_limite_diario')
        if val in (None, ''):
            return Decimal('0')
        return Decimal(int(val))

    def clean_monto_limite_mensual(self):
        val = self.cleaned_data.get('monto_limite_mensual')
        if val in (None, ''):
            return Decimal('0')
        return Decimal(int(val))

    def clean(self):
        """
        Valida que los límites sean números no negativos y que se seleccione un cliente.
        
        Returns
        -------
        dict
            Datos limpios después de la validación.
        Raises
        -------
        ValidationError
            Si los límites son negativos o no se selecciona un cliente.
        """
        cleaned_data = super().clean()
        monto_diario = cleaned_data.get('monto_limite_diario')
        monto_mensual = cleaned_data.get('monto_limite_mensual')

        # Valores ya limpiados por clean_field individuales (enteros envueltos en Decimal)


        if monto_diario is not None and monto_diario < 0:
            self.add_error('monto_limite_diario', 'El límite diario no puede ser negativo.')

        if monto_mensual is not None and monto_mensual < 0:
            self.add_error('monto_limite_mensual', 'El límite mensual no puede ser negativo.')

        return cleaned_data
    
    
class FormularioCliente(forms.ModelForm):
    """
    Formulario para crear y editar clientes.

    Este formulario valida de manera diferente según el tipo de cliente:

    - ``FISICA``: requiere nombre y apellido, y limpia campos de empresa.
    - ``JURIDICA``: requiere nombre de empresa y representante legal, y limpia nombre/apellido.

    Además agrega un comportamiento dinámico para alternar campos en la interfaz.

    Attributes
    -------------
    tipo_cliente : Select
        Tipo de cliente (FISICA o JURIDICA).
    estado : Select
        Estado del cliente (activo, inactivo, etc.).
    categoria : Select
        Categoría del cliente.
    nombre : TextInput
        Nombre del cliente (caso persona física).
    apellido : TextInput
        Apellido del cliente (caso persona física).
    nombre_empresa : TextInput
        Nombre de la empresa (caso persona jurídica).
    representante_legal : TextInput
        Nombre del representante legal (caso persona jurídica).
    numero_identificacion : TextInput
        Número de identificación del cliente.
    email : EmailInput
        Correo electrónico del cliente.
    telefono : TextInput
        Número de teléfono del cliente.
    direccion : Textarea
        Dirección del cliente.
    usa_limites_default : CheckboxInput
        Indica si el cliente usa los límites definidos por defecto o personalizados.
    
    
    """
    class Meta:
        model = Cliente
        fields = [
            'tipo_cliente', 'estado', 'categoria',
            'nombre', 'apellido', 'nombre_empresa', 'representante_legal',
            'numero_identificacion', 'email', 'telefono', 'direccion', 'usa_limites_default'
        ]
        widgets = {
            'tipo_cliente': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'representante_legal': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_identificacion': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            # Usar Textarea para direccion y evitar que el usuario la redimensione
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'usa_limites_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'tipo_cliente': 'Tipo de Cliente',
            'estado': 'Estado',
            'categoria': 'Categoría del Cliente',
            'nombre': 'Nombre(s)',
            'apellido': 'Apellido(s)',
            'nombre_empresa': 'Nombre de la Empresa',
            'representante_legal': 'Representante Legal',
            'numero_identificacion': 'Número de Identificación',
            'email': 'Correo Electrónico',
            'telefono': 'Teléfono de Contacto',
            'direccion': 'Dirección',
            'usa_limites_default': 'Usar Límites por Defecto'
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y aplica reglas dinámicas a los campos 
        (se requieren los campos según el tipo de cliente).
        
        Notes
        -----
        - Si hay edicion, se establecen los requerimientos por tipo de cliente.
        """
        super().__init__(*args, **kwargs)
        
        # Hacer campos requeridos según el tipo de cliente
        if self.instance and self.instance.pk:
            self._establecer_requerimientos_campos()
            # Deshabilitar edición de tipo_cliente cuando el registro ya existe
            self.fields['tipo_cliente'].disabled = True  # Django mantendrá el valor original
            # Quitar 'required' para evitar que crispy genere asterisco y validaciones sobre campo deshabilitado
            self.fields['tipo_cliente'].required = False
            # (Opcional) añadir una clase visual para indicar que está bloqueado
            clases = self.fields['tipo_cliente'].widget.attrs.get('class', '')
            if 'is-disabled' not in clases:
                self.fields['tipo_cliente'].widget.attrs['class'] = (clases + ' is-disabled').strip()
        
        # Añadir clases JavaScript para el comportamiento dinámico del formulario
        self.fields['tipo_cliente'].widget.attrs['onchange'] = 'alternarCamposPorTipoCliente()'

    def clean(self):
        """
        Valida los campos según el tipo de cliente y limpia los no aplicables.

        Returns
        -------
        dict
            Datos limpios después de la validación con campos no aplicables vaciados.
        
        Raises
        -------
        ValidationError
            Si faltan campos requeridos por tipo de cliente.
        """
        datos_limpios = super().clean()
        tipo_cliente = datos_limpios.get('tipo_cliente')
        
        if tipo_cliente == 'FISICA':
            # Persona física requiere nombre y apellido
            if not datos_limpios.get('nombre'):
                raise ValidationError({'nombre': 'El nombre es requerido para personas físicas.'})
            if not datos_limpios.get('apellido'):
                raise ValidationError({'apellido': 'El apellido es requerido para personas físicas.'})
            
            # Limpiar campos de persona jurídica
            datos_limpios['nombre_empresa'] = ''
            datos_limpios['representante_legal'] = ''
            
        elif tipo_cliente == 'JURIDICA':
            # Persona jurídica requiere nombre de la empresa
            if not datos_limpios.get('nombre_empresa'):
                raise ValidationError({'nombre_empresa': 'El nombre de la empresa es requerido para personas jurídicas.'})
            
            # Limpiar campos de persona física
            datos_limpios['nombre'] = ''
            datos_limpios['apellido'] = ''
        
        return datos_limpios

    def _establecer_requerimientos_campos(self):
        """Establece los requerimientos de los campos según el tipo de cliente.
        Evita requerir campos que no aplican al tipo seleccionado

        Para personas físicas:
            - Se requiere el nombre y apellido.
        Para personas jurídicas:
            - Se requiere el nombre de la empresa y el representante legal
        """
        if self.instance.tipo_cliente == 'FISICA':
            self.fields['nombre'].required = True
            self.fields['apellido'].required = True
            self.fields['nombre_empresa'].required = False
            self.fields['representante_legal'].required = False
        elif self.instance.tipo_cliente == 'JURIDICA':
            self.fields['nombre_empresa'].required = True
            self.fields['nombre'].required = False
            self.fields['apellido'].required = False


class FormularioClienteUsuario(forms.ModelForm):
    """
    Formulario para gestionar las asociaciones usuario-cliente con sus estados.

    Permite asignar un usuario activo a un cliente.

    Attributes
    ----------
    usuario : Usuario
        El usuario activo que se asignará al cliente.
    permisos : dict
        Permisos específicos para este usuario en este cliente.
    esta_activo : bool
        Indica si la asociación usuario-cliente está activa.
    """
    usuario = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Seleccionar usuario..."
    )
    
    permisos = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Permisos específicos en formato JSON (opcional)'
        }),
        help_text='Permisos específicos para este usuario en este cliente (formato JSON)'
    )
    
    class Meta:
        model = ClienteUsuario
        fields = ['usuario', 'esta_activo', 'permisos']
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'esta_activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario.
        Excluye del queryset los usuarios ya asociados al cliente.
        """
        self.cliente = kwargs.pop('cliente', None)
        super().__init__(*args, **kwargs)
        
        if self.cliente:
            # Excluir usuarios ya asociados con este cliente
            usuarios_existentes = self.cliente.usuarios.values_list('id', flat=True)
            if self.instance and self.instance.pk:
                # Permitir el usuario actual al editar
                usuarios_existentes = usuarios_existentes.exclude(id=self.instance.usuario.id)
            
            self.fields['usuario'].queryset = Usuario.objects.filter(
                is_active=True
            ).exclude(id__in=usuarios_existentes)

    def clean_permisos(self):
        """Valida que el campo de permisos contenga JSON válido.
        
        Returns
        -------
        dict
            Un diccionario con los permisos válidos o un diccionario vacío si no se especifican permisos.
        """
        permisos = self.cleaned_data.get('permisos', '').strip()
        if permisos:
            try:
                import json
                # Analiza y devuelve el objeto JSON para asegurar que es válido
                return json.loads(permisos)
            except (json.JSONDecodeError, TypeError):
                raise ValidationError('Los permisos deben estar en formato JSON válido.')
        # Devuelve un diccionario vacío si no se especifican permisos
        return {}


class FormularioBusquedaCliente(forms.Form):
    """
    Formulario para búsqueda y filtrado de clientes (solo lectura)

    Permite buscar clientes según diversos criterios.
    
    Attributes
    ----------
    busqueda : str
        Texto libre que puede coincidir con nombre, empresa, email o identificación.
    tipo_cliente : str
        Tipo de cliente (FISICA/JURIDICA).
    estado : str
        Estado actual del cliente.
    categoria : CategoriaCliente
        Categoría específica del cliente.
    """
    busqueda = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre, empresa, email o identificación...'
        })
    )
    
    tipo_cliente = forms.ChoiceField(
        choices=[('', 'Todos los tipos')] + Cliente.TIPOS_CLIENTE,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    estado = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + Cliente.ESTADOS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    categoria = forms.ModelChoiceField(
        queryset=CategoriaCliente.objects.all(),
        required=False,
        empty_label="Todas las categorías",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class FormularioAnadirMonedaFavorita(forms.ModelForm):
    """
    Formulario para asociar monedas favoritas a un cliente.

    Este formulario permite seleccionar una moneda activa y asignarle un orden
    de preferencia dentro de la lista de monedas favoritas del cliente.

    Notes
    -----
    - Evita que se dupliquen monedas ya asociadas al cliente.
    - Requiere un valor de orden numérico (entero ≥ 0).

    """
    class Meta:
        model = MonedaFavorita
        fields = ['moneda', 'orden']
        widgets = {
            'moneda': forms.Select(attrs={'class': 'form-control'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y excluye del queryset las monedas
        que ya fueron marcadas como favoritas por el cliente.
        """
        self.cliente = kwargs.pop('cliente', None)
        super().__init__(*args, **kwargs)
        
        if self.cliente:
            # Excluir monedas que ya son favoritas para este cliente
            monedas_existentes = self.cliente.monedas_favoritas.values_list('moneda_id', flat=True)
            self.fields['moneda'].queryset = Moneda.objects.filter(
                esta_activa=True
            ).exclude(id__in=monedas_existentes)


class FormularioAsignarUsuarioACliente(forms.Form):
    """
    Formulario para asignar un usuario a un cliente con un rol específico y permisos opcionales.

    Attributes
    ----------
    cliente : Cliente
        El cliente al que se asignará el usuario.
    rol : Rol
        El rol que se asignará al usuario en el cliente.
    permisos : dict
        Permisos específicos para el usuario en el cliente.
    """
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(estado='ACTIVO'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Seleccionar cliente..."
    )
    
    rol = forms.ChoiceField(
        choices=ClienteUsuario.ROLES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='AUTORIZADO'
    )
    
    permisos = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Permisos específicos en formato JSON (opcional)'
        }),
        help_text='Permisos específicos para este usuario en este cliente (formato JSON)'
    )

    def clean_permisos(self):
        """Valida que el campo de permisos contenga JSON válido.

        Returns
        -------
        dict
            Un diccionario con los permisos válidos o un diccionario vacío si no se especifican permisos.
        """
        permisos = self.cleaned_data.get('permisos')
        if permisos:
            try:
                import json
                json.loads(permisos)
            except json.JSONDecodeError:
                raise ValidationError('Los permisos deben estar en formato JSON válido.')
        return permisos or '{}'


class FormularioCategoriaCliente(forms.ModelForm):
    """
    Formulario para gestionar las categorías de clientes con sus preferencias exclusivas de la categoría.

    Attributes
    ----------
    nombre : str
        Nombre de la categoría.
    descripcion : str
        Descripción de la categoría.
    limite_transaccion_diario : float
        Límite de transacción diario para la categoría.
    limite_transaccion_mensual : float
        Límite de transacción mensual para la categoría.
    margen_tasa_preferencial : float
        Margen de tasa preferencial para la categoría.
    """
    class Meta:
        model = CategoriaCliente
        fields = [
            'nombre', 'descripcion', 'limite_transaccion_diario',
            'limite_transaccion_mensual', 'margen_tasa_preferencial', 'nivel_prioridad'
        ]
        widgets = {
            'nombre': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'limite_transaccion_diario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'limite_transaccion_mensual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'margen_tasa_preferencial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'nivel_prioridad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
        }


class FormularioEditarCategoriaCliente(forms.ModelForm):
    """Formulario para editar categorías de cliente."""

    class Meta:
        model = CategoriaCliente
        fields = ['margen_tasa_preferencial', 'descripcion']
        widgets = {
            'margen_tasa_preferencial': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'min': '0.0001',
                'placeholder': 'Ej: 0.0100 (1%)'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la categoría'
            })
        }
        labels = {
            'margen_tasa_preferencial': 'Margen de Tasa Preferencial (%)',
            'descripcion': 'Descripción'
        }

    def clean_margen_tasa_preferencial(self):
        valor = self.cleaned_data['margen_tasa_preferencial']

        if valor <= Decimal('0'):
            raise forms.ValidationError('El margen debe ser mayor a 0.')

        if valor > Decimal('1.0000'):
            raise forms.ValidationError('El margen no puede ser mayor al 100%.')

        return valor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Agregar help text personalizado
        self.fields['margen_tasa_preferencial'].help_text = (
            'Ingrese el margen como decimal (ej: 0.0100 = 1%, 0.0250 = 2.5%)'
        )