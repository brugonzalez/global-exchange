from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, get_user_model
from .models import Usuario, Rol, Permiso, Configuracion


class FormularioLogin(forms.Form):
    """
    Formulario de inicio de sesión de usuario.
    Permite inicio de sesión con nombre de usuario o email.
    Internamente, siempre normaliza el identificador al email.

    Attributes
    ----------
    identificador : CharField
        Campo de texto donde el usuario ingresa su username o email
    contrasena : CharField
        Campo de contraseña del usuario

    Notes
    -----
    - Si el identificador contiene un '@', se asume que es un email, caso contrario busca por nombre de usuario.
    - En todos los casos, el valor final en ``datos_limpios['username']`` será el email del usuario.
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
        """Valida los datos del formulario de autenticación: identificador y contraseña.

        Notes
        ------
        - Toma el valor ingresado en el campo 'identificador' y lo busca en la base de datos.
        - También toma la contraseña y la valida.
        - Si encuentra el usuario, siempre pone el email en datos_limpios['username'].
        - Si no encuentra el usuario, lanza un ``ValidationError``.
        
        Returns
        -------
        dict
            Datos limpios del formulario, con ``username`` siempre normalizada al email del usuario

        Raises
        -------
        forms.ValidationError
            Si el usuario no es encontrado o la contraseña es incorrecta.
        """
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
    Formulario para crear una cuenta de usuario.

    Attributes
    --------------
    full_name : CharField
        Nombre completo del usuario.
    email : EmailField
        Dirección de email del usuario.
    username : CharField
        Nombre de usuario del usuario.
    password1 : CharField       
        Contraseña del usuario.
    password2 : CharField
        Confirmación de la contraseña.
    terms_accepted : BooleanField
        Aceptación de los términos y condiciones.

    Validaciones
    ----------------
    - Hereda validaciones de UserCreationForm (coincidencia de contraseña)
    - Valida que no haya un usuario existente con el mismo email o nombre de usuario.
    - Valida que los términos y condiciones hayan sido aceptados.
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
        """
        Valida que el email ingresado no esté ya en uso por otro usuario.

        Returns
        -------
        str
            El email limpio y validado.

        Raises
        -------
        ValidationError
            Si el email ya está en uso.
        """
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe un usuario con este email.')
        return email
    
    def clean_username(self):
        """
        Valida que el nombre de usuario ingresado no esté ya en uso por otro usuario.

        Returns
        -------
        str
            El nombre de usuario limpio y validado.

        Raises
        -------
        ValidationError
            Si el nombre de usuario ya está en uso.
        """
        nombre_usuario = self.cleaned_data['username']
        if Usuario.objects.filter(username=nombre_usuario).exists():
            raise forms.ValidationError('Ya existe un usuario con este nombre de usuario.')
        return nombre_usuario
    
    def save(self, commit=True):
        """
        Guarda el usuario en la base de datos.

        Parameters
        ----------
        commit : bool
            Si se debe guardar el usuario en la base de datos.

        Returns
        -------
        Usuario
            El usuario creado o actualizado.
        """
        usuario = super().save(commit=False)
        usuario.email = self.cleaned_data['email']
        usuario.nombre_completo = self.cleaned_data['full_name']
        
        if commit:
            usuario.save()
        return usuario

    def clean_password1(self):
        """
        Valida que la contraseña ingresada cumpla con los requisitos.

        Returns
        -------
        str 
            La contraseña limpia y validada.

        Raises
        ------
        forms.ValidationError
            Si la contraseña no cumple con los requisitos.
        """
        password = self.cleaned_data.get("password1")
        if password and len(password) < 3:
            raise forms.ValidationError("La contraseña debe tener al menos 3 caracteres.")
        return password


class FormularioPerfil(forms.ModelForm):
    """
    Formulario para editar el perfil de usuario.
    Permite actualizar información personal (nombre completo y número de teléfono).

    Validaciones
    -------------
        - Verifica que el nombre completo no esté vacío.
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

    Permite a los usuarios cambiar su contraseña actual por una nueva.
    Pide la contraseña actual, una nueva y su confirmacion.

    Attributes
    ----------
    contrasena_actual : CharField
        Campo de contraseña para validar la contraseña actual del usuario.
    nueva_contrasena1 : CharField
        Campo para ingresar la nueva contraseña.
    nueva_contrasena2 : CharField
        Campo para confirmar la nueva contraseña.

    Notes
    ------
        - Verifica que la contraseña actual sea correcta.
        - Verifica que las nuevas contraseñas coincidan.
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
        """
        Inicializa el formulario con el usuario actual.

        Parameters
        ----------
        usuario : Usuario
            El usuario actual que está cambiando su contraseña.
        """
        self.usuario = usuario
        super().__init__(*args, **kwargs)
    
    def clean_contrasena_actual(self):
        """
        Verifica que la contraseña actual sea correcta

        Returns
        ---------
        str
            Contraseña actual validada

        Raises
        -------
        ValidationError
            Si la contraseña actual es incorrecta.
        """
        contrasena_actual = self.cleaned_data['contrasena_actual']
        if not self.usuario.check_password(contrasena_actual):
            raise forms.ValidationError('La contraseña actual es incorrecta.')
        return contrasena_actual
    
    def clean(self):
        """
        Verifica que las nuevas contraseñas coincidan.

        Returns
        -------
        dict
            Datos limpios del formulario.

        Raises
        -------
        ValidationError
            Si las nuevas contraseñas no coinciden.
        """
        datos_limpios = super().clean()
        nueva_contrasena1 = datos_limpios.get('nueva_contrasena1')
        nueva_contrasena2 = datos_limpios.get('nueva_contrasena2')
        
        if nueva_contrasena1 and nueva_contrasena2:
            if nueva_contrasena1 != nueva_contrasena2:
                raise forms.ValidationError('Las nuevas contraseñas no coinciden.')
        
        return datos_limpios
    
    def save(self):
        """
        Guarda la nueva contraseña del usuario.

        Returns
        -------
        Usuario
            El usuario actualizado.
        """
        nueva_contrasena = self.cleaned_data['nueva_contrasena1']
        self.usuario.set_password(nueva_contrasena)
        self.usuario.save()
        return self.usuario


