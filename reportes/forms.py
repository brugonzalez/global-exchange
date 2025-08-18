from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Reporte


class FormularioGeneracionReporte(forms.ModelForm):
    """
    Formulario para generar reportes.
    """
    class Meta:
        model = Reporte
        fields = [
            'nombre_reporte', 'tipo_reporte', 'formato', 
            'fecha_desde', 'fecha_hasta', 'cliente'
        ]
        widgets = {
            'nombre_reporte': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del reporte'
            }),
            'tipo_reporte': forms.Select(attrs={
                'class': 'form-control'
            }),
            'formato': forms.Select(attrs={
                'class': 'form-control'
            }),
            'fecha_desde': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'fecha_hasta': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'cliente': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Establecer fechas por defecto (últimos 30 días)
        ahora = timezone.now()
        self.fields['fecha_hasta'].initial = ahora
        self.fields['fecha_desde'].initial = ahora - timedelta(days=30)
        
        # Filtrar clientes para el usuario actual
        if usuario:
            self.fields['cliente'].queryset = usuario.obtener_clientes_disponibles()
        
        # Hacer el campo de cliente opcional
        self.fields['cliente'].required = False
        self.fields['cliente'].empty_label = "Todos los clientes"

    def clean(self):
        datos_limpios = super().clean()
        fecha_desde = datos_limpios.get('fecha_desde')
        fecha_hasta = datos_limpios.get('fecha_hasta')
        
        if fecha_desde and fecha_hasta:
            if fecha_desde >= fecha_hasta:
                raise forms.ValidationError(
                    'La fecha de inicio debe ser anterior a la fecha de fin.'
                )
            
            # Comprobar que el rango de fechas no sea demasiado grande
            if (fecha_hasta - fecha_desde).days > 365:
                raise forms.ValidationError(
                    'El rango de fechas no puede ser mayor a 365 días.'
                )
        
        return datos_limpios


class FormularioRangoFechas(forms.Form):
    """
    Formulario simple para selección de rango de fechas.
    """
    fecha_desde = forms.DateTimeField(
        label='Fecha desde',
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    fecha_hasta = forms.DateTimeField(
        label='Fecha hasta',
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Establecer fechas por defecto (últimos 7 días)
        ahora = timezone.now()
        self.fields['fecha_hasta'].initial = ahora
        self.fields['fecha_desde'].initial = ahora - timedelta(days=7)

    def clean(self):
        datos_limpios = super().clean()
        fecha_desde = datos_limpios.get('fecha_desde')
        fecha_hasta = datos_limpios.get('fecha_hasta')
        
        if fecha_desde and fecha_hasta:
            if fecha_desde >= fecha_hasta:
                raise forms.ValidationError(
                    'La fecha de inicio debe ser anterior a la fecha de fin.'
                )
        
        return datos_limpios


class FormularioFiltroReporte(forms.Form):
    """
    Formulario para filtrar reportes en análisis.
    """
    OPCIONES_PERIODO = [
        ('hoy', 'Hoy'),
        ('semana', 'Última semana'),
        ('mes', 'Último mes'),
        ('trimestre', 'Último trimestre'),
        ('ano', 'Último año'),
        ('personalizado', 'Personalizado'),
    ]
    
    periodo = forms.ChoiceField(
        choices=OPCIONES_PERIODO,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='mes'
    )
    
    moneda = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Todas las monedas",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Importar aquí para evitar importaciones circulares
        from divisas.models import Moneda
        self.fields['moneda'].queryset = Moneda.objects.filter(esta_activa=True)