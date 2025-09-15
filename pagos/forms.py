from django import forms
from django.core.exceptions import ValidationError
from .models import MedioPago


class FormularioMedioPago(forms.ModelForm):
    """
    Formulario para crear y editar medios de pago.
    Se adapta dinámicamente según el tipo de medio de pago seleccionado.
    Actualmente soporta:
    - Tarjetas de crédito (integración con Stripe)

    Atributtes
    ----------
    banco : forms.CharField
        Nombre del banco para cuentas bancarias.
    numero_cuenta : forms.CharField
        Número de cuenta bancaria.
    tipo_cuenta : forms.ChoiceField
        Tipo de cuenta bancaria (Ahorros o Corriente).
    proveedor_billetera : forms.ChoiceField
        Proveedor de billetera digital (PayPal, Sipap, etc.).
    cuenta_billetera : forms.EmailField
        Cuenta o email asociado a la billetera digital.
    stripe_token : forms.CharField
        Token de Stripe para tarjetas de crédito.
    ultimos_digitos : forms.CharField
        Últimos 4 dígitos de la tarjeta (se llena automáticamente).
    """

    # Campos adicionales para diferentes tipos de medios de pago
    banco = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre del banco'
        })
    )

    numero_cuenta = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de cuenta'
        })
    )

    tipo_cuenta = forms.ChoiceField(
        choices=[
            ('', 'Seleccione tipo de cuenta'),
            ('AHORROS', 'Ahorros'),
            ('CORRIENTE', 'Corriente')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    proveedor_billetera = forms.ChoiceField(
        choices=[
            ('', 'Seleccione proveedor'),
            ('PAYPAL', 'PayPal'),
            ('SIPAP', 'Sipap'),
            ('MERCADO_PAGO', 'Mercado Pago'),
            ('OTROS', 'Otros')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    cuenta_billetera = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        })
    )

    # Token de Stripe para tarjetas
    stripe_token = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.HiddenInput()
    )

    # Últimos 4 dígitos de la tarjeta (se llena automáticamente)
    ultimos_digitos = forms.CharField(
        max_length=4,
        required=False,
        widget=forms.HiddenInput()
    )



    class Meta:
        """
        Meta información del formulario.
        Define el modelo asociado y los campos a incluir.
        """
        model = MedioPago
        fields = [
            'tipo', 'nombre_titular'
        ]
        widgets = {
            'tipo_medio_pago': forms.Select(attrs={
                'class': 'form-control',
                'id': 'tipo_medio_pago'
            })
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y prellena campos si es una edición.
        Args:
            *args: Argumentos posicionales.
            **kwargs: Argumentos nombrados.
        """
        super().__init__(*args, **kwargs)

        # Hacer que el tipo de medio de pago sea requerido
        self.fields['tipo'].required = True

        # Si es una edición, prellenar campos específicos
        if self.instance and self.instance.pk:
            self._prellenar_campos_existentes()

    def _prellenar_campos_existentes(self):
        """Prellena los campos específicos si el medio de pago ya existe."""
        datos_especificos = self.instance.datos_especificos or {}

        if self.instance.tipo_medio_pago in ['TARJETA_CREDITO', 'TARJETA_DEBITO']:
            self.fields['ultimos_digitos'].initial = datos_especificos.get('ultimos_digitos', '')

        elif self.instance.tipo_medio_pago == 'CUENTA_BANCARIA':
            self.fields['banco'].initial = datos_especificos.get('banco', '')
            self.fields['numero_cuenta'].initial = datos_especificos.get('numero_cuenta', '')
            self.fields['tipo_cuenta'].initial = datos_especificos.get('tipo_cuenta', '')

        elif self.instance.tipo_medio_pago == 'BILLETERA_DIGITAL':
            self.fields['proveedor_billetera'].initial = datos_especificos.get('proveedor', '')
            self.fields['cuenta_billetera'].initial = datos_especificos.get('cuenta', '')

    def clean(self):
        """
        Validaciones personalizadas según el tipo de medio de pago.

        Raises:
        ------
            ValidationError: Si alguna validación falla.

        Returns:
        -------
            dict: Datos limpios del formulario.
        """
        cleaned_data = super().clean()
        tipo_medio_pago = cleaned_data.get('tipo')

        if not tipo_medio_pago:
            raise ValidationError('Debe seleccionar un tipo de medio de pago.')

        # Validaciones específicas por tipo
        if tipo_medio_pago in ['tarjeta']:
            self._validar_tarjeta(cleaned_data)

        elif tipo_medio_pago == 'CUENTA_BANCARIA':
            self._validar_cuenta_bancaria(cleaned_data)

        elif tipo_medio_pago == 'BILLETERA_DIGITAL':
            self._validar_billetera_digital(cleaned_data)

        return cleaned_data

    def _validar_tarjeta(self, cleaned_data):
        """
        Validaciones específicas para tarjetas de crédito.

        Raises:
        ------
            ValidationError: Si el token de Stripe no está presente al crear.

        Returns:
        -------
            None: no retorna nada si la validación pasa.
        """
        stripe_token = cleaned_data.get('stripe_token')

        if not stripe_token and not self.instance.pk:
            raise ValidationError('Se requiere información válida de la tarjeta.')

    def _validar_cuenta_bancaria(self, cleaned_data):
        """
        Validaciones específicas para cuentas bancarias.

        Atributes:
        ----------
            banco (str): Nombre del banco.
            numero_cuenta (str): Número de cuenta bancaria.
            tipo_cuenta (str): Tipo de cuenta (Ahorros o Corriente).

        Raises:
        ------
            ValidationError: Si algún campo requerido no está presente o es inválido.

        Returns:
        -------
            None: no retorna nada si la validación pasa.

        """
        banco = cleaned_data.get('banco')
        numero_cuenta = cleaned_data.get('numero_cuenta')
        tipo_cuenta = cleaned_data.get('tipo_cuenta')

        if not banco:
            raise ValidationError('El nombre del banco es requerido.')

        if not numero_cuenta:
            raise ValidationError('El número de cuenta es requerido.')

        if not tipo_cuenta:
            raise ValidationError('El tipo de cuenta es requerido.')

        # Validar que el número de cuenta solo contenga números
        if not numero_cuenta.isdigit():
            raise ValidationError('El número de cuenta debe contener solo números.')

    def _validar_billetera_digital(self, cleaned_data):
        """
        Validaciones específicas para billeteras digitales.

        Atributes:
        ----------
            proveedor (str): Proveedor de la billetera digital.
            cuenta (str): Cuenta o email asociado a la billetera digital.

        Raises:
        ------
            ValidationError: Si algún campo requerido no está presente.

        Returns:
        -------
            None: no retorna nada si la validación pasa.
        """
        proveedor = cleaned_data.get('proveedor_billetera')
        cuenta = cleaned_data.get('cuenta_billetera')

        if not proveedor:
            raise ValidationError('Debe seleccionar un proveedor de billetera digital.')

        if not cuenta:
            raise ValidationError('La cuenta/email de la billetera es requerida.')

    def save(self, commit=True):
        """
        Guarda el medio de pago, construyendo los datos específicos según el tipo.

        Arguments:
        ----------
            commit (bool): Si es True, guarda la instancia en la base de datos.

        Attributes:
        ----------
            medio_pago (MedioPago): Instancia del medio de pago a guardar.

        Returns:
        -------
            MedioPago: Instancia del medio de pago guardada.

        Raises:
        ------
            ValidationError: Si el formulario no es válido.
        """
        medio_pago = super().save(commit=False)

        # Construir datos específicos según el tipo
        datos_especificos = {}
        tipo_medio_pago = self.cleaned_data['tipo']

        if tipo_medio_pago in ['tarjeta']:
            datos_especificos = self._construir_datos_tarjeta()

        elif tipo_medio_pago == 'CUENTA_BANCARIA':
            datos_especificos = self._construir_datos_cuenta_bancaria()

        elif tipo_medio_pago == 'BILLETERA_DIGITAL':
            datos_especificos = self._construir_datos_billetera()

        medio_pago.datos_especificos = datos_especificos

        if commit:
            medio_pago.save()

        return medio_pago

    def _construir_datos_tarjeta(self):
        """
        Construye los datos específicos para tarjetas de crédito.

        Attributes:
        ----------
            stripe_token (str): Token de Stripe.
            ultimos_digitos (str): Últimos 4 dígitos de la tarjeta.
            procesador (str): Nombre del procesador de pagos (si aplica).

        Returns:
        -------
            dict: Datos específicos de la tarjeta.

        """
        return {
            'stripe_token': self.cleaned_data.get('stripe_token', ''),
            'ultimos_digitos': self.cleaned_data.get('ultimos_digitos', ''),
            'procesador': 'stripe'
        }

    def _construir_datos_cuenta_bancaria(self):
        """
        Construye los datos específicos para cuentas bancarias.

        Returns:
        -------
            dict: Datos específicos de la cuenta bancaria.
        """
        return {
            'banco': self.cleaned_data['banco'],
            'numero_cuenta': self.cleaned_data['numero_cuenta'],
            'tipo_cuenta': self.cleaned_data['tipo_cuenta']
        }

    def _construir_datos_billetera(self):
        """
        Construye los datos específicos para billeteras digitales.

        Returns:
        -------
            dict: Datos específicos de la billetera digital.

        """
        return {
            'proveedor': self.cleaned_data['proveedor_billetera'],
            'cuenta': self.cleaned_data['cuenta_billetera']
        }