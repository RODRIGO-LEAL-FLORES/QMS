from django.urls import path
from apps.usuarios.views import login_view, logout_view
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    path('login/', login_view, name='login'),
    path('home/', views.home, name='home'),
    path('scrap/', views.scrap, name='scrap'),
    path('logout/', logout_view, name='logout'),

    path(
        'api/notificaciones/',
        views.api_notificaciones,
        name='api_notificaciones'
    ),

    path(
        'api/notificaciones/<int:notificacion_id>/',
        views.eliminar_notificacion,
        name='eliminar_notificacion'
    ),
]