

from django.urls import path
from . import views


operacion = views.requiere_operacion_reclamaciones_internas
catalogo = views.requiere_catalogo_reclamaciones_internas
areas_consulta = views.requiere_permiso_submodulo('areas.view_area')
areas_agregar = views.requiere_permiso_submodulo('areas.add_area')
areas_editar = views.requiere_permiso_submodulo('areas.change_area')
areas_eliminar = views.requiere_permiso_submodulo('areas.delete_area')
prioridades_consulta = views.requiere_permiso_submodulo('reclamaciones_internas.view_prioridad')
prioridades_agregar = views.requiere_permiso_submodulo('reclamaciones_internas.add_prioridad')
prioridades_editar = views.requiere_permiso_submodulo('reclamaciones_internas.change_prioridad')
prioridades_eliminar = views.requiere_permiso_submodulo('reclamaciones_internas.delete_prioridad')
estatus_consulta = views.requiere_permiso_submodulo('reclamaciones_internas.view_estatusreclamacioninterna')
estatus_agregar = views.requiere_permiso_submodulo('reclamaciones_internas.add_estatusreclamacioninterna')
estatus_editar = views.requiere_permiso_submodulo('reclamaciones_internas.change_estatusreclamacioninterna')
estatus_eliminar = views.requiere_permiso_submodulo('reclamaciones_internas.delete_estatusreclamacioninterna')
formato_consulta = views.requiere_permiso_submodulo('reclamaciones_internas.view_formatoreclamacioninterna')
formato_editar = views.requiere_permiso_submodulo('reclamaciones_internas.change_formatoreclamacioninterna')
formato_eliminar = views.requiere_permiso_submodulo('reclamaciones_internas.delete_formatoreclamacioninterna')

urlpatterns = [
    path('', operacion(views.reclamaciones_internas), name='reclamaciones_int'),
    path('nuevo/', operacion(views.reclamaciones_internas_create), name='reclamaciones_internas_create'),
    path('editar/<int:item_id>/', operacion(views.reclamacion_interna_editar), name='reclamacion_interna_editar'),
    path('eliminar/<int:item_id>/', operacion(views.reclamacion_interna_eliminar), name='reclamacion_interna_eliminar'),
    path('mis-pendientes/', operacion(views.mis_reclamaciones_internas), name='mis_reclamaciones_internas'),
    path('seguimiento/', operacion(views.seguimiento_reclamaciones_internas), name='seguimiento_reclamaciones_internas'),
    path('por-cerrar/', operacion(views.reclamaciones_por_cerrar), name='reclamaciones_por_cerrar'),
    path('detalle/<int:item_id>/', operacion(views.reclamacion_interna_detail), name='reclamacion_interna_detail'),
    path('formato/', formato_consulta(views.formato_reclamacion_interna), name='formato_reclamacion_interna'),
    path('formato/editar/<int:item_id>/', formato_editar(views.formato_reclamacion_interna_editar), name='formato_reclamacion_interna_editar'),
    path('formato/eliminar/<int:item_id>/', formato_eliminar(views.formato_reclamacion_interna_eliminar), name='formato_reclamacion_interna_eliminar'),

    path('prioridades/', prioridades_consulta(views.prioridades), name='prioridades'),
    path('prioridades/crear/', prioridades_agregar(views.prioridad_crear), name='prioridad_crear'),
    path('prioridades/editar/<int:item_id>/', prioridades_editar(views.prioridad_editar), name='prioridad_editar'),
    path('prioridades/eliminar/<int:item_id>/', prioridades_eliminar(views.prioridad_eliminar), name='prioridad_eliminar'),

    path('areas/', areas_consulta(views.areas), name='areas'),
    path('areas/crear/', areas_agregar(views.area_crear), name='area_crear'),
    path('areas/editar/<int:item_id>/', areas_editar(views.area_editar), name='area_editar'),
    path('areas/eliminar/<int:item_id>/', areas_eliminar(views.area_eliminar), name='area_eliminar'),

   
    path('estatus/', estatus_consulta(views.estatus_reclamaciones_internas), name='estatus_reclamaciones_internas'),
    path('estatus/crear/', estatus_agregar(views.estatus_crear), name='estatus_crear'),
    path('estatus/editar/<int:item_id>/', estatus_editar(views.estatus_editar), name='estatus_editar'),
    path('estatus/eliminar/<int:item_id>/', estatus_eliminar(views.estatus_eliminar), name='estatus_eliminar'),

    path('reportes/', views.reportes_reclamaciones_internas, name='reportes_reclamaciones_internas'),
    path('reportes/csv/', views.reportes_exportar_csv, name='reportes_exportar_csv'),
]


