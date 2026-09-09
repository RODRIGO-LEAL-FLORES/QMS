
from django.urls import path
from . import views

urlpatterns=[
    path('',views.scrap,name='scrap'),
    path('reportes/',views.scrap_reportes,name='scrap_reportes'),
    path('reportes/pdf/',views.scrap_reporte_pdf,name='scrap_reporte_pdf'),
    path('get-turno/',views.get_turno,name='get_turno'),

    path('action/<str:section>/<str:action_type>/',views.scrap_actions,name='scrap_actions'),
    path('action/<str:section>/<str:action_type>/<int:item_id>/',views.scrap_actions,name='scrap_actions_item'),

    path('registro/editar/<int:item_id>/',views.scrap_editar,name='scrap_editar'),
    path('registro/eliminar/<int:item_id>/',views.scrap_eliminar,name='scrap_eliminar'),

    path('<str:section>/',views.scrap_section,name='scrap_section'),
]


