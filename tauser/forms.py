from django import forms

class FormDeposito(forms.Form):
    monto = forms.DecimalField(label='Monto a depositar', min_value=0.01)
    moneda = forms.ChoiceField(label='Moneda')  # Llénalo dinámicamente desde las monedas disponibles

class FormExtraccion(forms.Form):
    monto = forms.DecimalField(label='Monto a extraer', min_value=0.01)
    moneda = forms.ChoiceField(label='Moneda')  # Llénalo dinámicamente desde las monedas disponibles