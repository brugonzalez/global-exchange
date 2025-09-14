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
        fields = ['codigo', 'nombre', 'simbolo', 'pais', 'esta_activa', 
                 'precio_base_inicial', 'denominacion_minima', 'stock_inicial', 
                 'lugares_decimales', 'disponible_para_compra', 'disponible_para_venta']
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
            'pais': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Seleccionar país (opcional)'
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
            })
        }
        labels = {
            'codigo': 'Código',
            'nombre': 'Nombre',
            'simbolo': 'Símbolo',
            'pais': 'País',
            'esta_activa': 'Habilitada',
            'precio_base_inicial': 'Precio Base Inicial',
            'denominacion_minima': 'Denominación Mínima',
            'stock_inicial': 'Stock Inicial',
            'lugares_decimales': 'Precisión Decimal',
            'disponible_para_compra': 'Disponible para Compra',
            'disponible_para_venta': 'Disponible para Venta'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Determinar la precisión (al editar usar la del instance, al crear usar default 2)
        if self.instance and self.instance.pk:
            precision = self.instance.lugares_decimales or 2
        else:
            precision = 2  # Precisión por defecto para nuevas monedas
            
        # Aplicar configuración específica a cada campo
        # denominacion_minima y stock_inicial siempre son enteros (sin decimales)
        campos_enteros = ['denominacion_minima', 'stock_inicial']
        for nombre_campo in campos_enteros:
            if nombre_campo in self.fields:
                campo = self.fields[nombre_campo]
                campo.widget.attrs['step'] = '1'
                campo.widget.attrs['min'] = '0' if nombre_campo == 'stock_inicial' else '1'
                
                # Si estamos editando, formatear como entero
                if self.instance and self.instance.pk:
                    valor_actual = getattr(self.instance, nombre_campo, None)
                    if valor_actual is not None:
                        self.initial[nombre_campo] = int(valor_actual)
        
        # precio_base_inicial usa la precisión definida por lugares_decimales
        if 'precio_base_inicial' in self.fields:
            campo = self.fields['precio_base_inicial']
            step = self._obtener_step_segun_precision(precision)
            campo.widget.attrs['step'] = step
            
            # Ajustar el min para que sea compatible con el step
            if precision <= 0:
                campo.widget.attrs['min'] = '1'
            else:
                campo.widget.attrs['min'] = step
            
            # Si estamos editando, formatear el valor actual
            if self.instance and self.instance.pk:
                valor_actual = getattr(self.instance, 'precio_base_inicial', None)
                if valor_actual is not None:
                    valor_formateado = self._formatear_valor_con_precision(valor_actual, precision)
                    self.initial['precio_base_inicial'] = valor_formateado
        
        # Agregar clase CSS para identificar campos de parámetros
        for nombre_campo in ['precio_base_inicial', 'denominacion_minima', 'stock_inicial']:
            if nombre_campo in self.fields:
                clases_existentes = self.fields[nombre_campo].widget.attrs.get('class', '')
                if 'parametro-moneda' not in clases_existentes:
                    self.fields[nombre_campo].widget.attrs['class'] = clases_existentes + ' parametro-moneda'
        
        # Configurar campos de disponibilidad con JavaScript para control dinámico
        if 'disponible_para_compra' in self.fields:
            self.fields['disponible_para_compra'].widget.attrs['onchange'] = 'controlarDisponibilidadComisiones();'
        if 'disponible_para_venta' in self.fields:
            self.fields['disponible_para_venta'].widget.attrs['onchange'] = 'controlarDisponibilidadComisiones();'
    
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
        
        # Validar denominacion_minima y stock_inicial como enteros
        campos_enteros = ['denominacion_minima', 'stock_inicial']
        for nombre_campo in campos_enteros:
            valor = datos_limpios.get(nombre_campo)
            if valor is not None:
                # Verificar que sea un entero
                from decimal import Decimal
                try:
                    valor_decimal = Decimal(str(valor))
                    # Obtener el número de decimales del valor
                    decimales_valor = abs(valor_decimal.as_tuple().exponent)
                    
                    if decimales_valor > 0:
                        self.add_error(nombre_campo, 
                            f'{self.fields[nombre_campo].label} debe ser un número entero (sin decimales).')
                        
                except (ValueError, TypeError):
                    # Si no se puede convertir a decimal, Django ya validará esto
                    pass
        
        # Validar precio_base_inicial con la precisión definida
        if 'precio_base_inicial' in datos_limpios:
            valor = datos_limpios.get('precio_base_inicial')
            if valor is not None:
                from decimal import Decimal
                try:
                    valor_decimal = Decimal(str(valor))
                    # Obtener el número de decimales del valor
                    decimales_valor = abs(valor_decimal.as_tuple().exponent)
                    
                    if decimales_valor > precision:
                        self.add_error('precio_base_inicial', 
                            f'El valor no puede tener más de {precision} decimales.')
                        
                except (ValueError, TypeError):
                    # Si no se puede convertir a decimal, Django ya validará esto
                    pass
        
        return datos_limpios