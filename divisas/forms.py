from django import forms
from decimal import Decimal
from .models import Moneda, PrecioBase, AlertaTasa


class FormularioSimulacion(forms.Form):
    """
    Formulario para la simulación de conversión de moneda.
    """
    TIPOS_OPERACION = [
        ('BUY', 'Comprar'),
        ('SELL', 'Vender'),
    ]
    
    tipo_operacion = forms.ChoiceField(
        choices=TIPOS_OPERACION,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'tipo_operacion'
        }),
        label='Tipo de Operación'
    )
    
    moneda_origen = forms.ModelChoiceField(
        queryset=Moneda.objects.filter(esta_activa=True).order_by('codigo'),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'moneda_origen'
        }),
        label='Moneda Origen'
    )
    
    moneda_destino = forms.ModelChoiceField(
        queryset=Moneda.objects.filter(esta_activa=True).order_by('codigo'),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'moneda_destino'
        }),
        label='Moneda Destino'
    )
    
    monto = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'monto',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Ingrese el monto'
        }),
        label='Monto'
    )
    
    def clean(self):
        datos_limpios = super().clean()
        moneda_origen = datos_limpios.get('moneda_origen')
        moneda_destino = datos_limpios.get('moneda_destino')
        
        if moneda_origen == moneda_destino:
            raise forms.ValidationError('Las monedas de origen y destino deben ser diferentes.')
        
        return datos_limpios


class FormularioActualizacionTasa(forms.ModelForm):
    """
    Formulario para actualizaciones manuales de tasas.
    """
    class Meta:
        model = PrecioBase
        fields = ['precio_base']
        widgets = {
            'precio_base': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0',
                'placeholder': 'Tasa de compra'
            }),
        }
        labels = {
            'precio_base': 'Precio Base'
        }
    
    def clean(self):
        datos_limpios = super().clean()
        precio_base = datos_limpios.get('precio_base')

        return datos_limpios


class FormularioAlerta(forms.ModelForm):
    """
    Formulario para crear alertas de tasas.
    """
    class Meta:
        model = AlertaTasa
        fields = ['moneda', 'tipo_alerta', 'tasa_objetivo', 'cambio_porcentual']
        widgets = {
            'moneda': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tipo_alerta': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tasa_objetivo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.00000001',
                'min': '0',
                'placeholder': 'Tasa objetivo (opcional)'
            }),
            'cambio_porcentual': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'max': '100',
                'placeholder': 'Porcentaje de cambio (opcional)'
            })
        }
        labels = {
            'moneda': 'Moneda',
            'tipo_alerta': 'Tipo de Alerta',
            'tasa_objetivo': 'Tasa Objetivo',
            'cambio_porcentual': 'Porcentaje de Cambio (%)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['moneda'].queryset = Moneda.objects.filter(esta_activa=True).order_by('codigo')
        self.fields['tasa_objetivo'].required = False
        self.fields['cambio_porcentual'].required = False
    
    def clean(self):
        datos_limpios = super().clean()
        tipo_alerta = datos_limpios.get('tipo_alerta')
        tasa_objetivo = datos_limpios.get('tasa_objetivo')
        cambio_porcentual = datos_limpios.get('cambio_porcentual')
        
        if tipo_alerta == 'RATE_TARGET' and not tasa_objetivo:
            raise forms.ValidationError('La tasa objetivo es requerida para alertas de tasa objetivo.')
        
        if tipo_alerta in ['RATE_INCREASE', 'RATE_DECREASE', 'VOLATILITY'] and not cambio_porcentual:
            raise forms.ValidationError('El porcentaje de cambio es requerido para este tipo de alerta.')
        
        return datos_limpios


class FormularioMoneda(forms.ModelForm):
    """
    Formulario para crear/editar monedas.
    """
    class Meta:
        model = Moneda
        fields = ['codigo', 'nombre', 'simbolo', 'esta_activa', 
                 'es_moneda_base', 'lugares_decimales', 'comision_compra', 'comision_venta']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'USD, EUR, PYG, etc.',
                'maxlength': '10'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dólar Americano, Euro, etc.'
            }),
            'simbolo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '$, €, ₲, etc.',
                'maxlength': '10'
            }),
            'esta_activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'es_moneda_base': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'lugares_decimales': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '8'
            })
            ,'comision_compra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0',
                'placeholder': 'Comisión de compra en PYG'
            }),
            'comision_venta': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0',
                'placeholder': 'Comisión de venta en PYG'
            })
        }
        labels = {
            'codigo': 'Código',
            'nombre': 'Nombre',
            'simbolo': 'Símbolo',
            'esta_activa': 'Activa',
            'es_moneda_base': 'Moneda Base',
            'lugares_decimales': 'Decimales',
            'comision_compra': 'Comisión de compra',
            'comision_venta': 'Comisión de venta'
        }
    
    def clean_codigo(self):
        codigo = self.cleaned_data['codigo'].upper()
        return codigo
    
    def clean(self):
        datos_limpios = super().clean()
        es_moneda_base = datos_limpios.get('es_moneda_base')
        
        # Asegurar que solo exista una moneda base
        if es_moneda_base:
            base_existente = Moneda.objects.filter(es_moneda_base=True)
            if self.instance.pk:
                base_existente = base_existente.exclude(pk=self.instance.pk)
            
            if base_existente.exists():
                raise forms.ValidationError('Ya existe una moneda base. Solo puede haber una moneda base.')
        
        return datos_limpios