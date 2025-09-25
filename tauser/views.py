from django.core.checks import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import FormDeposito, FormExtraccion
from transacciones.models import Transaccion
from cuentas.models import Usuario
from rest_framework import serializers

def vista_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        usuario = authenticate(request, email=email, password=password)
        if usuario:
            login(request, usuario)
            return redirect('tauser_dashboard')
        else:
                # Buscar por nombre de usuario
                usuario = Usuario.objects.get(email=email)
                usuario.incrementar_intentos_fallidos()

                #messages.error(request, 'Credenciales inválidas.')
                return render(request, 'tauser/login_tauser.html', {'error': 'Credenciales incorrectas'})
    return render(request, 'tauser/login_tauser.html')

@login_required
def dashboard(request):
    return render(request, 'tauser/dashboard.html')

@login_required
def depositar(request):
    if request.method == 'POST':
        form = FormDeposito(request.POST)
        if form.is_valid():
            # Crear transacción tipo DEPOSITO
            Transaccion.objects.create(
                tipo_transaccion='DEPOSITO',
                usuario=request.user,
                monto_origen=form.cleaned_data['monto'],
                moneda_origen_id=form.cleaned_data['moneda'],
                # Completar otros campos necesarios...
            )
            return redirect('tauser_dashboard')
    else:
        form = FormDeposito()
    return render(request, 'tauser/depositar.html', {'form': form})

@login_required
def extraer(request):
    if request.method == 'POST':
        form = FormExtraccion(request.POST)
        if form.is_valid():
            # Crear transacción tipo EXTRACCION
            Transaccion.objects.create(
                tipo_transaccion='EXTRACCION',
                usuario=request.user,
                monto_origen=form.cleaned_data['monto'],
                moneda_origen_id=form.cleaned_data['moneda'],
                # Completar otros campos necesarios...
            )
            return redirect('tauser_dashboard')
    else:
        form = FormExtraccion()
    return render(request, 'tauser/extraer.html', {'form': form})

def vista_logout(request):
    logout(request)
    return redirect('tauser_login')