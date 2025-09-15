from django import forms
from decimal import Decimal
from .models import Moneda, PrecioBase, AlertaTasa


class FormularioSimulacion(forms.Form):
    """
    Formulario para la simulación de conversión de moneda.
    El usuario elige operación (compra/venta), monedas y monto.

    Attributes
    ----------
    tipo_operacion : str
        Tipo de operación (compra/venta).
    moneda_origen : Moneda
        Moneda de origen para la conversión.
    moneda_destino : Moneda
        Moneda de destino para la conversión.
    monto : Decimal
        Monto a convertir.
    
    Notes
    -----
    - Solo se usa para simular, no guarda nada en la base de datos.
    - No permite elegir la misma moneda como origen y destino.
    - Una de las monedas debe ser la moneda base (Gs).
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

    cantidad_entrega = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'cantidad_entrega',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Ingrese la cantidad'
        }),
        label='Cantidad a Entregar',
        required=False
    )

    cantidad_recibir = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'cantidad_recibir',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Ingrese la cantidad'
        }),
        label='Cantidad a Recibir',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        moneda_origen = None
        moneda_destino = None
        # Buscar en initial, data o POST
        if 'initial' in kwargs:
            moneda_origen = kwargs['initial'].get('moneda_origen')
            moneda_destino = kwargs['initial'].get('moneda_destino')
        if 'data' in kwargs:
            moneda_origen = kwargs['data'].get('moneda_origen') or moneda_origen
            moneda_destino = kwargs['data'].get('moneda_destino') or moneda_destino
        # Si es instancia de Moneda, usar directamente
        if moneda_origen and not isinstance(moneda_origen, Moneda):
            try:
                moneda_origen = Moneda.objects.get(pk=moneda_origen)
            except Exception:
                moneda_origen = None
        if moneda_destino and not isinstance(moneda_destino, Moneda):
            try:
                moneda_destino = Moneda.objects.get(pk=moneda_destino)
            except Exception:
                moneda_destino = None
        # Configurar step/min para cantidad_entrega
        if moneda_origen:
            precision = moneda_origen.lugares_decimales or 2
            step = self._obtener_step_segun_precision(precision)
            self.fields['cantidad_entrega'].widget.attrs['step'] = step
            self.fields['cantidad_entrega'].widget.attrs['min'] = step
            self.fields['cantidad_entrega'].decimal_places = precision
        # Configurar step/min para cantidad_recibir
        if moneda_destino:
            precision = moneda_destino.lugares_decimales or 2
            step = self._obtener_step_segun_precision(precision)
            self.fields['cantidad_recibir'].widget.attrs['step'] = step
            self.fields['cantidad_recibir'].widget.attrs['min'] = step
            self.fields['cantidad_recibir'].decimal_places = precision

    def _obtener_step_segun_precision(self, precision):
        if precision <= 0:
            return '1'
        return '0.' + '0' * (precision - 1) + '1'
    
    def clean(self):
        """
        Valida que las monedas de origen y destino sean diferentes.

        Returns
        -------
        dict
            Los datos limpios del formulario listos para usar.

        Raises
        ------
        forms.ValidationError
            Si el usuario elige la misma moneda en origen y destino.
        """
        datos_limpios = super().clean()
        moneda_origen = datos_limpios.get('moneda_origen')
        moneda_destino = datos_limpios.get('moneda_destino')
        
        if moneda_origen == moneda_destino:
            raise forms.ValidationError('Las monedas de origen y destino deben ser diferentes.')
        
        return datos_limpios


class FormularioActualizacionPrecioBase(forms.ModelForm):
    """
    Formulario para actualizaciones manuales de tasas de cambio
    Permite a los usuarios administradores editar el precio base de las monedas.

    Attributes
    ----------
    precio_base : Decimal
        Precio base de la moneda.
    Notes
    -----
    - Solo se usa para actualizar el precio base, no otras propiedades como las
      tasas específicas de compra y venta. Esas son actualizadas automaticamente
      por el sistema.
    - La lógica de actualización de tasas relacionadas a el precio base se maneja
      en signals.
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
        """
        Valida que el valor ingresado para el precio base sea positivo.

        Returns
        -------
        dict
            Los datos limpios del formulario.

        Raises
        ------
        forms.ValidationError
            Si el precio base es nulo o menor o igual a cero.
        """
        datos_limpios = super().clean()
        precio_base = datos_limpios.get('precio_base')

        if precio_base is None or precio_base <= 0:
            raise forms.ValidationError(
                'El precio base debe ser un número positivo.'
            )

        return datos_limpios


