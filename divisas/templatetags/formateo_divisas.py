from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def formatear_decimal_con_precision(valor, precision):
    """
    Formatea un valor decimal con la precisión especificada.
    
    Uso: {{ valor|formatear_decimal_con_precision:precision }}
    
    Ejemplos:
    - {{ 0.00000001|formatear_decimal_con_precision:2 }} -> "0.00"
    - {{ 0.01|formatear_decimal_con_precision:8 }} -> "0.01000000"
    """
    if valor is None or valor == '':
        return ''
    
    try:
        # Convertir a número
        if isinstance(valor, Decimal):
            numero = float(valor)
        else:
            numero = float(valor)
        
        # Aplicar precisión
        precision_int = int(precision) if precision is not None else 2
        if precision_int < 0:
            precision_int = 0
        elif precision_int > 8:
            precision_int = 8
            
        # Formatear con la precisión especificada
        return f"{numero:.{precision_int}f}"
        
    except (ValueError, TypeError, OverflowError):
        return str(valor)

@register.filter  
def obtener_step_precision(precision):
    """
    Obtiene el valor de step apropiado para un campo según la precisión decimal.
    
    Uso: {{ precision|obtener_step_precision }}
    
    Ejemplos:
    - {{ 2|obtener_step_precision }} -> "0.01"
    - {{ 8|obtener_step_precision }} -> "0.00000001"
    """
    try:
        precision_int = int(precision) if precision is not None else 2
        if precision_int <= 0:
            return '1'
        # Crear step como 0.0...01 con precision decimales
        return '0.' + '0' * (precision_int - 1) + '1'
    except (ValueError, TypeError):
        return '0.01'

@register.simple_tag
def formatear_parametros_moneda(moneda):
    """
    Tag para obtener los valores de parámetros de moneda formateados según su precisión.
    
    Uso: {% formatear_parametros_moneda moneda as parametros %}
    """
    if not moneda:
        return {}
    
    precision = getattr(moneda, 'lugares_decimales', 2)
    
    return {
        'precio_base_inicial': formatear_decimal_con_precision(moneda.precio_base_inicial, precision),
        'denominacion_minima': formatear_decimal_con_precision(moneda.denominacion_minima, precision), 
        'stock_inicial': formatear_decimal_con_precision(moneda.stock_inicial, precision),
        'precision': precision,
        'step': obtener_step_precision(precision)
    }