class FormularioSolicitudRestablecimientoContrasena(forms.Form):
    """
    Formulario de solicitud de restablecimiento de contraseña.

    Permite al usuario solicitar un restablecimiento de contraseña indicando su dirección de email.

    Attributes
    ----------
    email : EmailField
        Dirección de email del usuario.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Su dirección de email'
        }),
        label='Dirección de Email'
    )
    
    def clean_email(self):
        """
        Verifica que el email ingresado pertenezca a un usuario registrado.

        Returns
        -------
        str
            El email validado.

        Raises
        -------
        ValidationError
            Si el email no pertenece a un usuario registrado.
        """
        email = self.cleaned_data['email']
        try:
            usuario = Usuario.objects.get(email=email)
            return email
        except Usuario.DoesNotExist:
            raise forms.ValidationError('No existe un usuario con este email.')


class FormularioRestablecimientoContrasena(forms.Form):
    """
    Formulario para restablecer la contraseña con un token.
    Permite a los usuarios establecer una nueva contraseña después de solicitar un restablecimiento.

    Attributes
    ----------
    nueva_contrasena1 : CharField
        Nueva contraseña del usuario.
    nueva_contrasena2 : CharField
        Confirmación de la nueva contraseña.

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
        """
        Verifica que las nuevas contraseñas coincidan.

        Returns
        -------
        dict
            Datos limpios del formulario.

        Raises
        -------
        ValidationError
            Si las nuevas contraseñas no coinciden.
        """
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

    Permite definir un rol con su nombre, descripción y los permisos
    que tendrá asignados. Los permisos se presentan como una lista de
    checkboxes para facilitar la selección múltiple.

    Attributes
    ----------
    permisos : ModelMultipleChoiceField[:class:`Permiso`]
        Permisos asociados al rol renderizados como checkboxs.
    nombre_rol : CharField
        Nombre del rol.
    descripcion : CharField
        Descripción del rol.
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
        """
        Inicializa el formulario con los permisos disponibles.

        Notes
        -----
        Los permisos se ordenan alfabeticamente por su descripcion.
        """
        super().__init__(*args, **kwargs)
        # Organizar permisos por categorías para mejor presentación
        self.fields['permisos'].queryset = Permiso.objects.all().order_by('descripcion')


