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
                 'precio_base_inicial', 'denominacion_minima', 'stock_inicial', 
                 'lugares_decimales', 'disponible_para_compra', 'disponible_para_venta',
                 'comision_compra', 'comision_venta']
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
            'precio_base_inicial': forms.NumberInput(attrs={
                'class': 'form-control parametro-moneda',
                'placeholder': 'Precio base inicial'
                # step y min se configuran dinámicamente en __init__
            }),
            'denominacion_minima': forms.NumberInput(attrs={
                'class': 'form-control parametro-moneda',
                'placeholder': 'Denominación mínima'
                # step y min se configuran dinámicamente en __init__
            }),
            'stock_inicial': forms.NumberInput(attrs={
                'class': 'form-control parametro-moneda',
                'placeholder': 'Stock inicial'
                # step y min se configuran dinámicamente en __init__
            }),
            'lugares_decimales': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '8',
                'onchange': 'IG.aplicarPrecisionDecimalCampos(this.value);'
            }),
            'disponible_para_compra': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'disponible_para_venta': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'comision_compra': forms.NumberInput(attrs={
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
            'esta_activa': 'Habilitada',
            'precio_base_inicial': 'Precio Base Inicial',
            'denominacion_minima': 'Denominación Mínima',
            'stock_inicial': 'Stock Inicial',
            'lugares_decimales': 'Precisión Decimal',
            'disponible_para_compra': 'Disponible para Compra',
            'disponible_para_venta': 'Disponible para Venta',
            'comision_compra': 'Comisión de Compra',
            'comision_venta': 'Comisión de Venta'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Determinar la precisión (al editar usar la del instance, al crear usar default 2)
        if self.instance and self.instance.pk:
            precision = self.instance.lugares_decimales or 2
        else:
            precision = 2  # Precisión por defecto para nuevas monedas
            
        # Aplicar precisión a todos los campos de parámetros
        campos_parametros = ['precio_base_inicial', 'denominacion_minima', 'stock_inicial']
        for nombre_campo in campos_parametros:
            if nombre_campo in self.fields:
                campo = self.fields[nombre_campo]
                
                # Calcular step y min apropiados para la precisión
                step = self._obtener_step_segun_precision(precision)
                campo.widget.attrs['step'] = step
                
                # Ajustar el min para que sea compatible con el step
                if precision <= 0:
                    campo.widget.attrs['min'] = '1'
                else:
                    campo.widget.attrs['min'] = step  # Min debe ser múltiplo del step
                
                # Si estamos editando, formatear el valor actual
                if self.instance and self.instance.pk:
                    valor_actual = getattr(self.instance, nombre_campo, None)
                    if valor_actual is not None:
                        valor_formateado = self._formatear_valor_con_precision(valor_actual, precision)
                        self.initial[nombre_campo] = valor_formateado
        
        # Agregar clase CSS para identificar campos de parámetros
        for nombre_campo in ['precio_base_inicial', 'denominacion_minima', 'stock_inicial']:
            if nombre_campo in self.fields:
                clases_existentes = self.fields[nombre_campo].widget.attrs.get('class', '')
                if 'parametro-moneda' not in clases_existentes:
                    self.fields[nombre_campo].widget.attrs['class'] = clases_existentes + ' parametro-moneda'
    
    def _obtener_step_segun_precision(self, precision):
        """Obtiene el step apropiado para un campo según la precisión decimal."""
        if precision <= 0:
            return '1'
        # Crear step como 0.0...01 con precision decimales
        return '0.' + '0' * (precision - 1) + '1'
    
    def _formatear_valor_con_precision(self, valor, precision):
        """Formatea un valor decimal con la precisión especificada."""
        if valor is None:
            return None
        try:
            from decimal import Decimal
            if isinstance(valor, Decimal):
                # Convertir Decimal a float y luego formatear
                return f"{float(valor):.{precision}f}"
            else:
                return f"{float(valor):.{precision}f}"
        except (ValueError, TypeError):
            return valor
    
    def clean_codigo(self):
        codigo = self.cleaned_data['codigo'].upper()
        return codigo
    
    def clean(self):
        datos_limpios = super().clean()
        
        # Validar que los valores decimales estén alineados con la precisión
        precision = datos_limpios.get('lugares_decimales', 2)
        
        # Validar campos de parámetros con la precisión
        campos_a_validar = ['precio_base_inicial', 'denominacion_minima', 'stock_inicial']
        for nombre_campo in campos_a_validar:
            valor = datos_limpios.get(nombre_campo)
            if valor is not None:
                # Validar que el número de decimales no exceda la precisión
                from decimal import Decimal
                try:
                    valor_decimal = Decimal(str(valor))
                    # Obtener el número de decimales del valor
                    decimales_valor = abs(valor_decimal.as_tuple().exponent)
                    
                    if decimales_valor > precision:
                        self.add_error(nombre_campo, 
                            f'El valor no puede tener más de {precision} decimales.')
                        
                except (ValueError, TypeError):
                    # Si no se puede convertir a decimal, Django ya validará esto
                    pass
        
        return datos_limpios