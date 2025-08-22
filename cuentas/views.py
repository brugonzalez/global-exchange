from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, FormView, View, ListView, UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
import uuid

from clientes.views import MixinStaffRequerido
from .models import Usuario, VerificacionEmail, RestablecimientoContrasena, RegistroAuditoria, Rol, Permiso
from .forms import FormularioLogin, FormularioRegistro, FormularioPerfil, FormularioCambioContrasena, \
    FormularioSolicitudDesbloqueoCuenta, FormularioVerificacionCodigoDesbloqueo, EditarUsuarioForm
from clientes.models import Cliente
from django.utils import timezone



class VistaLogin(FormView):
    """
    Vista de inicio de sesión de usuario
    """
    template_name = 'cuentas/iniciar_sesion.html'
    form_class = FormularioLogin
    success_url = reverse_lazy('divisas:panel_de_control')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formulario'] = context['form']
        return context
    
    def form_valid(self, formulario):
        nombre_usuario = formulario.cleaned_data['username']
        contrasena = formulario.cleaned_data['contrasena']
        
        # Intentar autenticar
        usuario = authenticate(self.request, username=nombre_usuario, password=contrasena)
        
        if usuario is not None:
            if usuario.esta_cuenta_bloqueada():
                messages.error(self.request, 'Su cuenta está bloqueada temporalmente. Intente más tarde.')
                return self.form_invalid(formulario)
            
            if not usuario.email_verificado:
                messages.warning(self.request, 'Debe verificar su email antes de iniciar sesión.')
                return self.form_invalid(formulario)
            
            # Restablecer intentos fallidos en un inicio de sesión exitoso
            usuario.restablecer_intentos_fallidos()
            
            # Comprobar si el usuario tiene 2FA activado
            if usuario.autenticacion_dos_factores_activa:
                # Guardar ID de usuario en la sesión para la verificación 2FA
                self.request.session['id_usuario_pre_2fa'] = usuario.id
                
                # Guardar la URL de redirección
                siguiente_pagina = self.request.GET.get('next', '/divisas/')
                self.request.session['redireccion_login'] = siguiente_pagina
                
                # Redirigir a la verificación 2FA
                messages.info(self.request, 'Por favor ingrese su código iToken para completar el inicio de sesión.')
                return redirect('cuentas:itoken_verificar')
            else:
                # Completar el login sin 2FA
                login(self.request, usuario)
                messages.success(self.request, f'¡Bienvenido, {usuario.nombre_completo}!')
                
                # Redirigir a la página siguiente si se especifica
                siguiente_pagina = self.request.GET.get('next')
                if siguiente_pagina:
                    return redirect(siguiente_pagina)
                
                return super().form_valid(formulario)
        else:
            # Manejar login fallido
            try:
                # Buscar por nombre de usuario
                usuario = Usuario.objects.get(email=nombre_usuario)
                usuario.incrementar_intentos_fallidos()

                if usuario.esta_cuenta_bloqueada():
                    # Pasamos un flag para mostrar el botón de desbloqueo
                    return self.render_to_response(self.get_context_data(
                        formulario=formulario,
                        cuenta_bloqueada=True
                    ))
                
                if usuario.esta_cuenta_bloqueada():
                    messages.error(self.request, 'Su cuenta ha sido bloqueada debido a múltiples intentos fallidos.')
                else:
                    messages.error(self.request, 'Credenciales inválidas.')
            except Usuario.DoesNotExist:
                messages.error(self.request, 'Credenciales inválidas.')
            
            return self.form_invalid(formulario)


class VistaLogout(TemplateView):
    """
    Vista de cierre de sesión de usuario
    """
    def get(self, solicitud, *args, **kwargs):
        logout(solicitud)
        messages.success(solicitud, 'Ha cerrado sesión correctamente.')
        return redirect('divisas:panel_de_control')


class VistaRegistro(FormView):
    """
    Vista de registro de usuario
    """
    template_name = 'cuentas/registro.html'
    form_class = FormularioRegistro
    success_url = reverse_lazy('cuentas:iniciar_sesion')
    
    def form_valid(self, formulario):
        # Crear usuario
        usuario = formulario.save(commit=False)
        usuario.email_verificado = False
        usuario.save()
        
        # Generar token de verificación
        token = str(uuid.uuid4())
        VerificacionEmail.objects.create(
            usuario=usuario,
            token=token
        )
        
        # Enviar email de verificación
        self.enviar_email_verificacion(usuario, token)
        
        messages.success(
            self.request, 
            'Registro exitoso. Por favor, verifique su email para activar su cuenta.'
        )
        return super().form_valid(formulario)
    
    def enviar_email_verificacion(self, usuario, token):
        """Envía el correo de verificación de email"""
        enlace_verificacion = self.request.build_absolute_uri(
            f'/cuentas/verificar-email/{token}/'
        )
        
        asunto = 'Verifique su dirección de email - Global Exchange'
        mensaje = f'''
        Bienvenido a Global Exchange
        
        Para completar su registro, por favor verifique su dirección de email visitando el siguiente enlace:
        {enlace_verificacion}
        
        Este enlace expirará en 24 horas.
        '''
        
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [usuario.email],
            fail_silently=True
        )


