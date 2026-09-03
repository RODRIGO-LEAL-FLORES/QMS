from django.urls import path
from . import views

urlpatterns = [
    path('', views.reclamaciones, name='reclamaciones'),

    path(
        'reportes/',
        views.reclamaciones_reportes,
        name='reclamaciones_reportes'
    ),

    path(
        'reportes/pdf/',
        views.reclamaciones_reportes_pdf,
        name='reclamaciones_reportes_pdf'
    ),

    path(
        'action/nuevo/editar/<int:item_id>/',
        views.reclamaciones_editar,
        name='reclamaciones_editar'
    ),

    path(
        'action/nuevo/eliminar/<int:item_id>/',
        views.reclamaciones_eliminar,
        name='reclamaciones_eliminar'
    ),

    path(
        'action/<str:section>/<str:action_type>/',
        views.reclamaciones_actions,
        name='reclamaciones_actions'
    ),

    path(
        'action/<str:section>/<str:action_type>/<int:item_id>/',
        views.reclamaciones_actions,
        name='reclamaciones_actions_item'
    ),

    path(
        '<str:section>/',
        views.reclamaciones_section,
        name='reclamaciones_section'
    ),
]


