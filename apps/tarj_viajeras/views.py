from functools import wraps


from io import BytesIO

import barcode
from barcode.writer import SVGWriter

from django.http import HttpResponse, JsonResponse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Max, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.db import transaction


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128

from .models import (
    Espesor,
    NumeroParteCliente,
    StatusTar,
    Produccion,
    TarjetaViajera,
)

from apps.clientes.models import Cliente
from apps.scrap.models import TipoAcero
from apps.liberaciones.models import TipoLaminacion


# =========================================================
# PERMISOS
# =========================================================

def usuario_puede_ver_tarj_viajeras(user):
    return (
        user.is_authenticated
        and user.is_active
        and user.puede_gestionar_targetas_viajeras
    )


def requiere_acceso_tarj_viajeras(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not usuario_puede_ver_tarj_viajeras(request.user):
            messages.error(
                request,
                'No tienes permisos para acceder a Tarjetas Viajeras.'
            )
            return redirect('home')
        return view(request, *args, **kwargs)
    return wrapped


def requiere_gestion_tarj_viajeras(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if (
            not usuario_puede_ver_tarj_viajeras(request.user)
            or request.user.rol_id not in (1, 2, 4)
        ):
            messages.error(
                request,
                'Tu rol no permite gestionar Tarjetas Viajeras.'
            )
            return redirect('home')
        return view(request, *args, **kwargs)
    return wrapped


def requiere_admin_tarj_viajeras(view):
    """Solo rol 1 (o superusuario) con acceso a tarjetas. Igual que el dashboard."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        u = request.user
        if not (
            usuario_puede_ver_tarj_viajeras(u)
            and (u.is_superuser or u.rol_id == 1)
        ):
            messages.error(
                request,
                'No tienes permiso para administrar este catálogo.'
            )
            return redirect('tarj_viajeras')
        return view(request, *args, **kwargs)
    return wrapped


def redirect_edicion(nombre_url, item_id):
    """Redirige a la lista con ?edit_id=, usando reverse en vez de rutas fijas."""
    return redirect(f'{reverse(nombre_url)}?edit_id={item_id}')


# =========================================================
# DASHBOARD
# =========================================================

@login_required
@requiere_acceso_tarj_viajeras
def tarj_viajeras(request):
    return render(
        request,
        'tarj_viajeras/tarj_viajeras_dashboard.html'
    )


# =========================================================
# PRODUCCIÓN
# =========================================================

@login_required
@requiere_gestion_tarj_viajeras
def produccion(request):
    search_query = request.GET.get('search', '').strip()

    registros = Produccion.objects.select_related(
        'cliente',
        'material',
        'espesor',
        'laminacion',
        'numero_parte_cliente'
    ).order_by('-id_produccion')

    if search_query:
        registros = registros.filter(
            Q(numero_orden_trabajo__icontains=search_query) |
            Q(lote__icontains=search_query) |
            Q(numero_orden_compra__icontains=search_query) |
            Q(cliente__nombre__icontains=search_query) |
            Q(material__especificacion__icontains=search_query)
        )

    paginator = Paginator(registros, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    edit_item = None
    edit_id = request.GET.get('edit_id')
    if edit_id and edit_id.isdigit():
        edit_item = get_object_or_404(Produccion, id_produccion=edit_id)

    return render(
        request,
        'tarj_viajeras/produccion.html',
        {
            'page_obj': page_obj,
            'search_query': search_query,
            'edit_item': edit_item,
            'clientes': Cliente.objects.all().order_by('nombre'),
            'materiales': TipoAcero.objects.all().order_by('especificacion'),
            'espesores': Espesor.objects.all().order_by('espesor'),
            'laminaciones': TipoLaminacion.objects.all().order_by('especificacion'),
            'numeros_parte': NumeroParteCliente.objects.all().order_by('descripcion'),
        }
    )


def _datos_produccion(request):
    return {
        'numero_orden': request.POST.get('numero_orden_trabajo', '').strip(),
        'lote': request.POST.get('lote', '').strip(),
        'numero_orden_compra': request.POST.get('numero_orden_compra', '').strip(),
        'cliente_id': request.POST.get('id_cliente'),
        'material_id': request.POST.get('id_material'),
        'espesor_id': request.POST.get('id_espesor'),
        'laminacion_id': request.POST.get('id_laminacion'),
        'numero_parte_id': request.POST.get('id_num_pcli'),
    }


def _produccion_completa(d):
    return all([
        d['numero_orden'], d['lote'], d['cliente_id'], d['material_id'],
        d['espesor_id'], d['laminacion_id'], d['numero_parte_id']
    ])


@login_required
@requiere_gestion_tarj_viajeras
def produccion_crear(request):

    if request.method != 'POST':
        return redirect('produccion')

    d = _datos_produccion(request)

    if not _produccion_completa(d):
        messages.error(request, 'Completa todos los campos obligatorios.')
        return redirect('produccion')

    if Produccion.objects.filter(
        numero_orden_trabajo=d['numero_orden'],
        lote=d['lote']
    ).exists():
        messages.error(
            request,
            'Ya existe una producción con esa orden de trabajo y lote.'
        )
        return redirect('produccion')

    Produccion.objects.create(
        numero_orden_trabajo=d['numero_orden'],
        lote=d['lote'],
        numero_orden_compra=d['numero_orden_compra'] or None,
        cliente=get_object_or_404(Cliente, id_cliente=d['cliente_id']),
        material=get_object_or_404(TipoAcero, id_tipo_acero=d['material_id']),
        espesor=get_object_or_404(Espesor, id_espesor=d['espesor_id']),
        laminacion=get_object_or_404(
            TipoLaminacion, id_tipo_laminacion=d['laminacion_id']
        ),
        numero_parte_cliente=get_object_or_404(
            NumeroParteCliente, id_num_pcli=d['numero_parte_id']
        )
    )

    messages.success(request, 'Producción creada correctamente.')
    return redirect('produccion')


@login_required
@requiere_gestion_tarj_viajeras
def produccion_editar(request, item_id):

    item = get_object_or_404(Produccion, id_produccion=item_id)

    if request.method != 'POST':
        return redirect_edicion('produccion', item_id)

    d = _datos_produccion(request)

    if not _produccion_completa(d):
        messages.error(request, 'Completa todos los campos obligatorios.')
        return redirect_edicion('produccion', item_id)

    if Produccion.objects.filter(
        numero_orden_trabajo=d['numero_orden'],
        lote=d['lote']
    ).exclude(id_produccion=item_id).exists():
        messages.error(
            request,
            'Ya existe otra producción con esa orden de trabajo y lote.'
        )
        return redirect_edicion('produccion', item_id)

    item.numero_orden_trabajo = d['numero_orden']
    item.lote = d['lote']
    item.numero_orden_compra = d['numero_orden_compra'] or None
    item.cliente = get_object_or_404(Cliente, id_cliente=d['cliente_id'])
    item.material = get_object_or_404(TipoAcero, id_tipo_acero=d['material_id'])
    item.espesor = get_object_or_404(Espesor, id_espesor=d['espesor_id'])
    item.laminacion = get_object_or_404(
        TipoLaminacion, id_tipo_laminacion=d['laminacion_id']
    )
    item.numero_parte_cliente = get_object_or_404(
        NumeroParteCliente, id_num_pcli=d['numero_parte_id']
    )
    item.save()

    messages.success(request, 'Producción actualizada correctamente.')
    return redirect('produccion')

@login_required
@requiere_gestion_tarj_viajeras
def get_tarjetas_produccion(request, produccion_id):
    tarjetas = (
        TarjetaViajera.objects
        .filter(produccion__id_produccion=produccion_id)
        .order_by('numero_tarjeta', 'sufijo')
    )

    data = []

    for tarjeta in tarjetas:
        data.append({
            'id_tarjeta': tarjeta.id_tarjeta,
            'folio': tarjeta.folio_completo,
        })

    return JsonResponse({
        'tarjetas': data
    })
# =========================================================
# TARJETAS VIAJERAS
# =========================================================

@login_required
@requiere_gestion_tarj_viajeras
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
    ).order_by('-id_tarjeta')

    if search_query:
        # Código de barras: OT|FOLIO
        # Ejemplo: 3245|2
        if '|' in search_query:
            partes=search_query.split('|',1)
            orden=partes[0].strip()
            folio=partes[1].strip()

            if orden and folio:
                tarjetas=tarjetas.filter(
                    produccion__numero_orden_trabajo__iexact=orden,
                    numero_tarjeta__exact=folio
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
            'producciones':Produccion.objects.select_related(
                'cliente'
            ).order_by('-id_produccion'),
            'siguiente_folio':ultimo_folio+1,
        }
    )

def _datos_tarjeta(request):
    return {
        'numero_tarjeta': request.POST.get('numero_tarjeta', '').strip(),
        'sufijo': request.POST.get('sufijo', '').strip().upper(),
        'status_id': request.POST.get('id_status'),
        'numero_alambres': request.POST.get('numero_alambres'),
        'piezas_por_alambre': request.POST.get('piezas_por_alambre'),
        'peso_kg': request.POST.get('peso_kg'),
        'peso_lbs': request.POST.get('peso_lbs'),
        'tara': request.POST.get('tara', '').strip(),
    }


@login_required
@requiere_gestion_tarj_viajeras
def tarjeta_viajera_crear(request, produccion_id):

    produccion_item = get_object_or_404(
        Produccion,
        id_produccion=produccion_id
    )

    if request.method != 'POST':
        return redirect('tarjetas_viajeras')

    d = _datos_tarjeta(request)

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
                numero_alambres=d['numero_alambres'] or None,
                piezas_por_alambre=d['piezas_por_alambre'] or None,
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
@requiere_gestion_tarj_viajeras
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
        {'tarjeta': tarjeta}
    )


@login_required
@requiere_gestion_tarj_viajeras
def tarjeta_viajera_editar(request, item_id):

    item = get_object_or_404(TarjetaViajera, id_tarjeta=item_id)

    if request.method != 'POST':
        return redirect_edicion('tarjetas_viajeras', item_id)

    d = _datos_tarjeta(request)

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
    item.numero_alambres = d['numero_alambres'] or None
    item.piezas_por_alambre = d['piezas_por_alambre'] or None
    item.peso_kg = d['peso_kg'] or None
    item.peso_lbs = d['peso_lbs'] or None
    item.tara = d['tara'] or None
    item.save()

    messages.success(request, 'Tarjeta viajera actualizada correctamente.')
    return redirect('tarjetas_viajeras')


@login_required
@requiere_gestion_tarj_viajeras
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



def _codigo_barras(tarjeta):
    """Valor que se codifica en el código de barras: NUMERO-SUFIJO."""
    base = str(tarjeta.numero_tarjeta)
    return f'{base}-{tarjeta.sufijo}' if tarjeta.sufijo else base


def _tarjetas_base_qs():
    return TarjetaViajera.objects.select_related(
        'produccion',
        'produccion__cliente',
        'produccion__material',
        'produccion__espesor',
        'produccion__laminacion',
        'produccion__numero_parte_cliente',
        'status'
    )


@login_required
@requiere_gestion_tarj_viajeras
def tarjeta_viajera_imprimir(request, item_id):
    """Imprime UNA tarjeta viajera con su código de barras."""

    tarjeta = get_object_or_404(_tarjetas_base_qs(), id_tarjeta=item_id)
    tarjeta.codigo_barras = _codigo_barras(tarjeta)

    return render(
        request,
        'tarj_viajeras/tarjeta_viajera_imprimir.html',
        {
            'tarjetas': [tarjeta],
            'auto_print': request.GET.get('auto') == '1',
        }
    )


@login_required
@requiere_gestion_tarj_viajeras
def tarjetas_viajeras_imprimir(request):
    """
    Pantalla para seleccionar una Orden de Trabajo
    y posteriormente imprimir todas sus tarjetas viajeras.
    """

    # ---------------------------------------------------------
    # OBTENER LA PRODUCCIÓN SELECCIONADA
    # ---------------------------------------------------------

    produccion_id = request.GET.get('produccion', '').strip()

    # ---------------------------------------------------------
    # LISTADO DE PRODUCCIONES PARA EL SELECT
    # ---------------------------------------------------------

    producciones = (
        Produccion.objects
        .select_related('cliente')
        .order_by('-id_produccion')
    )

    # ---------------------------------------------------------
    # SI TODAVÍA NO SE SELECCIONÓ UNA OT
    # MOSTRAMOS LA PANTALLA DE SELECCIÓN
    # ---------------------------------------------------------

    if not produccion_id:

        return render(
            request,
            'tarj_viajeras/seleccionar_impresion.html',
            {
                'producciones': producciones,
            }
        )

    # ---------------------------------------------------------
    # VALIDAR ID DE PRODUCCIÓN
    # ---------------------------------------------------------

    if not produccion_id.isdigit():

        messages.error(
            request,
            'La orden de trabajo seleccionada no es válida.'
        )

        return redirect('tarjetas_viajeras_imprimir')

    # ---------------------------------------------------------
    # BUSCAR LA PRODUCCIÓN
    # ---------------------------------------------------------

    produccion = get_object_or_404(
        Produccion.objects.select_related(
            'cliente',
            'material',
            'espesor',
            'laminacion',
            'numero_parte_cliente',
        ),
        id_produccion=int(produccion_id)
    )

    # ---------------------------------------------------------
    # BUSCAR TODAS LAS TARJETAS DE ESA OT
    # ---------------------------------------------------------

    tarjetas = list(
        _tarjetas_base_qs()
        .filter(
            produccion__id_produccion=produccion.id_produccion
        )
        .order_by(
            'numero_tarjeta',
            'sufijo'
        )[:200]
    )

    # ---------------------------------------------------------
    # SI LA OT NO TIENE TARJETAS
    # ---------------------------------------------------------

    if not tarjetas:

        messages.error(
            request,
            f'La orden de trabajo '
            f'{produccion.numero_orden_trabajo} '
            f'no tiene tarjetas viajeras.'
        )

        return redirect('tarjetas_viajeras_imprimir')

    # ---------------------------------------------------------
    # PREPARAR CÓDIGOS DE BARRAS
    # ---------------------------------------------------------

    for tarjeta in tarjetas:
        tarjeta.codigo_barras = _codigo_barras(tarjeta)

    # ---------------------------------------------------------
    # ENVIAR LAS TARJETAS AL FORMATO DE IMPRESIÓN
    # ---------------------------------------------------------

    return render(
        request,
        'tarj_viajeras/tarjeta_viajera_imprimir.html',
        {
            'tarjetas': tarjetas,
            'produccion': produccion,
            'auto_print': request.GET.get('auto') == '1',
        }
    )

# =========================================================
# ESPESORES
# =========================================================

@login_required
@requiere_gestion_tarj_viajeras
def espesores(request):

    search_query = request.GET.get('search', '').strip()
    items = Espesor.objects.all().order_by('id_espesor')
    if search_query:
        items = items.filter(espesor__icontains=search_query)

    edit_item = None
    edit_id = request.GET.get('edit_id')
    if edit_id and edit_id.isdigit():
        edit_item = get_object_or_404(Espesor, id_espesor=edit_id)

    return render(
        request,
        'tarj_viajeras/espesores.html',
        {'items': items, 'edit_item': edit_item, 'search_query': search_query}
    )


@login_required
@requiere_gestion_tarj_viajeras
def espesor_crear(request):

    if request.method == 'POST':
        espesor = request.POST.get('espesor', '').strip()

        if not espesor:
            messages.error(request, 'El espesor es obligatorio.')
            return redirect('espesores')

        try:
            if Espesor.objects.filter(espesor=espesor).exists():
                messages.error(request, 'Ese espesor ya existe.')
                return redirect('espesores')
            Espesor.objects.create(espesor=espesor)
        except (ValidationError, ValueError, ArithmeticError):
            messages.error(request, 'Introduce un espesor válido.')
            return redirect('espesores')

        messages.success(request, 'Espesor creado correctamente.')

    return redirect('espesores')


@login_required
@requiere_gestion_tarj_viajeras
def espesor_editar(request, item_id):

    item = get_object_or_404(Espesor, id_espesor=item_id)

    if request.method == 'POST':
        espesor = request.POST.get('espesor', '').strip()

        if not espesor:
            messages.error(request, 'El espesor es obligatorio.')
            return redirect_edicion('espesores', item_id)

        try:
            if Espesor.objects.filter(
                espesor=espesor
            ).exclude(id_espesor=item_id).exists():
                messages.error(request, 'Ese espesor ya existe.')
                return redirect_edicion('espesores', item_id)
            item.espesor = espesor
            item.save()
        except (ValidationError, ValueError, ArithmeticError):
            messages.error(request, 'Introduce un espesor válido.')
            return redirect_edicion('espesores', item_id)

        messages.success(request, 'Espesor actualizado correctamente.')

    return redirect('espesores')


@login_required
@requiere_gestion_tarj_viajeras
def espesor_eliminar(request, item_id):

    if request.method == 'POST':
        item = get_object_or_404(Espesor, id_espesor=item_id)
        try:
            item.delete()
            messages.success(request, 'Espesor eliminado correctamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar porque el espesor está siendo utilizado.'
            )

    return redirect('espesores')


# =========================================================
# NÚMERO DE PARTE CLIENTE
# =========================================================

@login_required
@requiere_gestion_tarj_viajeras
def numero_parte_cliente(request):

    search_query = request.GET.get('search', '').strip()
    items = NumeroParteCliente.objects.all().order_by('id_num_pcli')
    if search_query:
        items = items.filter(descripcion__icontains=search_query)

    edit_item = None
    edit_id = request.GET.get('edit_id')
    if edit_id and edit_id.isdigit():
        edit_item = get_object_or_404(NumeroParteCliente, id_num_pcli=edit_id)

    return render(
        request,
        'tarj_viajeras/numero_parte_cliente.html',
        {'items': items, 'edit_item': edit_item, 'search_query': search_query}
    )


@login_required
@requiere_gestion_tarj_viajeras
def numero_parte_cliente_crear(request):

    if request.method == 'POST':
        descripcion = request.POST.get('descripcion', '').strip()

        if not descripcion:
            messages.error(request, 'La descripción es obligatoria.')
            return redirect('numero_parte_cliente')

        if NumeroParteCliente.objects.filter(
            descripcion__iexact=descripcion
        ).exists():
            messages.error(request, 'Ese número de parte ya existe.')
            return redirect('numero_parte_cliente')

        NumeroParteCliente.objects.create(descripcion=descripcion)
        messages.success(request, 'Número de parte creado correctamente.')

    return redirect('numero_parte_cliente')


@login_required
@requiere_gestion_tarj_viajeras
def numero_parte_cliente_editar(request, item_id):

    item = get_object_or_404(NumeroParteCliente, id_num_pcli=item_id)

    if request.method == 'POST':
        descripcion = request.POST.get('descripcion', '').strip()

        if not descripcion:
            messages.error(request, 'La descripción es obligatoria.')
            return redirect_edicion('numero_parte_cliente', item_id)

        if NumeroParteCliente.objects.filter(
            descripcion__iexact=descripcion
        ).exclude(id_num_pcli=item_id).exists():
            messages.error(request, 'Ese número de parte ya existe.')
            return redirect_edicion('numero_parte_cliente', item_id)

        item.descripcion = descripcion
        item.save()
        messages.success(request, 'Número de parte actualizado correctamente.')

    return redirect('numero_parte_cliente')


@login_required
@requiere_gestion_tarj_viajeras
def numero_parte_cliente_eliminar(request, item_id):

    if request.method == 'POST':
        item = get_object_or_404(NumeroParteCliente, id_num_pcli=item_id)
        try:
            item.delete()
            messages.success(request, 'Número de parte eliminado correctamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar porque está siendo utilizado.'
            )

    return redirect('numero_parte_cliente')


# =========================================================
# STATUS TARJETA
# =========================================================

@login_required
@requiere_gestion_tarj_viajeras
def status_tarjeta(request):

    search_query = request.GET.get('search', '').strip()
    items = StatusTar.objects.all().order_by('id_status')
    if search_query:
        items = items.filter(descripcion__icontains=search_query)

    edit_item = None
    edit_id = request.GET.get('edit_id')
    if edit_id and edit_id.isdigit():
        edit_item = get_object_or_404(StatusTar, id_status=edit_id)

    return render(
        request,
        'tarj_viajeras/status_tarjeta.html',
        {'items': items, 'edit_item': edit_item, 'search_query': search_query}
    )


@login_required
@requiere_gestion_tarj_viajeras
def status_tarjeta_crear(request):

    if request.method == 'POST':
        descripcion = request.POST.get('descripcion', '').strip()

        if not descripcion:
            messages.error(request, 'La descripción es obligatoria.')
            return redirect('status_tarjeta')

        if StatusTar.objects.filter(descripcion__iexact=descripcion).exists():
            messages.error(request, 'Ese estatus ya existe.')
            return redirect('status_tarjeta')

        StatusTar.objects.create(descripcion=descripcion)
        messages.success(request, 'Estatus creado correctamente.')

    return redirect('status_tarjeta')


@login_required
@requiere_gestion_tarj_viajeras
def status_tarjeta_editar(request, item_id):

    item = get_object_or_404(StatusTar, id_status=item_id)

    if request.method == 'POST':
        descripcion = request.POST.get('descripcion', '').strip()

        if not descripcion:
            messages.error(request, 'La descripción es obligatoria.')
            return redirect_edicion('status_tarjeta', item_id)

        if StatusTar.objects.filter(
            descripcion__iexact=descripcion
        ).exclude(id_status=item_id).exists():
            messages.error(request, 'Ese estatus ya existe.')
            return redirect_edicion('status_tarjeta', item_id)

        item.descripcion = descripcion
        item.save()
        messages.success(request, 'Estatus actualizado correctamente.')

    return redirect('status_tarjeta')


@login_required
@requiere_gestion_tarj_viajeras
def status_tarjeta_eliminar(request, item_id):

    if request.method == 'POST':
        item = get_object_or_404(StatusTar, id_status=item_id)
        try:
            item.delete()
            messages.success(request, 'Estatus eliminado correctamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar porque está siendo utilizado por una tarjeta viajera.'
            )

    return redirect('status_tarjeta')
@login_required
@requiere_gestion_tarj_viajeras
def status_tarjetas_pdf(request):
    estados=StatusTar.objects.all().order_by('id_status')

    response=HttpResponse(content_type='application/pdf')
    response['Content-Disposition']='inline; filename="codigos_estatus.pdf"'

    c=canvas.Canvas(response,pagesize=letter)
    pw,ph=letter

    c.setFont("Helvetica-Bold",18)
    c.drawCentredString(pw/2,ph-20*mm,"CÓDIGOS DE ESTATUS")

    c.setFont("Helvetica",9)
    c.drawCentredString(
        pw/2,ph-27*mm,
        "Tarjetas Viajeras - Escanear para cambiar estatus"
    )

    y=ph-48*mm

    for estado in estados:
        codigo=f"STATUS|{estado.id_status}"

        c.setFont("Helvetica-Bold",13)
        c.drawString(25*mm,y+7*mm,estado.descripcion)

        bc=code128.Code128(
            codigo,
            barHeight=15*mm,
            barWidth=.35*mm
        )
        bc.drawOn(c,80*mm,y)

        c.setFont("Helvetica",8)
        c.drawString(80*mm,y-4*mm,codigo)

        y-=30*mm

        if y<25*mm:
            c.showPage()
            y=ph-30*mm

    c.save()
    return response


# =========================================================
# ESCANER DE TARJETAS
# =========================================================

@login_required
@requiere_gestion_tarj_viajeras
def escaner_tarjetas(request):
    return render(
        request,
        'tarj_viajeras/escaner_tarjetas.html'
    )

@login_required
@requiere_gestion_tarj_viajeras
def cambiar_status_barcode(request):
    if request.method!='POST':
        return redirect('tarjetas_viajeras')

    codigo_tarjeta=request.POST.get('tarjeta','').strip()
    codigo_status=request.POST.get('status','').strip()

    try:
        orden,folio=codigo_tarjeta.split('|',1)
        prefijo,status_id=codigo_status.split('|',1)

        if prefijo.upper()!='STATUS':
            raise ValueError

        tarjeta=TarjetaViajera.objects.select_related(
            'produccion','status'
        ).get(
            produccion__numero_orden_trabajo__iexact=orden.strip(),
            numero_tarjeta=folio.strip()
        )

        nuevo_status=StatusTar.objects.get(
            id_status=int(status_id)
        )

        anterior=tarjeta.status.descripcion if tarjeta.status else 'SIN ESTATUS'

        tarjeta.status=nuevo_status
        tarjeta.save(update_fields=['status'])

        messages.success(
            request,
            f'Tarjeta {tarjeta.folio_completo}: {anterior} → {nuevo_status.descripcion}'
        )

    except ValueError:
        messages.error(request,'Código de barras inválido.')

    except TarjetaViajera.DoesNotExist:
        messages.error(request,'No se encontró la tarjeta.')

    except TarjetaViajera.MultipleObjectsReturned:
        messages.error(request,'Se encontró más de una tarjeta con ese código.')

    except StatusTar.DoesNotExist:
        messages.error(request,'El estatus escaneado no existe.')

    return redirect('tarjetas_viajeras')

# =========================================================
# TIPO DE ACERO
# =========================================================

@login_required
@requiere_admin_tarj_viajeras
def tipo_acero(request):

    search_query = request.GET.get('search', '').strip()
    items = TipoAcero.objects.all().order_by('especificacion')
    if search_query:
        items = items.filter(especificacion__icontains=search_query)

    edit_item = None
    edit_id = request.GET.get('edit_id')
    if edit_id and edit_id.isdigit():
        edit_item = get_object_or_404(TipoAcero, id_tipo_acero=edit_id)

    return render(
        request,
        'tarj_viajeras/tipo_acero.html',
        {'items': items, 'edit_item': edit_item, 'search_query': search_query}
    )


@login_required
@requiere_admin_tarj_viajeras
def tipo_acero_crear(request):

    if request.method == 'POST':
        especificacion = request.POST.get('especificacion', '').strip()

        if not especificacion:
            messages.error(request, 'La especificación es obligatoria.')
            return redirect('tarj_tipo_acero')

        if TipoAcero.objects.filter(especificacion__iexact=especificacion).exists():
            messages.error(request, 'Ese tipo de acero ya existe.')
            return redirect('tarj_tipo_acero')

        TipoAcero.objects.create(especificacion=especificacion)
        messages.success(request, 'Tipo de acero creado correctamente.')

    return redirect('tarj_tipo_acero')


@login_required
@requiere_admin_tarj_viajeras
def tipo_acero_editar(request, item_id):

    item = get_object_or_404(TipoAcero, id_tipo_acero=item_id)

    if request.method == 'POST':
        especificacion = request.POST.get('especificacion', '').strip()

        if not especificacion:
            messages.error(request, 'La especificación es obligatoria.')
            return redirect_edicion('tarj_tipo_acero', item_id)

        if TipoAcero.objects.filter(
            especificacion__iexact=especificacion
        ).exclude(id_tipo_acero=item_id).exists():
            messages.error(request, 'Ese tipo de acero ya existe.')
            return redirect_edicion('tarj_tipo_acero', item_id)

        item.especificacion = especificacion
        item.save()
        messages.success(request, 'Tipo de acero actualizado correctamente.')

    return redirect('tarj_tipo_acero')


@login_required
@requiere_admin_tarj_viajeras
def tipo_acero_eliminar(request, item_id):

    if request.method == 'POST':
        item = get_object_or_404(TipoAcero, id_tipo_acero=item_id)
        try:
            item.delete()
            messages.success(request, 'Tipo de acero eliminado correctamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar porque el tipo de acero está siendo utilizado.'
            )

    return redirect('tarj_tipo_acero')


# =========================================================
# TIPOS DE LAMINACIÓN
# =========================================================

@login_required
@requiere_admin_tarj_viajeras
def tipo_laminacion(request):

    search_query = request.GET.get('search', '').strip()
    items = TipoLaminacion.objects.all().order_by('especificacion')
    if search_query:
        items = items.filter(especificacion__icontains=search_query)

    edit_item = None
    edit_id = request.GET.get('edit_id')
    if edit_id and edit_id.isdigit():
        edit_item = get_object_or_404(TipoLaminacion, id_tipo_laminacion=edit_id)

    return render(
        request,
        'tarj_viajeras/tipo_laminacion.html',
        {'items': items, 'edit_item': edit_item, 'search_query': search_query}
    )


@login_required
@requiere_admin_tarj_viajeras
def tipo_laminacion_crear(request):

    if request.method == 'POST':
        especificacion = request.POST.get('especificacion', '').strip()

        if not especificacion:
            messages.error(request, 'La especificación es obligatoria.')
            return redirect('tarj_tipo_laminacion')

        if TipoLaminacion.objects.filter(especificacion__iexact=especificacion).exists():
            messages.error(request, 'Ese tipo de laminación ya existe.')
            return redirect('tarj_tipo_laminacion')

        TipoLaminacion.objects.create(especificacion=especificacion)
        messages.success(request, 'Tipo de laminación creado correctamente.')

    return redirect('tarj_tipo_laminacion')


@login_required
@requiere_admin_tarj_viajeras
def tipo_laminacion_editar(request, item_id):

    item = get_object_or_404(TipoLaminacion, id_tipo_laminacion=item_id)

    if request.method == 'POST':
        especificacion = request.POST.get('especificacion', '').strip()

        if not especificacion:
            messages.error(request, 'La especificación es obligatoria.')
            return redirect_edicion('tarj_tipo_laminacion', item_id)

        if TipoLaminacion.objects.filter(
            especificacion__iexact=especificacion
        ).exclude(id_tipo_laminacion=item_id).exists():
            messages.error(request, 'Ese tipo de laminación ya existe.')
            return redirect_edicion('tarj_tipo_laminacion', item_id)

        item.especificacion = especificacion
        item.save()
        messages.success(request, 'Tipo de laminación actualizado correctamente.')

    return redirect('tarj_tipo_laminacion')


@login_required
@requiere_admin_tarj_viajeras
def tipo_laminacion_eliminar(request, item_id):

    if request.method == 'POST':
        item = get_object_or_404(TipoLaminacion, id_tipo_laminacion=item_id)
        try:
            item.delete()
            messages.success(request, 'Tipo de laminación eliminado correctamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar porque el tipo de laminación está siendo utilizado.'
            )

    return redirect('tarj_tipo_laminacion')


# =========================================================
# EXCEL
# =========================================================

@login_required
@requiere_gestion_tarj_viajeras
def tarj_viajeras_excel(request):

    return render(
        request,
        'tarj_viajeras/tarj_viajeras_excel.html'
    )

def _texto_pdf(v):
    return "" if v is None else str(v)

def _dibujar_tarjeta_pdf(c,t,x,y,w,h):
    import os
    from django.conf import settings
    p=t.produccion
    m=5*mm
    top=y+h
    c.setLineWidth(.45)

    # ENCABEZADO
    c.setFont("Helvetica-Bold",13)
    c.drawString(x+m,top-7*mm,"Tarjeta viajera")
    c.setFont("Helvetica",4)
    c.drawRightString(x+w-24*mm,top-3*mm,"PR0200-F-05")
    c.drawRightString(x+w-24*mm,top-5*mm,"Rev. 03")
    c.drawRightString(x+w-24*mm,top-7*mm,"21.07.20")

    def campo(label,valor,lx,vy,lw=19*mm,vw=28*mm):
        c.setFont("Helvetica-Bold",5.5)
        c.drawRightString(lx+lw-1.5*mm,vy+1.8*mm,label)
        c.rect(lx+lw,vy,vw,5.5*mm)

        texto=_texto_pdf(valor)[:32]
        tam=6.5
        ancho_max=vw-2*mm

        while c.stringWidth(texto,"Helvetica",tam)>ancho_max and tam>4:
            tam-=0.2

        c.setFont("Helvetica",tam)
        c.drawString(lx+lw+mm,vy+1.7*mm,texto)

    # DATOS SUPERIORES
    sy=top-14*mm
    c1=x+15*mm
    c2=x+76*mm
    c3=x+122*mm

    campo("LOTE",p.lote,c1,sy)
    campo("MATERIAL",p.material,c1,sy-6.5*mm)
    campo("ESPESOR",p.espesor,c1,sy-13*mm)
    campo("ID",t.folio_completo,c2,sy)
    campo("OC",p.numero_orden_compra,c2,sy-6.5*mm)
    campo("CLIENTE",p.cliente.nombre,c2,sy-13*mm)
    campo("LAMINACIÓN",p.laminacion,c3,sy,24*mm,27*mm)
    campo("# DE PARTE CLIENTE",p.numero_parte_cliente,c3,sy-6.5*mm,24*mm,27*mm)
    campo("TARA",t.tara,c3,sy-13*mm,24*mm,27*mm)

    # POSICIONES
    p1=x-3*mm
    p2=x+68*mm
    p3=x+120*mm
    inicio=top-39*mm
    paso=5.3*mm

    # ================= TROQUELADO =================
    # ================= TROQUELADO =================
    lw1=25*mm
    tw=42*mm
    tx=p1+lw1
    col=tw/3

    c.setFont("Helvetica-Bold",6.5)
    c.drawCentredString(tx+tw/2,inicio+6*mm,"TROQUELADO")

    def fila_troq(fy,label,valor="",tipo="triple"):
        c.setFont("Helvetica",5.2)
        c.drawRightString(tx-1.2*mm,fy+1.5*mm,label)

        if tipo=="completa":
            c.rect(tx,fy,tw,5*mm)

        elif tipo=="triple":
            c.rect(tx,fy,col,5*mm)
            c.rect(tx+col,fy,col,5*mm)
            c.rect(tx+col*2,fy,col,5*mm)

        elif tipo=="desde_col2_doble":
            c.rect(tx+col,fy,col,5*mm)
            c.rect(tx+col*2,fy,col,5*mm)

        elif tipo=="desde_col2_unica":
            c.rect(tx+col,fy,col*2,5*mm)

        if valor not in ("",None):
            c.setFont("Helvetica",5)
            texto=_texto_pdf(valor)[:18]

            if tipo.startswith("desde_col2"):
                c.drawString(tx+col+mm,fy+1.5*mm,texto)
            else:
                c.drawString(tx+mm,fy+1.5*mm,texto)

    troq=[
        ("NO. ORDEN",p.numero_orden_trabajo,"completa"),
        ("FECHA","","triple"),
        ("TURNO","","triple"),
        ("PRENSISTA","","triple"),
        ("ALAMBRES","","triple"),
        ("TOTAL DE ALAMBRES",t.numero_alambres,"desde_col2_doble"),
        ("KGS BRUTOS",t.peso_kg,"desde_col2_unica"),
        ("KGS NETOS","","desde_col2_unica")
    ]

    for i,(label,valor,tipo) in enumerate(troq):
        fila_troq(inicio-i*paso,label,valor,tipo)
    # ================= HORNEADO =================
    lw2=25*mm
    hw=31*mm
    hx=p2+lw2
    mitad=hw/2

    c.setFont("Helvetica-Bold",6.5)
    c.drawCentredString(hx+hw/2,inicio+6*mm,"HORNEADO")

    def fila_h(fy,label,valor="",doble=False):
        c.setFont("Helvetica",5.2)
        c.drawRightString(hx-1.2*mm,fy+1.5*mm,label)
        if doble:
            c.rect(hx,fy,mitad,5*mm)
            c.rect(hx+mitad,fy,mitad,5*mm)
        else:
            c.rect(hx,fy,hw,5*mm)
        if valor not in ("",None):
            c.setFont("Helvetica",5)
            c.drawString(hx+mm,fy+1.5*mm,_texto_pdf(valor)[:18])

    fila_h(inicio,"NO. ORDEN",p.numero_orden_trabajo)

    # HORNEADO / P1 / P2
    fy=inicio-paso
    c.setFont("Helvetica",5.2)
    c.drawRightString(hx-1.2*mm,fy+1.5*mm,"HORNEADO")

    libre=17*mm
    pbox=(hw-libre)/2

    c.rect(hx,fy,libre,5*mm)
    c.rect(hx+libre,fy,pbox,5*mm)
    c.rect(hx+libre+pbox,fy,pbox,5*mm)

    c.setFont("Helvetica-Bold",5.5)
    c.drawCentredString(hx+libre+pbox/2,fy+1.5*mm,"P1")
    c.drawCentredString(hx+libre+pbox+pbox/2,fy+1.5*mm,"P2")

    horn=[
        ("FECHA","",True),
        ("HORA","",True),
        ("TURNO","",True),
        ("HORNERO","",True),
        ("ALAMBRES","",False),
        ("TOTAL DE ALAMBRES",t.numero_alambres,False),
        ("KGS BRUTOS",t.peso_kg,False),
        ("KGS NETOS","",False)
    ]

    for i,(a,b,doble) in enumerate(horn,start=2):
        fila_h(inicio-i*paso,a,b,doble)

    # ================= EMPAQUE =================
    lw3=25*mm
    ew=28*mm
    ex=p3+lw3

    c.setFont("Helvetica-Bold",6.5)
    c.drawCentredString(ex+ew/2,inicio+6*mm,"EMPAQUE")

    def fila_emp(fy,label,valor=""):
        c.setFont("Helvetica",5.2)
        c.drawRightString(ex-1.2*mm,fy+1.5*mm,label)
        c.rect(ex,fy,ew,5*mm)
        if valor not in ("",None):
            c.setFont("Helvetica",5)
            c.drawString(ex+mm,fy+1.5*mm,_texto_pdf(valor)[:18])

    emp=[
        ("NO. ORDEN",p.numero_orden_trabajo),
        ("FECHA",""),
        ("HORA",""),
        ("TURNO",""),
        ("EMPACADOR",""),
        ("ALAMBRES",""),
        ("TOTAL DE ALAMBRES",t.numero_alambres),
        ("KGS BRUTOS",t.peso_kg),
        ("KGS NETOS","")
    ]

    for i,(a,b) in enumerate(emp):
        fila_emp(inicio-i*paso,a,b)

    # LOGO
    logo=os.path.join(settings.BASE_DIR,"media","logo.png")
    logo_x=p1
    logo_y=y+3*mm
    logo_w=32*mm
    logo_h=10*mm

    if os.path.exists(logo):
        c.drawImage(
            logo,logo_x,logo_y,
            width=logo_w,height=logo_h,
            preserveAspectRatio=True,
            anchor="c",mask="auto"
        )

    # BARCODE
    codigo=f"{p.numero_orden_trabajo}|{t.folio_completo}"
    bc=code128.Code128(
        codigo,
        barHeight=17*mm,
        barWidth=.21*mm
    )

    bx=x+w-9*mm
    by=top-53*mm

    c.saveState()
    c.translate(bx,by)
    c.rotate(90)
    bc.drawOn(c,0,0)
    c.restoreState()

    # TEXTO BARCODE
    c.saveState()
    c.translate(x+w-5*mm,by)
    c.rotate(90)
    c.setFont("Helvetica",4.5)
    c.drawCentredString(10.5*mm,0,codigo)
    c.restoreState()

def _generar_pdf_tarjetas(tarjetas):
    response=HttpResponse(content_type="application/pdf")
    response["Content-Disposition"]='inline; filename="tarjetas_viajeras.pdf"'
    c=canvas.Canvas(response,pagesize=letter)
    pw,ph=letter
    mx,my,gap=5*mm,5*mm,3*mm
    w=pw-2*mx
    h=(ph-2*my-2*gap)/3
    for i,t in enumerate(tarjetas):
        pos=i%3
        if pos==0 and i>0: c.showPage()
        y=ph-my-h-pos*(h+gap)
        _dibujar_tarjeta_pdf(c,t,mx,y,w,h)
    c.save()
    return response

@login_required
@requiere_gestion_tarj_viajeras
def tarjeta_viajera_pdf(request,item_id):
    t=get_object_or_404(_tarjetas_base_qs(),id_tarjeta=item_id)
    return _generar_pdf_tarjetas([t])

@login_required
@requiere_gestion_tarj_viajeras
def tarjetas_viajeras_pdf(request):
    pid=request.GET.get("produccion","").strip()
    if not pid.isdigit():
        messages.error(request,"Selecciona una orden de trabajo.")
        return redirect("tarjetas_viajeras_imprimir")
    tarjetas=list(_tarjetas_base_qs().filter(produccion__id_produccion=int(pid)).order_by("numero_tarjeta","sufijo"))
    if not tarjetas:
        messages.error(request,"La orden seleccionada no tiene tarjetas.")
        return redirect("tarjetas_viajeras_imprimir")
    return _generar_pdf_tarjetas(tarjetas)
# =========================================================
# UTILIDADES
# =========================================================

@login_required
@requiere_gestion_tarj_viajeras
def get_folio(request):

    ultimo = TarjetaViajera.objects.order_by('-numero_tarjeta').first()
    siguiente = ultimo.numero_tarjeta + 1 if ultimo else 1

    return render(
        request,
        'tarj_viajeras/get_folio.html',
        {'siguiente_folio': siguiente}
    )


@login_required
@requiere_gestion_tarj_viajeras
def get_produccion(request, item_id):

    produccion_item = get_object_or_404(
        Produccion.objects.select_related(
            'cliente',
            'material',
            'espesor',
                'laminacion',
            'numero_parte_cliente'
        ),
        id_produccion=item_id
    )

    return render(
        request,
        'tarj_viajeras/get_produccion.html',
        {'produccion': produccion_item}
    )


# =========================================================
# ACCIONES GENERALES
# =========================================================

@login_required
@requiere_gestion_tarj_viajeras
def tarj_viajeras_actions(request, section, action_type, item_id=None):

    return redirect('tarj_viajeras')