class FormularioAlerta(forms.ModelForm):
    """
    Formulario para crear alertas de variacion en precio de tasas de cambio.

    Permite a los usuarios definir condiciones para recibir notificaciones
    cuando una moneda llegue a cierto valor o experimente variaciones porcentuales
    relevantes.

    Attributes
    ----------
    moneda : Moneda
        La moneda para la cual se crea la alerta.
    tipo_alerta : ChoiceField
        Tipo de alerta (ej. tasa objetivo, aumento, disminución).
    tasa_objetivo : Decimal
        Valor exacto de la tasa a monitorear (solo requerido en alertas tipo ``RATE_TARGET``).
    cambio_porcentual : Decimal
        Porcentaje de variación esperado (requerido en alertas tipo 
        ``RATE_INCREASE``, ``RATE_DECREASE`` o ``VOLATILITY``).
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
        """
        Inicializa el formulario filtrando las monedas activas y
        marcando como opcionales los campos numericos.
        """
        super().__init__(*args, **kwargs)
        self.fields['moneda'].queryset = Moneda.objects.filter(esta_activa=True).order_by('codigo')
        self.fields['tasa_objetivo'].required = False
        self.fields['cambio_porcentual'].required = False
    
    def clean(self):
        """
        Valida que los campos obligatorios estén completos según el tipo de alerta.

        Returns
        -------
        dict
            Los datos limpios del formulario.

        Raises
        ------
        forms.ValidationError
            - Si se elige ``RATE_TARGET`` y no se especifica `tasa_objetivo`.
            - Si se elige ``RATE_INCREASE``, ``RATE_DECREASE`` o ``VOLATILITY`` 
              y no se especifica `cambio_porcentual`.
        """
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
    Maneja validaciones de precision decimal y normaliza inputs para que los valores
    numéricos respeten lo que definimos como precision de la moneda.

    Attributes
    ----------
    codigo : str
        Código de la moneda (ej. USD, EUR, PYG).
    nombre : str
        Nombre completo de la moneda (ej. Dólar Americano, Euro).
    simbolo : str
        Símbolo de la moneda (ej. $, €, ₲).
    pais : str
        País de origen de la moneda.
    esta_activa : bool
        Indica si la moneda está activa.
    precio_base_inicial : Decimal
        Precio base inicial de la moneda.
    denominacion_minima : Decimal
        Denominación mínima de la moneda.
    stock_inicial : Decimal
        Stock inicial de la moneda.
    lugares_decimales : int
        Cantidad de lugares decimales para la moneda.
    disponible_para_compra : bool
        Indica si la moneda está disponible para compra.
    disponible_para_venta : bool
        Indica si la moneda está disponible para venta.
    
    Notes
    -----
    - `denominacion_minima` y `stock_inicial` se tratan como enteros

    """
    class Meta:
        model = Moneda
        fields = ['codigo', 'nombre', 'simbolo', 'pais', 'esta_activa', 
                 'precio_base_inicial', 'denominacion_minima', 'stock_inicial', 
                 'lugares_decimales', 'comision_compra', 'comision_venta',
                 'disponible_para_compra', 'disponible_para_venta']
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
            'comision_compra': forms.NumberInput(attrs={
                'class': 'form-control parametro-moneda',
                'placeholder': 'Comisión para compra'
                # step y min se configuran dinámicamente en __init__
            }),
            'comision_venta': forms.NumberInput(attrs={
                'class': 'form-control parametro-moneda',
                'placeholder': 'Comisión para venta'
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
            'comision_compra': 'Comisión para Compra',
            'comision_venta': 'Comisión para Venta',
            'lugares_decimales': 'Precisión Decimal',
            'disponible_para_compra': 'Disponible para Compra',
            'disponible_para_venta': 'Disponible para Venta'
        }
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y ajusta `step` y `min` según la precisión decimal.

        Notes
        -----
        - Si es edición, usa `lugares_decimales` de la instancia; si no, usa 2.
        - Fuerza `denominacion_minima` y `stock_inicial` a comportarse como enteros.
        - Formatea los valores iniciales para que coincidan con la precisión.

        """
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
        
        # precio_base_inicial, comision_compra y comision_venta usan la precisión definida por lugares_decimales
        campos_con_precision = ['precio_base_inicial', 'comision_compra', 'comision_venta']
        for nombre_campo in campos_con_precision:
            if nombre_campo in self.fields:
                campo = self.fields[nombre_campo]
                step = self._obtener_step_segun_precision(precision)
                campo.widget.attrs['step'] = step
                
                # Ajustar el min para que sea compatible con el step
                if precision <= 0:
                    campo.widget.attrs['min'] = '0'
                else:
                    campo.widget.attrs['min'] = '0'
                
                # Si estamos editando, formatear el valor actual
                if self.instance and self.instance.pk:
                    valor_actual = getattr(self.instance, nombre_campo, None)
                    if valor_actual is not None:
                        valor_formateado = self._formatear_valor_con_precision(valor_actual, precision)
                        self.initial[nombre_campo] = valor_formateado
        
        # Agregar clase CSS para identificar campos de parámetros
        for nombre_campo in ['precio_base_inicial', 'denominacion_minima', 'stock_inicial', 'comision_compra', 'comision_venta']:
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
        """
        Devuelve el `step` apropiado para un campo numérico según la precisión.

        Parameters
        ----------
        precision : int
            Cantidad de decimales que se permiten.

        Returns
        -------
        str
            Cadena compatible con atributo HTML `step` (ej.: `'0.01'`, `'1'`).

        Notes
        -----
        - Para `precision <= 0`, el step es `'1'` (solo enteros).
        """
        if precision <= 0:
            return '1'
        # Crear step como 0.0...01 con precision decimales
        return '0.' + '0' * (precision - 1) + '1'
    
    def _formatear_valor_con_precision(self, valor, precision):
        """
        Formatea un valor decimal con la precisión indicada.

        Parameters
        ----------
        valor : Decimal or float or str
            Valor a formatear.
        precision : int
            Cantidad de decimales.

        Returns
        -------
        str or None
            Valor formateado con `precision` decimales, o `None` si `valor` es `None`.

        """
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
        """
        Normaliza el código de moneda a mayúsculas.

        Returns
        -------
        str
            Código en mayúsculas (ej.: `USD`, `EUR`).
        """
        codigo = self.cleaned_data['codigo'].upper()
        return codigo
    
    def clean(self):
        """
        Valida consistencia de decimales y restricciones de enteros.

        Reglas
        ------
        - `denominacion_minima` y `stock_inicial` no aceptan decimales.
        - `precio_base_inicial` no puede superar la cantidad de decimales definida
          en `lugares_decimales`.

        Returns
        -------
        dict
            Datos limpios del formulario.

        Raises
        ------
        forms.ValidationError
            Agregada a campo específico cuando corresponde (vía `add_error`).
        """
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
        
        # Validar precio_base_inicial, comision_compra y comision_venta con la precisión definida
        campos_con_precision = ['precio_base_inicial', 'comision_compra', 'comision_venta']
        for nombre_campo in campos_con_precision:
            if nombre_campo in datos_limpios:
                valor = datos_limpios.get(nombre_campo)
                if valor is not None:
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