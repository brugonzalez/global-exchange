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
from django import forms
from .models import PreferenciaCliente
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Cliente, CategoriaCliente, ClienteUsuario, MonedaFavorita
from divisas.models import Moneda

Usuario = get_user_model()

class FormularioPreferenciaCliente(forms.ModelForm):
    """
    Formulario para la gestión de preferencias de clientes.
    Permite establecer límites y preferencias personalizadas que sobrescriben los valores por defecto de la categoría del cliente.
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

class FormularioCliente(forms.ModelForm):
    """
    Formulario para crear y editar clientes.

    Este formulario valida de manera diferente según el tipo de cliente:

    - ``FISICA``: requiere nombre y apellido, y limpia campos de empresa.
    - ``JURIDICA``: requiere nombre de empresa y representante legal, y limpia nombre/apellido.

    Además agrega un comportamiento dinámico para alternar campos en la interfaz.
    """
    class Meta:
        model = Cliente
        fields = [
            'tipo_cliente', 'estado', 'categoria',
            'nombre', 'apellido', 'nombre_empresa', 'representante_legal',
            'numero_identificacion', 'email', 'telefono', 'direccion'
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
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y aplica reglas dinámicas a los campos.
        Notes:
            - Si hay edicion, se establecen los requerimientos por tipo de cliente.
        """
        super().__init__(*args, **kwargs)
        
        # Hacer campos requeridos según el tipo de cliente
        if self.instance and self.instance.pk:
            self._establecer_requerimientos_campos()
        
        # Añadir clases JavaScript para el comportamiento dinámico del formulario
        self.fields['tipo_cliente'].widget.attrs['onchange'] = 'alternarCamposPorTipoCliente()'

    def clean(self):
        """
        Valida los campos según el tipo de cliente y limpia los no aplicables.

        Returns:
            dict: Datos limpios después de la validación con campos no aplicables vaciados.
        
        Raises:
            ValidationError: Si faltan campos requeridos por tipo de cliente.
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
        Evita requerir campos que no aplican al tipo seleccionado"""
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
        """Valida que el campo de permisos contenga JSON válido."""
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

   Incluye los siguientes criterios opcionales:

    - ``busqueda``: texto libre que puede coincidir con nombre, empresa, email o identificación.
    - ``tipo_cliente``: restringe la búsqueda por tipo de cliente (FISICA/JURIDICA).
    - ``estado``: filtra por estado actual del cliente.
    - ``categoria``: limita la búsqueda a una categoría específica.
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

    - Evita que se dupliquen monedas ya asociadas al cliente.
    - Requiere un valor de orden numérico (entero ≥ 0).

    Args:
        cliente (Cliente, opcional): instancia de cliente para filtrar las monedas
            disponibles. Si no se proporciona, mostrará todas las monedas activas.
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
    Args:
        cliente (Cliente, opcional): instancia de cliente para filtrar los usuarios
            disponibles. Si no se proporciona, mostrará todos los usuarios.
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
        """Valida que el campo de permisos contenga JSON válido."""
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
    Formulario para gestionar las categorías de clientes (límites y márgenes).
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