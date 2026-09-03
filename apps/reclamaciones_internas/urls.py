

from django.urls import path
from . import views


operacion = views.requiere_operacion_reclamaciones_internas
catalogo = views.requiere_catalogo_reclamaciones_internas

urlpatterns = [
    path('', operacion(views.reclamaciones_internas), name='reclamaciones_int'),
    path('nuevo/', operacion(views.reclamaciones_internas_create), name='reclamaciones_internas_create'),
    path('editar/<int:item_id>/', operacion(views.reclamacion_interna_editar), name='reclamacion_interna_editar'),
    path('eliminar/<int:item_id>/', operacion(views.reclamacion_interna_eliminar), name='reclamacion_interna_eliminar'),
    path('mis-pendientes/', operacion(views.mis_reclamaciones_internas), name='mis_reclamaciones_internas'),
    path('seguimiento/', operacion(views.seguimiento_reclamaciones_internas), name='seguimiento_reclamaciones_internas'),
    path('por-cerrar/', operacion(views.reclamaciones_por_cerrar), name='reclamaciones_por_cerrar'),
    path('detalle/<int:item_id>/', operacion(views.reclamacion_interna_detail), name='reclamacion_interna_detail'),

    path('prioridades/', catalogo(views.prioridades), name='prioridades'),
    path('prioridades/crear/', catalogo(views.prioridad_crear), name='prioridad_crear'),
    path('prioridades/editar/<int:item_id>/', catalogo(views.prioridad_editar), name='prioridad_editar'),
    path('prioridades/eliminar/<int:item_id>/', catalogo(views.prioridad_eliminar), name='prioridad_eliminar'),

    path('areas/', catalogo(views.areas), name='areas'),
    path('areas/crear/', catalogo(views.area_crear), name='area_crear'),
    path('areas/editar/<int:item_id>/', catalogo(views.area_editar), name='area_editar'),
    path('areas/eliminar/<int:item_id>/', catalogo(views.area_eliminar), name='area_eliminar'),

   
    path('estatus/', catalogo(views.estatus_reclamaciones_internas), name='estatus_reclamaciones_internas'),
    path('estatus/crear/', catalogo(views.estatus_crear), name='estatus_crear'),
    path('estatus/editar/<int:item_id>/', catalogo(views.estatus_editar), name='estatus_editar'),
    path('estatus/eliminar/<int:item_id>/', catalogo(views.estatus_eliminar), name='estatus_eliminar'),

    path('reportes/', views.reportes_reclamaciones_internas, name='reportes_reclamaciones_internas'),
    path('reportes/csv/', views.reportes_exportar_csv, name='reportes_exportar_csv'),
]


