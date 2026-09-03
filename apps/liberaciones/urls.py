from django.urls import path
from . import views


urlpatterns = [
    path('', views.liberaciones, name='liberaciones'),
    path('nuevo/', views.generar_liberacion, name='generar_liberacion'),
    path('nuevo/crear/', views.liberacion_crear, name='liberacion_crear'),
    path('nuevo/editar/<int:pk>/', views.liberacion_editar, name='liberacion_editar'),
    path('nuevo/eliminar/<int:pk>/', views.liberacion_eliminar, name='liberacion_eliminar'),
    
    
   
   
    path('maquina/<int:pk>/ultima/',views.ultima_liberacion_maquina,name='ultima_liberacion_maquina'),
    
  
    
    
    path('clientes/', views.clientes_liberaciones, name='clientes_liberaciones'),
    path('clientes/crear/', views.cliente_liberacion_crear, name='cliente_liberacion_crear'),
    path('clientes/editar/<int:pk>/', views.cliente_liberacion_editar, name='cliente_liberacion_editar'),
    path('clientes/eliminar/<int:pk>/', views.cliente_liberacion_eliminar, name='cliente_liberacion_eliminar'),
    
    
    
    path('maquinas/', views.maquinas_liberaciones, name='maquinas_liberaciones'),
    path('maquinas/crear/', views.maquina_liberacion_crear, name='maquina_liberacion_crear'),
    path('maquinas/editar/<int:pk>/', views.maquina_liberacion_editar, name='maquina_liberacion_editar'),
    path('maquinas/eliminar/<int:pk>/', views.maquina_liberacion_eliminar, name='maquina_liberacion_eliminar'),
        
    
    
    path('tipos-laminacion/', views.tipos_laminacion, name='tipos_laminacion'),
    path('tipos-laminacion/crear/', views.tipo_laminacion_crear, name='tipo_laminacion_crear'),
    path('tipos-laminacion/editar/<int:pk>/', views.tipo_laminacion_editar, name='tipo_laminacion_editar'),
    path('tipos-laminacion/eliminar/<int:pk>/', views.tipo_laminacion_eliminar, name='tipo_laminacion_eliminar'),
    
    
    path('estatus/', views.estatus_liberaciones, name='estatus_liberaciones'),
    path('estado-maquinas/', views.maquinas_status, name='maquinas_status'),
    path('estatus/crear/', views.estatus_liberacion_crear, name='estatus_liberacion_crear'),
    path('estatus/editar/<int:pk>/', views.estatus_liberacion_editar, name='estatus_liberacion_editar'),
    path('estatus/eliminar/<int:pk>/', views.estatus_liberacion_eliminar, name='estatus_liberacion_eliminar'),
    
    
    
    
]