class VistaVerificarEmail(TemplateView):
    """
    Vista de verificación de email
    """
    template_name = 'cuentas/verificar_email.html'
    
    def get(self, solicitud, token, *args, **kwargs):
        try:
            verificacion = VerificacionEmail.objects.get(token=token, utilizado=False)
            
            if verificacion.ha_expirado():
                messages.error(solicitud, 'El enlace de verificación ha expirado.')
                return render(solicitud, self.template_name, {'success': False})
            
            # Verificar al usuario
            usuario = verificacion.usuario
            usuario.email_verificado = True
            usuario.save()
            
            # Marcar verificación como utilizada
            verificacion.utilizado = True
            verificacion.save()
            
            messages.success(solicitud, 'Email verificado correctamente. Ya puede iniciar sesión.')
            return render(solicitud, self.template_name, {'success': True})
            
        except VerificacionEmail.DoesNotExist:
            messages.error(solicitud, 'Enlace de verificación inválido.')
            return render(solicitud, self.template_name, {'success': False})


class VistaPerfil(LoginRequiredMixin, TemplateView):
    """
    Vista del perfil de usuario
    """
    template_name = 'cuentas/perfil.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['usuario'] = self.request.user
        contexto['clientes'] = self.request.user.clientes.all()
        return contexto


class VistaEditarPerfil(LoginRequiredMixin, FormView):
    """
    Vista para editar el perfil de usuario
    """
    template_name = 'cuentas/editar_perfil.html'
    form_class = FormularioPerfil
    success_url = reverse_lazy('cuentas:perfil')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs
    
    def form_valid(self, formulario):
        formulario.save()
        messages.success(self.request, 'Perfil actualizado correctamente.')
        return super().form_valid(formulario)


class VistaSeleccionarCliente(LoginRequiredMixin, TemplateView):
    """
    Vista de selección de cliente
    """
    template_name = 'cuentas/seleccionar_cliente.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['clientes'] = self.request.user.clientes.filter(
            clienteusuario__esta_activo=True
        )
        return contexto


class VistaCambiarCliente(LoginRequiredMixin, TemplateView):
    """
    Cambia el cliente activo
    """
    def post(self, solicitud, id_cliente, *args, **kwargs):
        try:
            cliente = get_object_or_404(
                Cliente,
                id=id_cliente,
                usuarios=solicitud.user,
                clienteusuario__esta_activo=True
            )
            
            # Actualizar el cliente seleccionado del usuario
            solicitud.user.ultimo_cliente_seleccionado = cliente
            solicitud.user.save(update_fields=['ultimo_cliente_seleccionado'])
            
            messages.success(solicitud, f'Cliente activo cambiado a: {cliente.obtener_nombre_completo()}')
            
        except Cliente.DoesNotExist:
            messages.error(solicitud, 'Cliente no encontrado o no autorizado.')
        
        return redirect('divisas:panel_de_control')


class VistaDeseleccionarCliente(LoginRequiredMixin, TemplateView):
    """
    Deselecciona el cliente activo
    """
    def post(self, solicitud, *args, **kwargs):
        # Limpiar el cliente seleccionado del usuario
        solicitud.user.ultimo_cliente_seleccionado = None
        solicitud.user.save(update_fields=['ultimo_cliente_seleccionado'])
        
        messages.success(solicitud, 'Cliente deseleccionado. Seleccione un cliente para realizar transacciones.')
        
        return redirect('cuentas:seleccionar_cliente')


# Vistas de Restablecimiento de Contraseña
class VistaSolicitudRestablecimientoContrasena(FormView):
    """
    Vista de solicitud de restablecimiento de contraseña
    """
    template_name = 'cuentas/solicitud_restablecimiento_contrasena.html'
    form_class = 'FormularioSolicitudRestablecimientoContrasena'
    success_url = reverse_lazy('cuentas:iniciar_sesion')
    
    def get_form_class(self):
        from .forms import FormularioSolicitudRestablecimientoContrasena
        return FormularioSolicitudRestablecimientoContrasena
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formulario'] = context['form']
        return context
    
    def form_valid(self, formulario):
        email = formulario.cleaned_data['email']
        
        try:
            usuario = Usuario.objects.get(email=email)
            
            # Generar token de restablecimiento
            token = str(uuid.uuid4())
            
            # Crear o actualizar registro de restablecimiento de contraseña
            RestablecimientoContrasena.objects.filter(usuario=usuario, utilizado=False).delete()  # Limpiar tokens antiguos
            registro_restablecimiento = RestablecimientoContrasena.objects.create(
                usuario=usuario,
                token=token
            )
            
            # Enviar email de restablecimiento
            self.enviar_email_restablecimiento(usuario, token)
            
            messages.success(
                self.request,
                'Se ha enviado un enlace de recuperación a su email. Revise su bandeja de entrada.'
            )
            
        except Usuario.DoesNotExist:
            # No revelar si el email existe o no por seguridad
            messages.success(
                self.request,
                'Si el email existe en nuestro sistema, recibirá un enlace de recuperación.'
            )
        
        return super().form_valid(formulario)
    
    def enviar_email_restablecimiento(self, usuario, token):
        """Envía el email de restablecimiento de contraseña"""
        enlace_restablecimiento = self.request.build_absolute_uri(
            f'/cuentas/contrasena/restablecer/{token}/'
        )
        
        asunto = 'Recuperación de contraseña - Global Exchange'
        mensaje = f'''
        Hola {usuario.nombre_completo},
        
        Ha solicitado restablecer su contraseña en Global Exchange.
        
        Para crear una nueva contraseña, haga clic en el siguiente enlace:
        {enlace_restablecimiento}
        
        Este enlace expirará en 1 hora por motivos de seguridad.
        
        Si no solicitó este cambio, ignore este mensaje.
        
        Equipo de Global Exchange
        '''
        
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [usuario.email],
            fail_silently=True
        )


