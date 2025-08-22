from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.vista_login, name='tauser_login'),
    path('logout/', views.vista_logout, name='tauser_logout'),
    path('dashboard/', views.dashboard, name='tauser_dashboard'),
    path('depositar/', views.depositar, name='tauser_depositar'),
    path('extraer/', views.extraer, name='tauser_extraer'),
]