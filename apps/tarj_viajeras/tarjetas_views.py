"""Vistas de tarjetas viajeras y su configuración operativa."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Max, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction

from apps.clientes.models import Cliente
from apps.scrap.models import TipoAcero
from apps.liberaciones.models import TipoLaminacion

from .models import (
    ConfiguracionPiezasAlambre,
    Espesor,
    NumeroParteCliente,
    PROCESOS_PRODUCCION,
    ProcesoTarjeta,
    Produccion,
    ReasignacionTarjeta,
    StatusTar,
    TarjetaViajera,
)
from .services.formularios import (
    datos_configuracion_piezas as _datos_configuracion_piezas,
    datos_tarjeta as _datos_tarjeta,
    validar_datos_configuracion_piezas as _validar_datos_configuracion_piezas,
)
from .services.produccion import configuracion_de_produccion as _configuracion_de_produccion
from .services.procesos import estatus_permitido as _estatus_permitido
from .views import (
    redirect_edicion,
    requiere_acceso_tarj_viajeras,
    requiere_actualizar_tarj_viajera,
    requiere_permiso_tarj_viajeras,
    usuario_puede,
    usuario_puede_actualizar_datos_tarj_viajeras,
    usuario_puede_actualizar_tarj_viajeras,
    usuario_puede_gestionar_tarj_viajeras,
    usuario_puede_imprimir_tarj_viajeras,
)

# =========================================================
# TARJETAS VIAJERAS
# =========================================================


@login_required
@requiere_acceso_tarj_viajeras
def tarjetas_viajeras(request):
    search_query=request.GET.get('search','').strip()

    tarjetas=TarjetaViajera.objects.select_related(
        'produccion',
        'produccion__cliente',
        'produccion__material',
        'produccion__espesor',
        'produccion__laminacion',
        'produccion__numero_parte_cliente',
        'status'
        , 'proceso_tarjeta'
    ).order_by('-id_tarjeta')

    if search_query:
        # Corrige lectura del COM-598: Ñ -> :
        codigo_busqueda=(search_query
            .replace('Ñ',':').replace('ñ',':')
            .replace('Ç','|').replace('ç','|')
        )

        # Código de barras: OT|FOLIO
        # Ejemplo leído: EÑ9617|23
        # Se convierte a: E:9617|23
        if '|' in codigo_busqueda:
            orden,folio=codigo_busqueda.split('|',1)

            if orden.strip() and folio.strip():
                tarjetas=tarjetas.filter(
                    produccion__numero_orden_trabajo__iexact=orden.strip(),
                    numero_tarjeta__exact=folio.strip()
                )
            else:
                tarjetas=tarjetas.none()
        else:
            # Búsqueda normal/manual
            tarjetas=tarjetas.filter(
                Q(numero_tarjeta__icontains=search_query) |
                Q(sufijo__icontains=search_query) |
                Q(status__descripcion__icontains=search_query) |
                Q(produccion__numero_orden_trabajo__icontains=search_query) |
                Q(produccion__lote__icontains=search_query) |
                Q(produccion__cliente__nombre__icontains=search_query)
            ).order_by('numero_tarjeta')

    paginator=Paginator(tarjetas,20)
    page_obj=paginator.get_page(request.GET.get('page'))

    edit_item=None
    edit_id=request.GET.get('edit_id')

    if edit_id and edit_id.isdigit():
        edit_item=get_object_or_404(
            TarjetaViajera,
            id_tarjeta=edit_id
        )

    ultimo_folio=TarjetaViajera.objects.aggregate(
        m=Max('numero_tarjeta')
    )['m'] or 0

    return render(
        request,
        'tarj_viajeras/tarjetas_viajeras.html',
        {
            'page_obj':page_obj,
            'search_query':search_query,
            'edit_item':edit_item,
            'estatus':StatusTar.objects.all().order_by('descripcion'),
            'procesos_tarjeta':ProcesoTarjeta.objects.filter(activo=True).prefetch_related('estatus_proceso__status'),
            'producciones':Produccion.objects.select_related(
                'cliente'
            ).order_by('-id_produccion'),
            'siguiente_folio':ultimo_folio+1,
            'puede_gestionar_tarj_viajeras':
                usuario_puede_gestionar_tarj_viajeras(request.user),
            'puede_actualizar_datos_tarj_viajeras':
                usuario_puede_actualizar_datos_tarj_viajeras(request.user),
            'puede_actualizar_estatus_tarj_viajeras':
                usuario_puede_actualizar_tarj_viajeras(request.user),
            'puede_imprimir_tarj_viajeras':
                usuario_puede_imprimir_tarj_viajeras(request.user),
        }
    )

@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.view_configuracionpiezasalambre')
def configuracion_piezas_alambre(request):
    search_query = request.GET.get('search', '').strip()
    items = ConfiguracionPiezasAlambre.objects.select_related(
        'cliente',
        'numero_parte_cliente',
        'laminacion'
    ).order_by('cliente__nombre', 'numero_parte_cliente__descripcion', 'proceso')

    if search_query:
        items = items.filter(
            Q(cliente__nombre__icontains=search_query) |
            Q(numero_parte_cliente__descripcion__icontains=search_query) |
            Q(laminacion__especificacion__icontains=search_query) |
            Q(proceso__icontains=search_query)
        )

    edit_item = None
    edit_id = request.GET.get('edit_id')
    if edit_id and edit_id.isdigit():
        edit_item = get_object_or_404(ConfiguracionPiezasAlambre, pk=edit_id)

    return render(
        request,
        'tarj_viajeras/configuracion_piezas_alambre.html',
        {
            'items': items,
            'edit_item': edit_item,
            'search_query': search_query,
            'clientes': Cliente.objects.filter(activo=True).order_by('nombre'),
            'numeros_parte': NumeroParteCliente.objects.all().order_by(
                'descripcion'
            ),
            'laminaciones': TipoLaminacion.objects.all().order_by(
                'especificacion'
            ),
            'procesos': PROCESOS_PRODUCCION,
            'puede_agregar_configuracion': usuario_puede(request.user, 'tarj_viajeras.add_configuracionpiezasalambre'),
            'puede_editar_configuracion': usuario_puede(request.user, 'tarj_viajeras.change_configuracionpiezasalambre'),
            'puede_eliminar_configuracion': usuario_puede(request.user, 'tarj_viajeras.delete_configuracionpiezasalambre'),
        }
    )


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.add_configuracionpiezasalambre')
def configuracion_piezas_alambre_crear(request):
    if request.method == 'POST':
        datos = _datos_configuracion_piezas(request.POST)
        piezas = _validar_datos_configuracion_piezas(datos)
        if piezas is None:
            messages.error(
                request,
                'Completa todos los campos e introduce piezas por alambre '
                'con un número entero igual o mayor a cero.'
            )
            return redirect('configuracion_piezas_alambre')

        clave = {
            'cliente_id': datos['cliente_id'],
            'numero_parte_cliente_id': datos['numero_parte_id'],
            'laminacion_id': datos['laminacion_id'],
            'proceso': datos['proceso'],
        }
        if ConfiguracionPiezasAlambre.objects.filter(**clave).exists():
            messages.error(
                request,
                'Ya existe una configuración para esa combinación.'
            )
            return redirect('configuracion_piezas_alambre')

        ConfiguracionPiezasAlambre.objects.create(
            **clave,
            piezas_por_alambre=piezas
        )
        messages.success(request, 'Configuración creada correctamente.')

    return redirect('configuracion_piezas_alambre')


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_configuracionpiezasalambre')
def configuracion_piezas_alambre_editar(request, item_id):
    item = get_object_or_404(ConfiguracionPiezasAlambre, pk=item_id)

    if request.method == 'POST':
        datos = _datos_configuracion_piezas(request.POST)
        piezas = _validar_datos_configuracion_piezas(datos)
        if piezas is None:
            messages.error(
                request,
                'Completa todos los campos e introduce piezas por alambre '
                'con un número entero igual o mayor a cero.'
            )
            return redirect_edicion('configuracion_piezas_alambre', item_id)

        clave = {
            'cliente_id': datos['cliente_id'],
            'numero_parte_cliente_id': datos['numero_parte_id'],
            'laminacion_id': datos['laminacion_id'],
            'proceso': datos['proceso'],
        }
        if ConfiguracionPiezasAlambre.objects.filter(
            **clave
        ).exclude(pk=item_id).exists():
            messages.error(
                request,
                'Ya existe una configuración para esa combinación.'
            )
            return redirect_edicion('configuracion_piezas_alambre', item_id)

        for campo, valor in clave.items():
            setattr(item, campo, valor)
        item.piezas_por_alambre = piezas
        item.save()
        messages.success(request, 'Configuración actualizada correctamente.')

    return redirect('configuracion_piezas_alambre')


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.delete_configuracionpiezasalambre')
def configuracion_piezas_alambre_eliminar(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(ConfiguracionPiezasAlambre, pk=item_id)
        item.delete()
        messages.success(request, 'Configuración eliminada correctamente.')
    return redirect('configuracion_piezas_alambre')


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.add_tarjetaviajera')
def tarjeta_viajera_crear(request, produccion_id):

    produccion_item = get_object_or_404(
        Produccion,
        id_produccion=produccion_id
    )

    if request.method != 'POST':
        return redirect('tarjetas_viajeras')

    d = _datos_tarjeta(request.POST)

    cantidad_raw = request.POST.get('cantidad_tarjetas', '').strip()

    try:
        cantidad = int(cantidad_raw)
    except (TypeError, ValueError):
        cantidad = 0

    if cantidad < 1:
        messages.error(
            request,
            'La cantidad de tarjetas debe ser mayor a 0.'
        )
        return redirect('tarjetas_viajeras')

    try:
        status = StatusTar.objects.get(
            descripcion__iexact='CREADA'
        )
    except StatusTar.DoesNotExist:
        messages.error(
            request,
            'No existe el estatus CREADA en el catálogo de estatus.'
        )
        return redirect('tarjetas_viajeras')
    except StatusTar.MultipleObjectsReturned:
        messages.error(
            request,
            'Existe más de un estatus con el nombre CREADA.'
        )
        return redirect('tarjetas_viajeras')

    proceso_tarjeta = get_object_or_404(
        ProcesoTarjeta,
        pk=d['proceso_tarjeta_id'],
        activo=True,
    ) if d['proceso_tarjeta_id'] else None
    if proceso_tarjeta is None:
        messages.error(request, 'Selecciona un proceso para la tarjeta.')
        return redirect('tarjetas_viajeras')
    if not _estatus_permitido(proceso_tarjeta, status.id_status):
        messages.error(request, 'El estatus inicial no pertenece al proceso seleccionado.')
        return redirect('tarjetas_viajeras')

    ultimo_folio = TarjetaViajera.objects.aggregate(
        m=Max('numero_tarjeta')
    )['m'] or 0

    primer_folio = int(ultimo_folio) + 1
    ultimo_folio_nuevo = primer_folio + cantidad - 1

    with transaction.atomic():

        for numero_tarjeta in range(
            primer_folio,
            ultimo_folio_nuevo + 1
        ):

            if TarjetaViajera.objects.filter(
                numero_tarjeta=numero_tarjeta,
                sufijo=d['sufijo'] or None
            ).exists():
                messages.error(
                    request,
                    f'Ya existe una tarjeta con el número {numero_tarjeta} '
                    f'y sufijo {d["sufijo"] or ""}.'
                )
                return redirect('tarjetas_viajeras')

            TarjetaViajera.objects.create(
                produccion=produccion_item,
                numero_tarjeta=numero_tarjeta,
                sufijo=d['sufijo'] or None,
                status=status,
                proceso_tarjeta=proceso_tarjeta,
                numero_alambres=d['numero_alambres'] or None,
                piezas_por_alambre=(
                    produccion_item.piezas_por_alambre
                    if produccion_item.piezas_por_alambre is not None
                    else d['piezas_por_alambre'] or None
                ),
                peso_kg=d['peso_kg'] or None,
                peso_lbs=d['peso_lbs'] or None,
                tara=d['tara'] or None
            )

    messages.success(
        request,
        f'{cantidad} tarjeta{"s" if cantidad != 1 else ""} '
        f'viajera{"s" if cantidad != 1 else ""} creada'
        f'{"s" if cantidad != 1 else ""} correctamente.'
    )

    return redirect('tarjetas_viajeras')


@login_required
@requiere_acceso_tarj_viajeras
def tarjeta_viajera_detalle(request, item_id):

    tarjeta = get_object_or_404(
        TarjetaViajera.objects.select_related(
            'produccion',
            'produccion__cliente',
            'produccion__material',
            'produccion__espesor',
                'produccion__laminacion',
            'produccion__numero_parte_cliente',
            'status'
        ),
        id_tarjeta=item_id
    )

    return render(
        request,
        'tarj_viajeras/tarjeta_viajera_detalle.html',
        {
            'tarjeta': tarjeta,
            'puede_actualizar_tarj_viajeras':
                usuario_puede_actualizar_tarj_viajeras(request.user),
            'puede_imprimir_tarj_viajeras':
                usuario_puede_imprimir_tarj_viajeras(request.user),
        }
    )


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_reasignaciontarjeta')
def tarjeta_viajera_reasignar(request, item_id):
    tarjeta = get_object_or_404(
        TarjetaViajera.objects.select_related(
            'produccion',
            'produccion__cliente',
            'produccion__numero_parte_cliente'
        ),
        id_tarjeta=item_id
    )
    produccion_base = tarjeta.produccion.subvariante_de or tarjeta.produccion
    tarjetas_familia = (
        TarjetaViajera.objects
        .filter(
            Q(produccion_id=produccion_base.pk) |
            Q(produccion__subvariante_de_id=produccion_base.pk)
        )
        .select_related(
            'produccion',
            'produccion__cliente',
            'produccion__numero_parte_cliente'
        )
        .order_by('numero_tarjeta', 'sufijo')
    )
    variantes = (
        Produccion.objects
        .filter(subvariante_de_id=produccion_base.pk)
        .select_related('cliente', 'numero_parte_cliente')
        .order_by('id_produccion')
    )
    reasignaciones = (
        tarjeta.reasignaciones
        .select_related(
            'produccion_origen',
            'produccion_origen__cliente',
            'produccion_origen__numero_parte_cliente',
            'produccion_destino',
            'produccion_destino__cliente',
            'produccion_destino__numero_parte_cliente'
        )
        .order_by('-fecha')
    )

    return render(
        request,
        'tarj_viajeras/tarjeta_viajera_reasignar.html',
        {
            'tarjeta': tarjeta,
            'tarjetas_familia': tarjetas_familia,
            'variantes': variantes,
            'clientes': Cliente.objects.filter(activo=True).order_by('nombre'),
            'numeros_parte': NumeroParteCliente.objects.all().order_by(
                'descripcion'
            ),
            'reasignaciones': reasignaciones,
        }
    )


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_reasignaciontarjeta')
def tarjeta_viajera_reasignar_crear(request, item_id):
    if request.method != 'POST':
        return redirect('tarjeta_viajera_reasignar', item_id=item_id)

    destino_id = request.POST.get('id_produccion_destino', '').strip()
    motivo = request.POST.get('motivo', '').strip()
    tarjetas_ids = request.POST.getlist('tarjetas')

    cliente_id = request.POST.get('id_cliente', '').strip()
    numero_parte_id = request.POST.get('id_num_pcli', '').strip()
    if destino_id and not destino_id.isdigit():
        messages.error(request, 'Selecciona una producción destino existente.')
        return redirect('tarjeta_viajera_reasignar', item_id=item_id)
    if not destino_id and not all((cliente_id.isdigit(), numero_parte_id.isdigit())):
        messages.error(request, 'Selecciona cliente y número de parte para crear la variante.')
        return redirect('tarjeta_viajera_reasignar', item_id=item_id)

    if not motivo:
        messages.error(request, 'Debes indicar el motivo de la reasignación.')
        return redirect('tarjeta_viajera_reasignar', item_id=item_id)

    if not tarjetas_ids or any(not x.isdigit() for x in tarjetas_ids):
        messages.error(request, 'Selecciona al menos una tarjeta válida.')
        return redirect('tarjeta_viajera_reasignar', item_id=item_id)

    ids = [int(x) for x in tarjetas_ids]

    if len(ids) != len(set(ids)):
        messages.error(request, 'Hay tarjetas duplicadas en la selección.')
        return redirect('tarjeta_viajera_reasignar', item_id=item_id)

    with transaction.atomic():
        referencia = get_object_or_404(
            TarjetaViajera.objects.select_for_update().select_related('produccion'),
            id_tarjeta=item_id
        )

        base = referencia.produccion.subvariante_de or referencia.produccion

        if destino_id:
            destino = Produccion.objects.select_for_update().filter(
                Q(id_produccion=base.pk) | Q(subvariante_de_id=base.pk),
                id_produccion=destino_id
            ).first()
        else:
            destino = Produccion.objects.select_for_update().filter(
                subvariante_de_id=base.pk,
                cliente_id=cliente_id,
                numero_parte_cliente_id=numero_parte_id,
                laminacion_id=base.laminacion_id,
            ).first()
            if destino is None:
                destino = Produccion.objects.create(
                    subvariante_de=base,
                    numero_orden_trabajo=base.numero_orden_trabajo,
                    lote=base.lote,
                    proceso=base.proceso,
                    numero_orden_compra=base.numero_orden_compra,
                    material=base.material,
                    espesor=base.espesor,
                    laminacion=base.laminacion,
                    cliente_id=cliente_id,
                    numero_parte_cliente_id=numero_parte_id,
                    piezas_por_alambre=base.piezas_por_alambre,
                )

        if destino is None:
            messages.error(request, 'El destino no existe o no pertenece a esta producción.')
            return redirect('tarjeta_viajera_reasignar', item_id=item_id)

        tarjetas = list(
            TarjetaViajera.objects.select_for_update().filter(
                Q(produccion_id=base.pk) | Q(produccion__subvariante_de_id=base.pk),
                id_tarjeta__in=ids
            ).select_related('produccion')
        )

        if len(tarjetas) != len(ids):
            messages.error(request, 'Una o varias tarjetas no pertenecen a esta orden.')
            return redirect('tarjeta_viajera_reasignar', item_id=item_id)

        repetidas = [t.folio_completo for t in tarjetas if t.produccion_id == destino.pk]

        if repetidas:
            messages.error(
                request,
                'Estas tarjetas ya pertenecen al destino seleccionado: ' + ', '.join(repetidas)
            )
            return redirect('tarjeta_viajera_reasignar', item_id=item_id)

        for tarjeta in tarjetas:
            ReasignacionTarjeta.objects.create(
                tarjeta=tarjeta,
                produccion_origen=tarjeta.produccion,
                produccion_destino=destino,
                motivo=motivo
            )
            tarjeta.produccion = destino
            tarjeta.save(update_fields=['produccion'])

    messages.success(request, f'Se reasignaron correctamente {len(tarjetas)} tarjetas.')
    return redirect('tarjeta_viajera_reasignar', item_id=item_id)
@login_required
@requiere_actualizar_tarj_viajera
def tarjeta_viajera_editar(request, item_id):

    item = get_object_or_404(TarjetaViajera, id_tarjeta=item_id)

    if request.method != 'POST':
        return redirect_edicion('tarjetas_viajeras', item_id)

    d = _datos_tarjeta(request.POST)

    proceso_tarjeta = item.proceso_tarjeta
    if usuario_puede_gestionar_tarj_viajeras(request.user):
        if not d['proceso_tarjeta_id']:
            messages.error(request, 'Selecciona un proceso para la tarjeta.')
            return redirect_edicion('tarjetas_viajeras', item_id)
        proceso_tarjeta = get_object_or_404(ProcesoTarjeta, pk=d['proceso_tarjeta_id'], activo=True)
    if not _estatus_permitido(proceso_tarjeta, d['status_id']):
        messages.error(request, 'El estatus seleccionado no pertenece al proceso de esta tarjeta.')
        return redirect_edicion('tarjetas_viajeras', item_id)

    if request.user.has_perm('tarj_viajeras.update_status_tarjetaviajera'):
        if not d['status_id']:
            messages.error(request, 'El estatus es obligatorio.')
            return redirect_edicion('tarjetas_viajeras', item_id)
        item.status = get_object_or_404(StatusTar, id_status=d['status_id'])
        if usuario_puede_gestionar_tarj_viajeras(request.user):
            item.proceso_tarjeta = proceso_tarjeta
        item.save(update_fields=['status', 'proceso_tarjeta'])
        messages.success(request, 'Estatus de la tarjeta actualizado correctamente.')
        return redirect('tarjetas_viajeras')

    if request.user.has_perm('tarj_viajeras.update_measurements_tarjetaviajera'):
        if not d['status_id']:
            messages.error(request, 'El estatus es obligatorio.')
            return redirect_edicion('tarjetas_viajeras', item_id)
        item.status = get_object_or_404(StatusTar, id_status=d['status_id'])
        item.proceso_tarjeta = proceso_tarjeta
        item.numero_alambres = d['numero_alambres'] or None
        item.piezas_por_alambre = d['piezas_por_alambre'] or None
        item.peso_kg = d['peso_kg'] or None
        item.peso_lbs = d['peso_lbs'] or None
        item.tara = d['tara'] or None
        item.save(update_fields=[
            'status',
            'proceso_tarjeta',
            'numero_alambres',
            'piezas_por_alambre',
            'peso_kg',
            'peso_lbs',
            'tara',
        ])
        messages.success(request, 'Tarjeta viajera actualizada correctamente.')
        return redirect('tarjetas_viajeras')

    if not d['numero_tarjeta'] or not d['status_id']:
        messages.error(
            request,
            'El número de tarjeta y el estatus son obligatorios.'
        )
        return redirect_edicion('tarjetas_viajeras', item_id)

    if TarjetaViajera.objects.filter(
        numero_tarjeta=d['numero_tarjeta'],
        sufijo=d['sufijo'] or None
    ).exclude(id_tarjeta=item_id).exists():
        messages.error(
            request,
            'Ya existe otra tarjeta con ese número y sufijo.'
        )
        return redirect_edicion('tarjetas_viajeras', item_id)

    item.numero_tarjeta = d['numero_tarjeta']
    item.sufijo = d['sufijo'] or None
    item.status = get_object_or_404(StatusTar, id_status=d['status_id'])
    item.proceso_tarjeta = proceso_tarjeta
    item.numero_alambres = d['numero_alambres'] or None
    item.piezas_por_alambre = d['piezas_por_alambre'] or None
    item.peso_kg = d['peso_kg'] or None
    item.peso_lbs = d['peso_lbs'] or None
    item.tara = d['tara'] or None
    item.save()

    messages.success(request, 'Tarjeta viajera actualizada correctamente.')
    return redirect('tarjetas_viajeras')


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.delete_tarjetaviajera')
def tarjeta_viajera_eliminar(request, item_id):

    if request.method != 'POST':
        return redirect('tarjetas_viajeras')

    item = get_object_or_404(TarjetaViajera, id_tarjeta=item_id)

    try:
        item.delete()
        messages.success(request, 'Tarjeta viajera eliminada correctamente.')
    except ProtectedError:
        messages.error(
            request,
            'No se puede eliminar porque la tarjeta está siendo utilizada.'
        )

    return redirect('tarjetas_viajeras')