class VistaRestablecimientoContrasena(FormView):
    """
    Vista de confirmación de restablecimiento de contraseña con token
    """
    template_name = 'cuentas/restablecimiento_contrasena.html'
    form_class = 'FormularioRestablecimientoContrasena'
    success_url = reverse_lazy('cuentas:iniciar_sesion')
    
    def get_form_class(self):
        from .forms import FormularioRestablecimientoContrasena
        return FormularioRestablecimientoContrasena
    
    def dispatch(self, solicitud, token, *args, **kwargs):
        """Valida el token antes de procesar"""
        try:
            self.registro_restablecimiento = RestablecimientoContrasena.objects.get(token=token, utilizado=False)
            
            if self.registro_restablecimiento.ha_expirado():
                messages.error(solicitud, 'El enlace de recuperación ha expirado. Solicite uno nuevo.')
                return redirect('cuentas:restablecer_contrasena')
            
        except RestablecimientoContrasena.DoesNotExist:
            messages.error(solicitud, 'El enlace de recuperación es inválido. Solicite uno nuevo.')
            return redirect('cuentas:restablecer_contrasena')
        
        return super().dispatch(solicitud, token, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['usuario'] = self.registro_restablecimiento.usuario
        if 'form' in contexto:
            contexto['formulario'] = contexto['form']
        else:
            # Si no hay 'form', crear uno vacío o manejar el caso
            contexto['formulario'] = self.get_form()#contexto['formulario'] = contexto['form']
        
        return contexto
    
    def form_valid(self, formulario):
        # Restablecer la contraseña
        usuario = self.registro_restablecimiento.usuario
        nueva_contrasena = formulario.cleaned_data['nueva_contrasena1']
        usuario.set_password(nueva_contrasena)
        usuario.save()
        
        # Marcar el token de restablecimiento como utilizado
        self.registro_restablecimiento.utilizado = True
        self.registro_restablecimiento.save()
        
        # Registrar evento de auditoría
        RegistroAuditoria.objects.create(
            usuario=usuario,
            accion='PASSWORD_RESET',
            descripcion='Usuario restableció su contraseña mediante email',
            direccion_ip=self.request.META.get('REMOTE_ADDR'),
            agente_usuario=self.request.META.get('HTTP_USER_AGENT')
        )
        
        messages.success(
            self.request,
            'Su contraseña ha sido restablecida exitosamente. Ya puede iniciar sesión.'
        )
        
        return super().form_valid(formulario)


class VistaCambioContrasena(LoginRequiredMixin, FormView):
    """
    Vista de cambio de contraseña para usuarios autenticados
    """
    template_name = 'cuentas/cambiar_contrasena.html'
    form_class = FormularioCambioContrasena
    success_url = reverse_lazy('cuentas:perfil')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formulario'] = context['form']
        return context
    
    def form_valid(self, formulario):
        formulario.save()
        
        # Registrar evento de auditoría
        from .models import RegistroAuditoria
        RegistroAuditoria.objects.create(
            usuario=self.request.user,
            accion='PASSWORD_CHANGE',
            descripcion='Usuario cambió su contraseña',
            direccion_ip=self.request.META.get('REMOTE_ADDR'),
            agente_usuario=self.request.META.get('HTTP_USER_AGENT')
        )
        
        messages.success(self.request, 'Contraseña cambiada exitosamente.')
        return super().form_valid(formulario)


# Vistas de iToken

class VistaConfiguracionDosFactores(LoginRequiredMixin, TemplateView):
    """
    Configura iToken para la cuenta del usuario
    """
    template_name = 'cuentas/2fa_configurar.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Comprobar si el usuario ya tiene 2FA activado
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        dispositivos_usuario = TOTPDevice.objects.devices_for_user(self.request.user)
        contexto['tiene_dispositivo_totp'] = dispositivos_usuario.exists()
        contexto['dispositivos_totp'] = dispositivos_usuario
        
        # Obtener o crear la configuración 2FA
        from .models import ConfiguracionDosFactoresUsuario
        configuracion, creado = ConfiguracionDosFactoresUsuario.objects.get_or_create(
            usuario=self.request.user
        )
        contexto['configuracion_2fa'] = configuracion
        
        return contexto


class VistaActivarDosFactores(LoginRequiredMixin, TemplateView):
    """
    Activa el dispositivo iToken TOTP
    """
    template_name = 'cuentas/2fa_activar.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        from django_otp.plugins.otp_totp.models import TOTPDevice
        import qrcode
        import io
        import base64
        
        # Crear u obtener dispositivo no confirmado
        dispositivo = TOTPDevice.objects.filter(
            user=self.request.user,
            confirmed=False
        ).first()
        
        if not dispositivo:
            dispositivo = TOTPDevice.objects.create(
                user=self.request.user,
                name=f"Global Exchange - {self.request.user.email}",
                confirmed=False
            )
        
        # Generar código QR
        uri_aprovisionamiento = dispositivo.config_url
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri_aprovisionamiento)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer_img = io.BytesIO()
        img.save(buffer_img, format='PNG')
        buffer_img.seek(0)
        
        datos_codigo_qr = base64.b64encode(buffer_img.getvalue()).decode()
        
        contexto.update({
            'dispositivo': dispositivo,
            'datos_codigo_qr': datos_codigo_qr,
            'clave_entrada_manual': dispositivo.bin_key.hex(),
            'uri_aprovisionamiento': uri_aprovisionamiento
        })
        
        return contexto
    
    def post(self, solicitud, *args, **kwargs):
        """Verifica y confirma el dispositivo TOTP"""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        token = solicitud.POST.get('token')
        if not token:
            messages.error(solicitud, 'Por favor ingrese el código de verificación.')
            return self.get(solicitud, *args, **kwargs)
        
        # Obtener dispositivo no confirmado
        dispositivo = TOTPDevice.objects.filter(
            user=solicitud.user,
            confirmed=False
        ).first()
        
        if not dispositivo:
            messages.error(solicitud, 'No se encontró dispositivo para configurar.')
            return redirect('cuentas:itoken_configurar')
        
        # Verificar token
        if dispositivo.verify_token(token):
            # Confirmar dispositivo
            dispositivo.confirmed = True
            dispositivo.save()
            
            # Activar iToken para el usuario
            solicitud.user.autenticacion_dos_factores_activa = True
            solicitud.user.save()
            
            # Registrar evento de auditoría
            from .models import RegistroAuditoria
            RegistroAuditoria.objects.create(
                usuario=solicitud.user,
                accion='2FA_SETUP',
                descripcion='Usuario configuró autenticación de dos factores',
                direccion_ip=solicitud.META.get('REMOTE_ADDR'),
                agente_usuario=solicitud.META.get('HTTP_USER_AGENT')
            )
            
            messages.success(solicitud, '¡iToken configurado exitosamente!')
            return redirect('cuentas:itoken_configurar')
        else:
            messages.error(solicitud, 'Código de verificación inválido. Intente nuevamente.')
            return self.get(solicitud, *args, **kwargs)


