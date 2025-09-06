from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponseRedirect

# Establecer encabezados personalizados del sitio de administración
admin.site.site_header = "Global Exchange - Administración"
admin.site.site_title = "Admin de Global Exchange"
admin.site.index_title = "Panel de Administración"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cuentas/', include('cuentas.urls')),
    path('clientes/', include('clientes.urls')),
    path('divisas/', include('divisas.urls')),
    path('transacciones/', include('transacciones.urls')),
    path('reportes/', include('reportes.urls')),
    path('notificaciones/', include('notificaciones.urls')),
    
    # Specific redirects for legacy API endpoints
    path('currencies/api/rates/', lambda request: HttpResponseRedirect('/divisas/api/tasas/')),
    path('currencies/', lambda request: HttpResponseRedirect('/divisas/')),
    
    path('', lambda solicitud: redirect('divisas:panel_de_control')),  # Redirigir al panel de control
    path('tauser/', include('tauser.urls')),
    path('pagos/', include('pagos.urls')),
]

# Servir archivos de medios en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)