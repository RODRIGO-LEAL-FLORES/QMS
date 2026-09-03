from django.urls import path
from . import views



urlpatterns = [
    path('', views.usuarios, name='usuarios'),
    path('crear/', views.crear_usuario, name='crear_usuario'),
    path('editar/<int:id_usuario>/', views.editar_usuario, name='editar_usuario'),
    path('eliminar/<int:id_usuario>/', views.eliminar_usuario, name='eliminar_usuario'),
]