class VistaTokensRespaldoDosFactores(LoginRequiredMixin, TemplateView):
    """
    Muestra los tokens de respaldo después de la configuración de iToken
    """
    template_name = 'cuentas/2fa_tokens_respaldo.html'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        
        # Obtener tokens de respaldo de la sesión
        tokens_respaldo = self.request.session.get('tokens_respaldo', [])
        contexto['tokens_respaldo'] = tokens_respaldo
        
        return contexto
    
    def post(self, solicitud, *args, **kwargs):
        """Confirma la recepción de los tokens de respaldo y los elimina de la sesión"""
        if 'tokens_respaldo' in solicitud.session:
            del solicitud.session['tokens_respaldo']
        
        messages.success(solicitud, 'Tokens de respaldo guardados correctamente.')
        return redirect('cuentas:itoken_configurar')


class VistaDesactivarDosFactores(LoginRequiredMixin, TemplateView):
    """
    Desactiva iToken para la cuenta del usuario
    """
    template_name = 'cuentas/2fa_desactivar.html'
    
    def post(self, solicitud, *args, **kwargs):
        """Desactiva 2FA después de la confirmación con iToken"""
        token = solicitud.POST.get('token')
        confirmar = solicitud.POST.get('confirmar')
        
        if not token:
            messages.error(solicitud, 'Por favor ingrese el código de verificación.')
            return self.get(solicitud, *args, **kwargs)
        
        if not confirmar:
            messages.error(solicitud, 'Debe confirmar que entiende los riesgos.')
            return self.get(solicitud, *args, **kwargs)
        
        # Verificar token TOTP
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        dispositivos = TOTPDevice.objects.filter(user=solicitud.user, confirmed=True)
        verificado = False
        
        for dispositivo in dispositivos:
            if dispositivo.verify_token(token):
                verificado = True
                break
        
        if not verificado:
            messages.error(solicitud, 'Código de verificación inválido.')
            return self.get(solicitud, *args, **kwargs)
        
        # Eliminar todos los dispositivos TOTP
        TOTPDevice.objects.filter(user=solicitud.user).delete()
        
        # Desactivar 2FA
        solicitud.user.autenticacion_dos_factores_activa = False
        solicitud.user.tokens_respaldo = []
        solicitud.user.save()
        
        # Registrar evento de auditoría
        from .models import RegistroAuditoria
        RegistroAuditoria.objects.create(
            usuario=solicitud.user,
            accion='2FA_DISABLE',
            descripcion='Usuario desactivó autenticación de dos factores',
            direccion_ip=solicitud.META.get('REMOTE_ADDR'),
            agente_usuario=solicitud.META.get('HTTP_USER_AGENT')
        )
        
        messages.success(solicitud, 'iToken desactivado correctamente.')
        return redirect('cuentas:itoken_configurar')


