from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, get_user_model
from .models import Usuario, Rol, Permiso


class FormularioLogin(forms.Form):
    """
    Formulario de inicio de sesión de usuario.
    Soporta inicio de sesión con nombre de usuario o email.
    """
    identificador = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Usuario o Email',
            'autocomplete': 'username'
        }),
        label='Usuario o Email'
    )
    
    contrasena = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña',
            'autocomplete': 'current-password'
        }),
        label='Contraseña'
    )
    
    def clean(self):
        datos_limpios = super().clean()
        identificador = datos_limpios.get('identificador')
        contrasena = datos_limpios.get('contrasena')
        
        if identificador and contrasena:
            # Intenta encontrar el usuario por nombre de usuario o email
            try:
                if '@' in identificador:
                    # Si se proporcionó un email, buscar por email
                    usuario = Usuario.objects.get(email=identificador)
                    # Usar el email para la autenticación
                    datos_limpios['username'] = usuario.email
                else:
                    # Si se proporcionó un nombre de usuario, buscar por él
                    usuario = Usuario.objects.get(username=identificador)
                    # Usar el email para la autenticación
                    datos_limpios['username'] = usuario.email
                
            except Usuario.DoesNotExist:
                raise forms.ValidationError('Usuario no encontrado.')
        
        return datos_limpios


class FormularioRegistro(UserCreationForm):
    """
    Formulario de registro de usuario.
    """
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre completo'
        }),
        label='Nombre Completo'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@ejemplo.com'
        }),
        label='Dirección de Email'
    )
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario'
        }),
        label='Nombre de Usuario'
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        }),
        label='Contraseña'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        }),
        label='Confirmar Contraseña'
    )
    
    terms_accepted = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Acepto los términos y condiciones',
        required=True
    )
    
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'full_name', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe un usuario con este email.')
        return email
    
    def clean_username(self):
        nombre_usuario = self.cleaned_data['username']
        if Usuario.objects.filter(username=nombre_usuario).exists():
            raise forms.ValidationError('Ya existe un usuario con este nombre de usuario.')
        return nombre_usuario
    
    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.email = self.cleaned_data['email']
        usuario.nombre_completo = self.cleaned_data['full_name']
        
        if commit:
            usuario.save()
        return usuario


class FormularioPerfil(forms.ModelForm):
    """
    Formulario para editar el perfil de usuario.
    """
    class Meta:
        model = Usuario
        fields = ['nombre_completo', 'nro_telefono']  # Solo permitir editar campos no críticos
        widgets = {
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo'
            }),
            'nro_telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono'
            })
        }
        labels = {
            'nombre_completo': 'Nombre Completo',
            'nro_telefono': 'Número de Teléfono'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer que el nombre completo sea requerido
        self.fields['nombre_completo'].required = True
        self.fields['nro_telefono'].required = False


class FormularioCambioContrasena(forms.Form):
    """
    Formulario para cambio de contraseña para usuarios autenticados.
    """
    contrasena_actual = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña actual'
        }),
        label='Contraseña Actual'
    )
    
    nueva_contrasena1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña'
        }),
        label='Nueva Contraseña'
    )
    
    nueva_contrasena2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar nueva contraseña'
        }),
        label='Confirmar Nueva Contraseña'
    )
    
    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)
    
    def clean_contrasena_actual(self):
        contrasena_actual = self.cleaned_data['contrasena_actual']
        if not self.usuario.check_password(contrasena_actual):
            raise forms.ValidationError('La contraseña actual es incorrecta.')
        return contrasena_actual
    
    def clean(self):
        datos_limpios = super().clean()
        nueva_contrasena1 = datos_limpios.get('nueva_contrasena1')
        nueva_contrasena2 = datos_limpios.get('nueva_contrasena2')
        
        if nueva_contrasena1 and nueva_contrasena2:
            if nueva_contrasena1 != nueva_contrasena2:
                raise forms.ValidationError('Las nuevas contraseñas no coinciden.')
        
        return datos_limpios
    
    def save(self):
        nueva_contrasena = self.cleaned_data['nueva_contrasena1']
        self.usuario.set_password(nueva_contrasena)
        self.usuario.save()
        return self.usuario


class FormularioSolicitudRestablecimientoContrasena(forms.Form):
    """
    Formulario de solicitud de restablecimiento de contraseña.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Su dirección de email'
        }),
        label='Dirección de Email'
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            usuario = Usuario.objects.get(email=email)
            return email
        except Usuario.DoesNotExist:
            raise forms.ValidationError('No existe un usuario con este email.')


class FormularioRestablecimientoContrasena(forms.Form):
    """
    Formulario para restablecer la contraseña con un token.
    """
    nueva_contrasena1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña'
        }),
        label='Nueva Contraseña'
    )
    
    nueva_contrasena2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar nueva contraseña'
        }),
        label='Confirmar Nueva Contraseña'
    )
    
    def clean(self):
        datos_limpios = super().clean()
        nueva_contrasena1 = datos_limpios.get('nueva_contrasena1')
        nueva_contrasena2 = datos_limpios.get('nueva_contrasena2')
        
        if nueva_contrasena1 and nueva_contrasena2:
            if nueva_contrasena1 != nueva_contrasena2:
                raise forms.ValidationError('Las contraseñas no coinciden.')
        
        return datos_limpios


class FormularioRol(forms.ModelForm):
    """
    Formulario para crear y editar roles.
    """
    permisos = forms.ModelMultipleChoiceField(
        queryset=Permiso.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label='Permisos'
    )
    
    class Meta:
        model = Rol
        fields = ['nombre_rol', 'descripcion', 'permisos']
        widgets = {
            'nombre_rol': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del rol'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del rol',
                'rows': 3
            }),
        }
        labels = {
            'nombre_rol': 'Nombre del Rol',
            'descripcion': 'Descripción'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Organizar permisos por categorías para mejor presentación
        self.fields['permisos'].queryset = Permiso.objects.all().order_by('descripcion')


class FormularioAsignarRoles(forms.Form):
    """
    Formulario para asignar roles a un usuario.
    """
    roles = forms.ModelMultipleChoiceField(
        queryset=Rol.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label='Roles'
    )
    
    def __init__(self, usuario=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields['roles'].queryset = Rol.objects.all().order_by('nombre_rol')
        
        # Si hay un usuario, preseleccionar sus roles actuales
        if usuario:
            self.fields['roles'].initial = usuario.roles.all()
    
    def save(self):
        """Guarda los roles asignados al usuario."""
        if self.usuario:
            roles_seleccionados = self.cleaned_data['roles']
            self.usuario.roles.set(roles_seleccionados)
            return self.usuario


class FormularioSolicitudDesbloqueoCuenta(forms.Form):
    email = forms.EmailField(
        label="Correo electrónico asociado",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo electrónico',
            'required': True
        })
    )

class FormularioVerificacionCodigoDesbloqueo(forms.Form):
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Correo electrónico',
            'required': True
        })
    )
    codigo = forms.CharField(
        label="Código de verificación",
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el código recibido',
            'required': True
        })
    )




class EditarUsuarioForm(forms.ModelForm):
    Usuario = get_user_model()
    class Meta:
        model = Usuario
        fields = ['nombre_completo', 'email']
        labels = {
            'nombre_completo': 'Nombre Completo',
            'email': 'Correo Electrónico',
        }
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }