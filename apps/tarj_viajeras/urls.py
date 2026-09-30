from django.urls import path
from . import views

urlpatterns = [
    # Dashboard principal
    path('', views.tarj_viajeras, name='tarj_viajeras'),

    # Producción
    path('produccion/', views.produccion, name='produccion'),
    path('produccion/crear/', views.produccion_crear, name='produccion_crear'),
    path('produccion/editar/<int:item_id>/', views.produccion_editar, name='produccion_editar'),

    # Tarjetas Viajeras
    path('tarjetas/', views.tarjetas_viajeras, name='tarjetas_viajeras'),
    path('tarjetas/crear/<int:produccion_id>/', views.tarjeta_viajera_crear, name='tarjeta_viajera_crear'),
    path('tarjetas/detalle/<int:item_id>/', views.tarjeta_viajera_detalle, name='tarjeta_viajera_detalle'),
    path('tarjetas/editar/<int:item_id>/', views.tarjeta_viajera_editar, name='tarjeta_viajera_editar'),
    path('tarjetas/eliminar/<int:item_id>/', views.tarjeta_viajera_eliminar, name='tarjeta_viajera_eliminar'),

    # Impresión / PDF
    path('tarjetas-viajeras/imprimir/', views.tarjetas_viajeras_imprimir, name='tarjetas_viajeras_imprimir'),
    path('produccion/<int:produccion_id>/tarjetas-json/', views.get_tarjetas_produccion, name='get_tarjetas_produccion'),
    path('tarjetas-viajeras/<int:item_id>/pdf/', views.tarjeta_viajera_pdf, name='tarjeta_viajera_pdf'),
    path('tarjetas-viajeras/pdf/', views.tarjetas_viajeras_pdf, name='tarjetas_viajeras_pdf'),

    # Catálogo de Espesores
    path('catalogos/espesores/', views.espesores, name='espesores'),
    path('catalogos/espesores/crear/', views.espesor_crear, name='espesor_crear'),
    path('catalogos/espesores/editar/<int:item_id>/', views.espesor_editar, name='espesor_editar'),
    path('catalogos/espesores/eliminar/<int:item_id>/', views.espesor_eliminar, name='espesor_eliminar'),

    # Catálogo de Tipo de Acero
    path('catalogos/tipo-acero/', views.tipo_acero, name='tarj_tipo_acero'),
    path('catalogos/tipo-acero/crear/', views.tipo_acero_crear, name='tarj_tipo_acero_crear'),
    path('catalogos/tipo-acero/editar/<int:item_id>/', views.tipo_acero_editar, name='tarj_tipo_acero_editar'),
    path('catalogos/tipo-acero/eliminar/<int:item_id>/', views.tipo_acero_eliminar, name='tarj_tipo_acero_eliminar'),

    # Catálogo de Tipos de Laminación
    path('catalogos/tipo-laminacion/', views.tipo_laminacion, name='tarj_tipo_laminacion'),
    path('catalogos/tipo-laminacion/crear/', views.tipo_laminacion_crear, name='tarj_tipo_laminacion_crear'),
    path('catalogos/tipo-laminacion/editar/<int:item_id>/', views.tipo_laminacion_editar, name='tarj_tipo_laminacion_editar'),
    path('catalogos/tipo-laminacion/eliminar/<int:item_id>/', views.tipo_laminacion_eliminar, name='tarj_tipo_laminacion_eliminar'),

    # Catálogo de Número de Parte Cliente
    path('catalogos/numero-parte/', views.numero_parte_cliente, name='numero_parte_cliente'),
    path('catalogos/numero-parte/crear/', views.numero_parte_cliente_crear, name='numero_parte_cliente_crear'),
    path('catalogos/numero-parte/editar/<int:item_id>/', views.numero_parte_cliente_editar, name='numero_parte_cliente_editar'),
    path('catalogos/numero-parte/eliminar/<int:item_id>/', views.numero_parte_cliente_eliminar, name='numero_parte_cliente_eliminar'),

    # Catálogo de Status
    path('catalogos/status/', views.status_tarjeta, name='status_tarjeta'),
    path('catalogos/status/crear/', views.status_tarjeta_crear, name='status_tarjeta_crear'),
    path('catalogos/status/editar/<int:item_id>/', views.status_tarjeta_editar, name='status_tarjeta_editar'),
    path('catalogos/status/eliminar/<int:item_id>/', views.status_tarjeta_eliminar, name='status_tarjeta_eliminar'),

    path('tarjetas/status/barcodes/pdf/',views.status_tarjetas_pdf,name='status_tarjetas_pdf'),
    path('tarjetas/escaner/',views.escaner_tarjetas,name='escaner_tarjetas'),
    path('tarjetas/escaner/cambiar-status/',views.cambiar_status_barcode,name='cambiar_status_barcode'),



    # Reportes
    path('reportes/excel/', views.tarj_viajeras_excel, name='tarj_viajeras_excel'),

    # Consultas / AJAX
    path('get-folio/', views.get_folio, name='get_folio'),
    path('get-produccion/<int:item_id>/', views.get_produccion, name='get_produccion'),

    # Acciones genéricas
    path('action/<str:section>/<str:action_type>/', views.tarj_viajeras_actions, name='tarj_viajeras_actions'),
    path('action/<str:section>/<str:action_type>/<int:item_id>/', views.tarj_viajeras_actions, name='tarj_viajeras_actions_item'),
]