class VistaVerificarDosFactores(TemplateView):
    """
    Verifica el token 2FA durante el inicio de sesión
    """
    template_name = 'cuentas/2fa_verificar.html'
    
    def dispatch(self, solicitud, *args, **kwargs):
        # Comprobar si el usuario está parcialmente autenticado
        if not hasattr(solicitud, 'session') or not solicitud.session.get('id_usuario_pre_2fa'):
            messages.error(solicitud, 'Sesión inválida.')
            return redirect('cuentas:iniciar_sesion')
        
        return super().dispatch(solicitud, *args, **kwargs)
    
    def post(self, solicitud, *args, **kwargs):
        """Verifica el token 2FA"""
        token = solicitud.POST.get('token')
        
        if not token:
            messages.error(solicitud, 'Por favor ingrese el código de verificación.')
            return self.get(solicitud, *args, **kwargs)
        
        # Obtener usuario de la sesión
        id_usuario = solicitud.session.get('id_usuario_pre_2fa')
        try:
            usuario = Usuario.objects.get(id=id_usuario)
        except Usuario.DoesNotExist:
            messages.error(solicitud, 'Sesión inválida.')
            return redirect('cuentas:iniciar_sesion')
        
        # Verificar token TOTP
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        dispositivos = TOTPDevice.objects.filter(user=usuario, confirmed=True)
        verificado = False
        
        for dispositivo in dispositivos:
            if dispositivo.verify_token(token):
                verificado = True
                break
        
        if verificado:
            # Completar el login
            login(solicitud, usuario)
            
            # Limpiar sesión
            if 'id_usuario_pre_2fa' in solicitud.session:
                del solicitud.session['id_usuario_pre_2fa']
            
            # Registrar evento de auditoría
            from .models import RegistroAuditoria
            RegistroAuditoria.objects.create(
                usuario=usuario,
                accion='2FA_VERIFY',
                descripcion='Usuario verificó 2FA exitosamente',
                direccion_ip=solicitud.META.get('REMOTE_ADDR'),
                agente_usuario=solicitud.META.get('HTTP_USER_AGENT')
            )
            
            messages.success(solicitud, f'¡Bienvenido, {usuario.nombre_completo}!')
            
            # Redirigir a la página solicitada originalmente
            siguiente_pagina = solicitud.session.get('redireccion_login', '/divisas/')
            if 'redireccion_login' in solicitud.session:
                del solicitud.session['redireccion_login']
            
            return redirect(siguiente_pagina)
        else:
            messages.error(solicitud, 'Código de verificación inválido.')
            return self.get(solicitud, *args, **kwargs)


class MixinRequerirDosFactores:
    """
    Mixin para requerir 2FA para operaciones sensibles
    """
    def dispatch(self, solicitud, *args, **kwargs):
        if solicitud.user.is_authenticated and solicitud.user.requiere_2fa('sensible'):
            # Comprobar si el usuario ha verificado 2FA recientemente (en la última hora)
            from django.utils import timezone
            from datetime import timedelta
            
            ultima_verificacion_2fa = solicitud.session.get('ultima_verificacion_2fa')
            if ultima_verificacion_2fa:
                hora_ultima_verificacion = timezone.datetime.fromisoformat(ultima_verificacion_2fa)
                if timezone.now() - hora_ultima_verificacion < timedelta(hours=1):
                    return super().dispatch(solicitud, *args, **kwargs)
            
            # Requerir verificación 2FA
            solicitud.session['redireccion_operacion_sensible'] = solicitud.get_full_path()
            messages.warning(solicitud, 'Esta operación requiere verificación adicional.')
            return redirect('cuentas:itoken_verificar_sensible')
        
        return super().dispatch(solicitud, *args, **kwargs)


class VistaVerificarDosFactoresSensible(LoginRequiredMixin, TemplateView):
    """
    Verifica 2FA para operaciones sensibles
    """
    template_name = 'cuentas/2fa_verificar_sensible.html'
    
    def post(self, solicitud, *args, **kwargs):
        """Verifica el token 2FA para una operación sensible"""
        token = solicitud.POST.get('token')
        
        if not token:
            messages.error(solicitud, 'Por favor ingrese el código de verificación.')
            return self.get(solicitud, *args, **kwargs)
        
        # Verificar token TOTP
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        dispositivos = TOTPDevice.objects.filter(user=solicitud.user, confirmed=True)
        verificado = False
        
        for dispositivo in dispositivos:
            if dispositivo.verify_token(token):
                verificado = True
                break
        
        if verificado:
            # Marcar como verificado en la sesión
            from django.utils import timezone
            solicitud.session['ultima_verificacion_2fa'] = timezone.now().isoformat()
            
            messages.success(solicitud, 'Verificación exitosa.')
            
            # Redirigir a la operación original
            url_redireccion = solicitud.session.get('redireccion_operacion_sensible', '/')
            if 'redireccion_operacion_sensible' in solicitud.session:
                del solicitud.session['redireccion_operacion_sensible']
            
            return redirect(url_redireccion)
        else:
            messages.error(solicitud, 'Código de verificación inválido.')
            return self.get(solicitud, *args, **kwargs)


