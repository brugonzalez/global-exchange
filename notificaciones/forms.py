from django import forms
from django.core.validators import EmailValidator
from .models import TicketSoporte, MensajeTicket, PreferenciaNotificacion


class FormularioTicketSoporte(forms.ModelForm):
    """
    Formulario para crear tickets de soporte.
    """
    class Meta:
        model = TicketSoporte
        fields = ['nombre_usuario', 'email_usuario', 'asunto', 'descripcion', 'categoria', 'prioridad']
        widgets = {
            'nombre_usuario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Su nombre completo'
            }),
            'email_usuario': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'su.email@ejemplo.com'
            }),
            'asunto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Resumen del problema o consulta'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describa detalladamente su problema o consulta...'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),
            'prioridad': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-rellenar datos del usuario si está autenticado
        if usuario and usuario.is_authenticated:
            self.fields['nombre_usuario'].initial = usuario.nombre_completo
            self.fields['email_usuario'].initial = usuario.email
            
            # Hacer los campos de solo lectura para usuarios autenticados
            self.fields['nombre_usuario'].widget.attrs['readonly'] = True
            self.fields['email_usuario'].widget.attrs['readonly'] = True
        
        # Establecer textos de ayuda
        self.fields['categoria'].help_text = "Seleccione la categoría que mejor describe su consulta"
        self.fields['prioridad'].help_text = "Seleccione la urgencia de su consulta"
        self.fields['descripcion'].help_text = "Incluya toda la información relevante para que podamos ayudarle mejor"

    def clean_email_usuario(self):
        email = self.cleaned_data.get('email_usuario')
        if email:
            validator = EmailValidator()
            validator(email)
        return email

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion')
        if descripcion and len(descripcion.strip()) < 10:
            raise forms.ValidationError(
                'La descripción debe tener al menos 10 caracteres.'
            )
        return descripcion


class FormularioRespuestaTicket(forms.ModelForm):
    """
    Formulario para responder a tickets de soporte.
    """
    class Meta:
        model = MensajeTicket
        fields = ['mensaje']
        widgets = {
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escriba su respuesta aquí...'
            })
        }

    def clean_mensaje(self):
        mensaje = self.cleaned_data.get('mensaje')
        if mensaje and len(mensaje.strip()) < 5:
            raise forms.ValidationError(
                'El mensaje debe tener al menos 5 caracteres.'
            )
        return mensaje


class FormularioPreferenciasNotificacion(forms.ModelForm):
    """
    Formulario para gestionar las preferencias de notificación.
    """
    class Meta:
        model = PreferenciaNotificacion
        fields = [
            'email_actualizaciones_transaccion',
            'email_alertas_tasa'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Añadir clases de Bootstrap a los checkboxes
        for nombre_campo in ['email_actualizaciones_transaccion', 'email_alertas_tasa']:
            self.fields[nombre_campo].widget.attrs.update({
                'class': 'form-check-input'
            })
        
        # Añadir etiquetas y textos de ayuda
        self.fields['email_actualizaciones_transaccion'].label = "Actualizaciones de Transacciones"
        self.fields['email_actualizaciones_transaccion'].help_text = "Recibir notificaciones cuando cambien los estados de las transacciones"
        
        self.fields['email_alertas_tasa'].label = "Alertas de Tasas de Cambio"
        self.fields['email_alertas_tasa'].help_text = "Recibir notificaciones cuando las tasas de cambio se actualicen manualmente"


class FormularioSoporteRapido(forms.Form):
    """
    Formulario de soporte rápido para problemas comunes.
    """
    TIPOS_PROBLEMA = [
        ('login', 'Problemas para iniciar sesión'),
        ('transaction', 'Problemas con transacciones'),
        ('verification', 'Problemas de verificación de cuenta'),
        ('2fa', 'Problemas con autenticación de dos factores'),
        ('rates', 'Consultas sobre tasas de cambio'),
        ('reports', 'Problemas con reportes'),
        ('other', 'Otro problema'),
    ]
    
    tipo_problema = forms.ChoiceField(
        choices=TIPOS_PROBLEMA,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Tipo de problema"
    )
    
    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describa brevemente su problema...'
        }),
        label="Descripción",
        max_length=500
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'su.email@ejemplo.com'
        }),
        label="Email de contacto"
    )

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion')
        if descripcion and len(descripcion.strip()) < 10:
            raise forms.ValidationError(
                'La descripción debe tener al menos 10 caracteres.'
            )
        return descripcion


class FormularioBusquedaNotificacion(forms.Form):
    """
    Formulario para buscar notificaciones.
    """
    TIPOS_NOTIFICACION = [
        ('', 'Todos los tipos'),
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('PUSH', 'Push'),
        ('IN_APP', 'En la aplicación'),
    ]
    
    ESTADOS = [
        ('', 'Todos los estados'),
        ('PENDIENTE', 'Pendiente'),
        ('ENVIADO', 'Enviado'),
        ('ENTREGADO', 'Entregado'),
        ('FALLIDO', 'Fallido'),
        ('LEIDO', 'Leído'),
    ]
    
    termino_busqueda = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar en asunto o mensaje...'
        }),
        label="Buscar"
    )
    
    tipo_notificacion = forms.ChoiceField(
        choices=TIPOS_NOTIFICACION,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Tipo"
    )
    
    estado = forms.ChoiceField(
        choices=ESTADOS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Estado"
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Desde"
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Hasta"
    )