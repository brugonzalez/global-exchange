from django import template

register = template.Library()

@register.filter
def filtrar_por_estado(consulta, estado):
    """Filtra un queryset por estado"""
    if hasattr(consulta, 'filter'):
        return consulta.filter(estado=estado)
    else:
        return [item for item in consulta if getattr(item, 'estado', None) == estado]

@register.filter
def obtener_elemento(diccionario, clave):
    """Obtiene un elemento de un diccionario"""
    return diccionario.get(clave)