# Decorador para verificar permisos de administrador
def requiere_permiso_admin(permiso):
    """Decorador para requerir permisos específicos de administrador."""
    from django.contrib.auth.decorators import user_passes_test
    from django.core.exceptions import PermissionDenied
    
    def test_permiso(user):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.tiene_permiso(permiso)
    
    return user_passes_test(test_permiso, login_url='cuentas:iniciar_sesion')


class MixinPermisosAdmin:
    """Mixin para verificar permisos de administrador en vistas basadas en clases."""
    permiso_requerido = None
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('cuentas:iniciar_sesion')
        
        if not request.user.is_superuser and not request.user.tiene_permiso(self.permiso_requerido):
            messages.error(request, 'No tiene permisos para acceder a esta funcionalidad.')
            return redirect('divisas:panel_de_control')
        
        return super().dispatch(request, *args, **kwargs)


class VistaGestionarRoles(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Vista para gestionar roles del sistema.
    """
    template_name = 'cuentas/gestionar_roles.html'
    permiso_requerido = 'gestionar_roles'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            'roles': Rol.objects.all().prefetch_related('permisos'),
            'total_roles': Rol.objects.count(),
            'total_permisos': Permiso.objects.count(),
        })
        return contexto


class VistaCrearRol(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Vista para crear un nuevo rol.
    """
    template_name = 'cuentas/crear_rol.html'
    permiso_requerido = 'gestionar_roles'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        from .forms import FormularioRol
        contexto['formulario'] = FormularioRol()
        contexto['permisos'] = Permiso.objects.all().order_by('descripcion')
        return contexto
    
    def post(self, request, *args, **kwargs):
        from .forms import FormularioRol
        formulario = FormularioRol(request.POST)
        
        if formulario.is_valid():
            # Crear el rol
            rol = formulario.save()
            
            # Registrar en auditoría
            RegistroAuditoria.objects.create(
                usuario=request.user,
                accion='ROLE_CREATED',
                descripcion=f'Creó el rol: {rol.nombre_rol}',
                direccion_ip=request.META.get('REMOTE_ADDR'),
                agente_usuario=request.META.get('HTTP_USER_AGENT'),
                datos_adicionales={'rol_id': rol.id, 'rol_nombre': rol.nombre_rol}
            )
            
            messages.success(request, f'Rol "{rol.nombre_rol}" creado exitosamente.')
            return redirect('cuentas:gestionar_roles')
        else:
            contexto = self.get_context_data(**kwargs)
            contexto['formulario'] = formulario
            messages.error(request, 'Error al crear el rol. Verifique los datos ingresados.')
            return render(request, self.template_name, contexto)


class VistaEditarRol(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Vista para editar un rol existente.
    """
    template_name = 'cuentas/editar_rol.html'
    permiso_requerido = 'gestionar_roles'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        rol_id = kwargs.get('rol_id')
        rol = get_object_or_404(Rol, id=rol_id)
        
        from .forms import FormularioRol
        contexto.update({
            'rol': rol,
            'formulario': FormularioRol(instance=rol),
            'permisos': Permiso.objects.all().order_by('descripcion'),
            'es_edicion': True
        })
        return contexto
    
    def post(self, request, *args, **kwargs):
        rol_id = kwargs.get('rol_id')
        rol = get_object_or_404(Rol, id=rol_id)
        
        # Verificar que no se editen roles críticos del sistema
        if rol.es_sistema and rol.nombre_rol == 'Administrador':
            # Permitir solo editar descripción y algunos permisos específicos
            pass
        
        from .forms import FormularioRol
        formulario = FormularioRol(request.POST, instance=rol)
        
        if formulario.is_valid():
            rol_actualizado = formulario.save()
            
            # Registrar en auditoría
            RegistroAuditoria.objects.create(
                usuario=request.user,
                accion='ROLE_UPDATED',
                descripcion=f'Actualizó el rol: {rol_actualizado.nombre_rol}',
                direccion_ip=request.META.get('REMOTE_ADDR'),
                agente_usuario=request.META.get('HTTP_USER_AGENT'),
                datos_adicionales={'rol_id': rol_actualizado.id, 'rol_nombre': rol_actualizado.nombre_rol}
            )
            
            messages.success(request, f'Rol "{rol_actualizado.nombre_rol}" actualizado exitosamente.')
            return redirect('cuentas:gestionar_roles')
        else:
            contexto = self.get_context_data(**kwargs)
            contexto['formulario'] = formulario
            messages.error(request, 'Error al actualizar el rol. Verifique los datos ingresados.')
            return render(request, self.template_name, contexto)


class VistaEliminarRol(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Vista para eliminar un rol.
    """
    template_name = 'cuentas/eliminar_rol.html'
    permiso_requerido = 'gestionar_roles'
    
    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        rol_id = kwargs.get('rol_id')
        rol = get_object_or_404(Rol, id=rol_id)
        
        contexto.update({
            'rol': rol,
            'usuarios_afectados': Usuario.objects.filter(roles=rol),
            'puede_eliminar': not rol.es_sistema
        })
        return contexto
    
    def post(self, request, *args, **kwargs):
        rol_id = kwargs.get('rol_id')
        rol = get_object_or_404(Rol, id=rol_id)
        
        # No permitir eliminar roles del sistema
        if rol.es_sistema:
            messages.error(request, 'No se pueden eliminar roles del sistema.')
            return redirect('cuentas:gestionar_roles')
        
        nombre_rol = rol.nombre_rol
        
        # Registrar en auditoría antes de eliminar
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='ROLE_DELETED',
            descripcion=f'Eliminó el rol: {nombre_rol}',
            direccion_ip=request.META.get('REMOTE_ADDR'),
            agente_usuario=request.META.get('HTTP_USER_AGENT'),
            datos_adicionales={'rol_id': rol.id, 'rol_nombre': nombre_rol}
        )
        
        # Eliminar el rol
        rol.delete()
        
        messages.success(request, f'Rol "{nombre_rol}" eliminado exitosamente.')
        return redirect('cuentas:gestionar_roles')


class VistaGestionarUsuarios(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Vista para gestionar usuarios.
    """
    template_name = 'cuentas/gestionar_usuarios.html'
    permiso_requerido = 'asignar_roles'
    
    def get_context_data(self, **kwargs):
        from django.db import models
        contexto = super().get_context_data(**kwargs)
        
        # Paginación de usuarios
        from django.core.paginator import Paginator
        usuarios = Usuario.objects.all().prefetch_related('roles').order_by('nombre_completo')
        
        # Filtros
        buscar = self.request.GET.get('buscar', '')
        if buscar:
            usuarios = usuarios.filter(
                models.Q(nombre_completo__icontains=buscar) |
                models.Q(email__icontains=buscar) |
                models.Q(username__icontains=buscar)
            )
        
        paginator = Paginator(usuarios, 20)  # 20 usuarios por página
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        contexto.update({
            'usuarios': page_obj,
            'roles_disponibles': Rol.objects.all(),
            'buscar': buscar
        })
        return contexto


class VistaAsignarRolesUsuario(LoginRequiredMixin, MixinPermisosAdmin, TemplateView):
    """
    Vista para asignar roles a un usuario específico.
    """
    template_name = 'cuentas/asignar_roles_usuario.html'
    permiso_requerido = 'asignar_roles'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario_id = kwargs.get('usuario_id')
        usuario = get_object_or_404(Usuario, id=usuario_id)

        from .forms import FormularioAsignarRoles
        contexto.update({
            'usuario_objetivo': usuario,
            'formulario': FormularioAsignarRoles(usuario=usuario),
            'roles_actuales': usuario.roles.all(),
            'permisos_actuales': usuario.obtener_permisos()
        })
        return contexto

    def post(self, request, *args, **kwargs):
        usuario_id = kwargs.get('usuario_id')
        usuario = get_object_or_404(Usuario, id=usuario_id)

        from .forms import FormularioAsignarRoles
        formulario = FormularioAsignarRoles(usuario=usuario, data=request.POST)

        if formulario.is_valid():
            roles_anteriores = list(usuario.roles.all())
            usuario_actualizado = formulario.save()
            roles_nuevos = list(usuario.roles.all())

            # Registrar en auditoría
            RegistroAuditoria.objects.create(
                usuario=request.user,
                accion='ROLE_ASSIGNED',
                descripcion=f'Modificó roles del usuario: {usuario.email}',
                direccion_ip=request.META.get('REMOTE_ADDR'),
                agente_usuario=request.META.get('HTTP_USER_AGENT'),
                datos_adicionales={
                    'usuario_id': usuario.id,
                    'usuario_email': usuario.email,
                    'roles_anteriores': [r.nombre_rol for r in roles_anteriores],
                    'roles_nuevos': [r.nombre_rol for r in roles_nuevos]
                }
            )

            messages.success(request, f'Roles actualizados para {usuario.nombre_completo}.')
            return redirect('cuentas:gestionar_usuarios')
        else:
            contexto = self.get_context_data(**kwargs)
            contexto['formulario'] = formulario
            messages.error(request, 'Error al asignar roles. Verifique los datos.')
            return render(request, self.template_name, contexto)


Usuario = get_user_model()

# Modelo temporal para guardar el código OTP de desbloqueo (puedes crear un modelo real)
# Aquí solo se simula con un diccionario para ejemplo
CODIGOS_DESBLOQUEO = {}

class VistaSolicitudDesbloqueoCuenta(FormView):
    template_name = 'cuentas/solicitud_desbloqueo.html'
    form_class = FormularioSolicitudDesbloqueoCuenta
    success_url = reverse_lazy('cuentas:verificar_codigo_desbloqueo')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            usuario = Usuario.objects.get(email=email)
            if not usuario.esta_cuenta_bloqueada():
                messages.info(self.request, 'Tu cuenta no está bloqueada.')
                return redirect('cuentas:iniciar_sesion')
            # Generar código OTP simple
            codigo = str(uuid.uuid4())[:8]
            # Guardar código temporalmente
            CODIGOS_DESBLOQUEO[email] = {
                'codigo': codigo,
                'expira': timezone.now() + timezone.timedelta(minutes=1)
            }

            # Enviar correo
            #self.enviar_email_desbloqueo(usuario, codigo)

            #de momento imprimimos en la consola el codigo
            print(f"Código OTP para {email}: {codigo}")

            messages.success(self.request, f'Se envió un código de desbloqueo a {email}.')
        except Usuario.DoesNotExist:
            messages.info(self.request, 'Si el correo existe, recibirá instrucciones.')
        return super().form_valid(form)

    def enviar_email_desbloqueo(self, usuario, codigo):
        """Envía el email de restablecimiento de contraseña"""
        enlace_restablecimiento = self.request.build_absolute_uri(
            f'/cuentas/contrasena/restablecer/{codigo}/'
        )

        asunto = 'Desbloqueo de cuenta - Global Exchange'
        mensaje = f'''
        Hola {usuario.nombre_completo},

        Ha desbloquear su cuenta en Global Exchange.

        Para desbloquear su cuenta ingrese el siguiente codigo
        {codigo}, o haz clic en el siguiente enlace.
        {enlace_restablecimiento}

        Este enlace expirará en 1 hora por motivos de seguridad.

        Si no solicitó este cambio, ignore este mensaje.

        Equipo de Global Exchange
        '''

        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [usuario.email],
            fail_silently=True
        )

class VistaVerificarCodigoDesbloqueo(FormView):
    template_name = 'cuentas/verificar_codigo_desbloqueo.html'
    form_class = FormularioVerificacionCodigoDesbloqueo
    success_url = reverse_lazy('cuentas:iniciar_sesion')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        codigo = form.cleaned_data['codigo']
        registro = CODIGOS_DESBLOQUEO.get(email)
        if not registro or registro['expira'] < timezone.now():
            messages.error(self.request, 'El código ha expirado o es inválido.')
            return super().form_invalid(form)
        if registro['codigo'] != codigo:
            messages.error(self.request, 'Código incorrecto.')
            return super().form_invalid(form)
        try:
            usuario = Usuario.objects.get(email=email)
            usuario.restablecer_intentos_fallidos()
            usuario.save()
            # Eliminar el código usado
            del CODIGOS_DESBLOQUEO[email]
            messages.success(self.request, '¡Cuenta desbloqueada exitosamente! Ahora puede iniciar sesión.')
        except Usuario.DoesNotExist:
            messages.error(self.request, 'Usuario no encontrado.')
        return super().form_valid(form)

class EditarUsuario(LoginRequiredMixin, MixinPermisosAdmin, UpdateView):
    """
    Vista para editar a un usuario específico.
    """
    model = get_user_model()  # Modelo de usuario
    form_class = EditarUsuarioForm  # Formulario que definimos
    template_name = 'cuentas/editar_usuario.html'  # Template
    pk_url_kwarg = 'usuario_id'  # Nombre del parámetro en la URL
    success_url = reverse_lazy('cuentas:gestionar_usuarios')  # A dónde redirige al guardar

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuario_objetivo'] = self.object  # Le damos el nombre que quieres en el template
        return context

    def form_valid(self, form):
        usuario = self.object  # Usuario antes de guardar
        datos_anteriores = {
            'nombre_completo': usuario.nombre_completo,
            'email': usuario.email,
            # agregar más campos si quieres auditar
        }

        # Guardar cambios
        response = super().form_valid(form)
        usuario_actualizado = self.object

        # Detectar cambios en los campos del formulario
        cambios_campos = {}
        for field, valor_anterior in datos_anteriores.items():
            valor_nuevo = getattr(usuario_actualizado, field)
            if valor_anterior != valor_nuevo:
                cambios_campos[field] = {'anterior': valor_anterior, 'nuevo': valor_nuevo}

        # Registrar en auditoría
        RegistroAuditoria.objects.create(
            usuario=self.request.user,
            accion='USER_UPDATED',
            descripcion=f'Modificó usuario: {usuario.email}',
            direccion_ip=self.request.META.get('REMOTE_ADDR'),
            agente_usuario=self.request.META.get('HTTP_USER_AGENT'),
            datos_adicionales={
                'usuario_id': usuario.id,
                'usuario_email': usuario.email,
                'campos_cambiados': cambios_campos,
            }
        )

        # Mensaje de éxito
        messages.success(self.request, "Usuario actualizado correctamente")
        return response

    def form_invalid(self, form):
        # Mostrar error si el formulario es inválido
        messages.error(self.request, "Por favor, corrige los errores en el formulario.")
        return super().form_invalid(form)

class CambiarEstadoUsuarioView(LoginRequiredMixin, MixinPermisosAdmin, View):
    def post(self, request, usuario_id):
        Usuario = get_user_model()
        usuario = get_object_or_404(Usuario, id=usuario_id)

        if usuario.is_active:
            usuario.bloquear(ejecutor=request.user)
            messages.success(request, f"Usuario {usuario.email} bloqueado correctamente.")
        else:
            usuario.desbloquear(ejecutor=request.user)
            messages.success(request, f"Usuario {usuario.email} desbloqueado correctamente.")

        return redirect('cuentas:editar_usuario', usuario_id=usuario.id)