class FormularioAsignarRoles(forms.Form):
    """
    Formulario para asignar roles a un usuario.

    Permite seleccionar uno o varios roles de la lista disponible y
    asignarlos a un usuario específico.

    Attributes
    ----------
    roles : ModelMultipleChoiceField[:class:`Rol`]
        Roles disponibles para asignar al usuario.
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
        """
        Inicializa el formulario de asignación de roles para un usuario específico.

        Si se pasa un usuario, se muestran sus roles actuales como seleccionados
        por defecto.

        Parameters
        ----------
        usuario : Usuario, optional
            El usuario al que se le asignarán los roles.
        """
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields['roles'].queryset = Rol.objects.all().order_by('nombre_rol')
        
        # Si hay un usuario, preseleccionar sus roles actuales
        if usuario:
            self.fields['roles'].initial = usuario.roles.all()
    
    def save(self):
        """
        Guarda los roles asignados al usuario.

        Returns
        -------
        Usuario
            El usuario actualizado.
        """
        if self.usuario:
            roles_seleccionados = self.cleaned_data['roles']
            self.usuario.roles.set(roles_seleccionados)
            return self.usuario


class FormularioSolicitudDesbloqueoCuenta(forms.Form):
    """
    Formulario para solicitar el desbloqueo de una cuenta.

    El usuario debe ingresar el correo electrónico asociado a la cuenta
    para iniciar el proceso de validación y desbloqueo.

    Attributes
    ----------
    email : EmailField
        Correo electrónico asociado a la cuenta.
    """
    email = forms.EmailField(
        label="Correo electrónico asociado",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo electrónico',
            'required': True
        })
    )

class FormularioVerificacionCodigoDesbloqueo(forms.Form):
    """
    Formulario para verificar el código de desbloqueo de cuenta.
    El usuario ingresa su correo electrónico y el código de verificación recibido
    para desbloquear su cuenta.

    Attributes
    ----------
    email : EmailField
        Correo electrónico asociado a la cuenta.
    codigo : CharField
        Código de verificación enviado al correo electrónico.
    """
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
    """
    Formulario para editar un usuario existente. (desde el panel de administración)

    Permite modificar los datos básicos del usuario.
    Attributes
    ----------
    usuario : Usuario
        El usuario que se va a editar.
    nombre_completo : CharField
        Nombre completo del usuario.
    email : EmailField
        Correo electrónico del usuario.
    """
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

class FormularioRegistroUsuario(UserCreationForm):
    """
    Formulario de registrar un nuevo usuario

    Attributes
    ----------
    full_name : CharField
        Nombre completo del usuario.
    email : EmailField
        Correo electrónico del usuario.
    username : CharField
        Nombre de usuario.
    password1 : CharField
        Contraseña del usuario.
    password2 : CharField
        Confirmación de la contraseña.
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

    rol = forms.ModelChoiceField(
        queryset=Rol.objects.all(),
        required=False,
        label="Rol",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Usuario  # tu modelo de usuario custom
        fields = ["full_name", "email", "username", "password1", "password2", "rol"]


class FormularioConfiguracion(forms.ModelForm):
    """
    Formulario para editar configuraciones del sistema.
    Permite modificar el nombre, valor y descripción de una configuración específica.
    
    """

    class Meta:
        model = Configuracion
        fields = ['nombre', 'valor', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre legible (opcional)'
            }),
            'valor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el valor'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la configuración'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Adaptar el widget según el tipo de valor
        if self.instance and self.instance.pk:
            tipo_valor = self.instance.tipo_valor

            if tipo_valor == 'BOOLEAN':
                self.fields['valor'] = forms.ChoiceField(
                    choices=[('true', 'Verdadero'), ('false', 'Falso')],
                    widget=forms.Select(attrs={'class': 'form-control'})
                )
                self.fields['valor'].initial = 'true' if self.instance.convertir_valor() else 'false'

            elif tipo_valor == 'NUMBER':
                self.fields['valor'].widget = forms.NumberInput(attrs={
                    'class': 'form-control',
                    'step': 'any'
                })

            elif tipo_valor == 'EMAIL':
                self.fields['valor'].widget = forms.EmailInput(attrs={
                    'class': 'form-control'
                })

            elif tipo_valor == 'URL':
                self.fields['valor'].widget = forms.URLInput(attrs={
                    'class': 'form-control'
                })

    def clean_valor(self):
        valor = self.cleaned_data['valor']

        if self.instance and self.instance.pk:
            tipo_valor = self.instance.tipo_valor

            if tipo_valor == 'NUMBER':
                try:
                    float(valor)
                except ValueError:
                    raise forms.ValidationError('Debe ingresar un número válido.')

            elif tipo_valor == 'EMAIL':
                from django.core.validators import validate_email
                from django.core.exceptions import ValidationError as DjangoValidationError
                try:
                    validate_email(valor)
                except DjangoValidationError:
                    raise forms.ValidationError('Debe ingresar un email válido.')

        return valor