from functools import wraps
import re
import unicodedata

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

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
from django.utils import timezone


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128
from reportlab.lib.utils import simpleSplit

from .models import (
    Espesor,
    NumeroParteCliente,
    ConfiguracionPiezasAlambre,
    PROCESOS_PRODUCCION,
    StatusTar,
    ProcesoTarjeta,
    Produccion,
    TarjetaViajera,
    ReasignacionTarjeta,
)

from apps.clientes.models import Cliente
from apps.scrap.models import TipoAcero
from apps.liberaciones.models import TipoLaminacion
from apps.usuarios.permissions import tiene_permiso
from .services.produccion import (
    ProduccionInvalida as _ProduccionInvalida,
    actualizar_produccion as _actualizar_produccion,
    configuracion_de_produccion as _configuracion_de_produccion,
    crear_produccion as _crear_produccion,
    crear_subvariante as _crear_subvariante,
    datos_produccion as _datos_produccion,
    numero_orden_sin_prefijo as _numero_orden_sin_prefijo,
    produccion_completa as _produccion_completa,
)
from .services.formularios import (
    datos_configuracion_piezas as _datos_configuracion_piezas,
    datos_tarjeta as _datos_tarjeta,
    validar_datos_configuracion_piezas as _validar_datos_configuracion_piezas,
)
from .services.estatus import (
    separar_codigo_tarjeta as _separar_codigo_tarjeta,
)
from .services.procesos import (
    actualizar_proceso as _actualizar_proceso,
    crear_proceso as _crear_proceso,
    estatus_ids_del_formulario as _estatus_ids_del_formulario,
    estatus_permitido as _estatus_permitido,
)
from .estatus_views import (
    cambiar_status_barcode,
    escaner_tarjetas,
    status_tarjeta,
    status_tarjeta_crear,
    status_tarjeta_editar,
    status_tarjeta_eliminar,
    status_tarjetas_pdf,
)


# =========================================================
# PERMISOS
# =========================================================

def usuario_puede_ver_tarj_viajeras(user):
    return tiene_permiso(
        user,
        'tarj_viajeras.view_tarjetaviajera',
    )


def usuario_puede_gestionar_tarj_viajeras(user):
    return tiene_permiso(
        user,
        'tarj_viajeras.change_tarjetaviajera',
    )


def usuario_puede_actualizar_tarj_viajeras(user):
    return any(tiene_permiso(user, permiso) for permiso in (
        'tarj_viajeras.change_tarjetaviajera',
        'tarj_viajeras.update_status_tarjetaviajera',
        'tarj_viajeras.update_measurements_tarjetaviajera',
    ))


def usuario_puede_actualizar_datos_tarj_viajeras(user):
    return tiene_permiso(user, 'tarj_viajeras.update_measurements_tarjetaviajera')


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
        if not usuario_puede_gestionar_tarj_viajeras(request.user):
            messages.error(
                request,
                'Tu rol no permite gestionar Tarjetas Viajeras.'
            )
            return redirect('tarj_viajeras')
        return view(request, *args, **kwargs)
    return wrapped


def requiere_actualizar_tarj_viajera(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not usuario_puede_actualizar_tarj_viajeras(request.user):
            messages.error(
                request,
                'Tu rol no permite actualizar Tarjetas Viajeras.'
            )
            return redirect('tarj_viajeras')
        return view(request, *args, **kwargs)
    return wrapped


def usuario_puede_imprimir_tarj_viajeras(user):
    return tiene_permiso(user, 'tarj_viajeras.print_tarjetaviajera')


def usuario_puede_ver_tipo_laminacion(user):
    return tiene_permiso(user, 'liberaciones.view_tipolaminacion')


def usuario_puede(user, permiso):
    """Indica si el usuario tiene un permiso puntual del submódulo."""
    return tiene_permiso(user, permiso)


def requiere_permiso_tipo_laminacion(permiso):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not tiene_permiso(request.user, permiso):
                messages.error(
                    request,
                    'No tienes permisos para realizar esta acción sobre tipos de laminación.'
                )
                return redirect('tarj_viajeras')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def requiere_permiso_tarj_viajeras(permiso):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not tiene_permiso(request.user, permiso):
                messages.error(
                    request,
                    'No tienes permisos para acceder a esta opción.'
                )
                return redirect('tarj_viajeras')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def requiere_impresion_tarj_viajeras(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not usuario_puede_imprimir_tarj_viajeras(request.user):
            messages.error(
                request,
                'No tienes permisos para imprimir tarjetas viajeras o etiquetas.'
            )
            return redirect('tarj_viajeras')
        return view(request, *args, **kwargs)
    return wrapped


def requiere_admin_tarj_viajeras(view):
    """Restringe la administración del módulo a ADMIN y ENCARGADO."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        u = request.user
        if not usuario_puede_gestionar_tarj_viajeras(u):
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
        'tarj_viajeras/tarj_viajeras_dashboard.html',
        {
            'puede_ver_tarj_viajeras':
                usuario_puede_ver_tarj_viajeras(request.user),
            'puede_gestionar_tarj_viajeras':
                usuario_puede_gestionar_tarj_viajeras(request.user),
            'puede_imprimir_tarj_viajeras':
                usuario_puede_imprimir_tarj_viajeras(request.user),
            'puede_ver_tipo_laminacion':
                usuario_puede_ver_tipo_laminacion(request.user),
            'puede_ver_produccion':
                tiene_permiso(request.user, 'tarj_viajeras.view_produccion'),
            'puede_ver_configuracion_piezas':
                tiene_permiso(request.user, 'tarj_viajeras.view_configuracionpiezasalambre'),
            'puede_ver_espesores':
                tiene_permiso(request.user, 'tarj_viajeras.view_espesor'),
            'puede_ver_numero_parte':
                tiene_permiso(request.user, 'tarj_viajeras.view_numeropartecliente'),
            'puede_ver_status_tarjeta':
                tiene_permiso(request.user, 'tarj_viajeras.view_statustar'),
            'puede_ver_tipo_acero':
                tiene_permiso(request.user, 'scrap.view_tipoacero'),
        }
    )


# =========================================================
# PRODUCCIÓN
# =========================================================


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.view_produccion')
def obtener_combinaciones_produccion(request):
    proceso = request.GET.get('proceso', '').strip()
    cliente = request.GET.get('cliente', '').strip()

    if proceso not in dict(PROCESOS_PRODUCCION) or not cliente.isdigit():
        return JsonResponse({'combinaciones': []})

    configuraciones = ConfiguracionPiezasAlambre.objects.filter(
        proceso=proceso,
        cliente_id=cliente
    ).select_related(
        'numero_parte_cliente',
        'laminacion'
    ).order_by(
        'numero_parte_cliente__descripcion',
        'laminacion__especificacion'
    )

    datos = [{
        'parte_id': c.numero_parte_cliente_id,
        'parte': c.numero_parte_cliente.descripcion,
        'laminacion_id': c.laminacion_id,
        'laminacion': c.laminacion.especificacion,
        'piezas_por_alambre': c.piezas_por_alambre
    } for c in configuraciones]

    return JsonResponse({'combinaciones': datos})

@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.view_produccion')
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
    if (
        edit_id and edit_id.isdigit()
        and usuario_puede(request.user, 'tarj_viajeras.change_produccion')
    ):
        edit_item = get_object_or_404(Produccion, id_produccion=edit_id)

    return render(
        request,
        'tarj_viajeras/produccion.html',
        {
            'page_obj': page_obj,
            'search_query': search_query,
            'edit_item': edit_item,
            'edit_numero_orden': (
                _numero_orden_sin_prefijo(
                    edit_item.numero_orden_trabajo,
                    edit_item.proceso
                )
                if edit_item else ''
            ),
            'clientes': Cliente.objects.filter(activo=True).order_by('nombre'),
            'materiales': TipoAcero.objects.all().order_by('especificacion'),
            'espesores': Espesor.objects.all().order_by('espesor'),
            'laminaciones': TipoLaminacion.objects.all().order_by('especificacion'),
            'numeros_parte': NumeroParteCliente.objects.all().order_by('descripcion'),
            'procesos': PROCESOS_PRODUCCION,
            'configuraciones':ConfiguracionPiezasAlambre.objects.select_related('cliente','numero_parte_cliente','laminacion').all(),
            'puede_agregar_produccion': usuario_puede(request.user, 'tarj_viajeras.add_produccion'),
            'puede_editar_produccion': usuario_puede(request.user, 'tarj_viajeras.change_produccion'),
            'puede_eliminar_produccion': usuario_puede(request.user, 'tarj_viajeras.delete_produccion'),
        }
    )


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.add_produccion')
def produccion_crear(request):

    if request.method != 'POST':
        return redirect('produccion')
    try:
        _crear_produccion(_datos_produccion(request.POST))
    except _ProduccionInvalida as error:
        messages.error(request, str(error))
        return redirect('produccion')
    messages.success(request, 'Producción creada correctamente.')
    return redirect('produccion')


def produccion_subvariante_crear(request,item_id):
    if request.method != 'POST':
        return redirect('produccion')
    base = get_object_or_404(Produccion, id_produccion=item_id)
    base = base.subvariante_de or base
    cliente_id = request.POST.get('id_cliente', '').strip()
    parte_id = request.POST.get('id_num_pcli', '').strip()
    laminacion_id = request.POST.get('id_laminacion', '').strip()
    if not all(x.isdigit() for x in [cliente_id, parte_id, laminacion_id]):
        messages.error(request, 'Selecciona cliente, número de parte y laminación.')
        return redirect('produccion')
    try:
        _crear_subvariante(base, cliente_id, parte_id, laminacion_id)
    except _ProduccionInvalida as error:
        messages.error(request, str(error))
        return redirect('produccion')
    messages.success(request, 'Subvariante creada correctamente.')
    return redirect('produccion')


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_produccion')
def produccion_editar(request, item_id):
    if request.method != 'POST':
        return redirect_edicion('produccion', item_id)
    item = get_object_or_404(Produccion, id_produccion=item_id)
    try:
        _actualizar_produccion(item, _datos_produccion(request.POST))
    except _ProduccionInvalida as error:
        messages.error(request, str(error))
        return redirect_edicion('produccion', item_id)
    messages.success(request, 'Producción actualizada correctamente.')
    return redirect('produccion')


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.delete_produccion')
def produccion_eliminar(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Produccion, id_produccion=item_id)
        try:
            item.delete()
            messages.success(request, 'Producción eliminada correctamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar esta producción porque tiene tarjetas '
                'o subvariantes relacionadas.'
            )
    return redirect('produccion')


@requiere_impresion_tarj_viajeras
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

@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.view_reasignaciontarjeta')
def reasignaciones_tarjetas(request):
    search_query = request.GET.get('search', '').strip()
    reasignaciones = ReasignacionTarjeta.objects.select_related(
        'tarjeta',
        'produccion_origen__cliente',
        'produccion_origen__numero_parte_cliente',
        'produccion_destino__cliente',
        'produccion_destino__numero_parte_cliente'
    ).order_by('-fecha', '-pk')

    if search_query:
        filtros = (
            Q(motivo__icontains=search_query) |
            Q(tarjeta__sufijo__icontains=search_query) |
            Q(produccion_origen__numero_orden_trabajo__icontains=search_query) |
            Q(produccion_origen__lote__icontains=search_query) |
            Q(produccion_origen__cliente__nombre__icontains=search_query) |
            Q(produccion_origen__numero_parte_cliente__descripcion__icontains=search_query) |
            Q(produccion_destino__numero_orden_trabajo__icontains=search_query) |
            Q(produccion_destino__lote__icontains=search_query) |
            Q(produccion_destino__cliente__nombre__icontains=search_query) |
            Q(produccion_destino__numero_parte_cliente__descripcion__icontains=search_query)
        )
        if search_query.isdigit():
            filtros |= Q(tarjeta__numero_tarjeta__exact=int(search_query))
        reasignaciones = reasignaciones.filter(filtros)

    page_obj = Paginator(reasignaciones, 20).get_page(
        request.GET.get('page')
    )
    return render(
        request,
        'tarj_viajeras/reasignaciones_tarjetas.html',
        {
            'page_obj': page_obj,
            'search_query': search_query,
        }
    )





def _codigo_barras(tarjeta):
    """Valor que se codifica en el código de barras: NUMERO-SUFIJO."""
    base = str(tarjeta.numero_tarjeta)
    return f'{base}-{tarjeta.sufijo}' if tarjeta.sufijo else base


def _codigo_barras_etiqueta(tarjeta):
    """Genera el código legible para la etiqueta según el formato de la tarjeta."""
    if tarjeta.sufijo:
        return f'{tarjeta.produccion.numero_orden_trabajo}|{tarjeta.numero_tarjeta}-{tarjeta.sufijo}'
    return f'{tarjeta.produccion.numero_orden_trabajo}|{tarjeta.numero_tarjeta}'


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
@requiere_impresion_tarj_viajeras
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
@requiere_impresion_tarj_viajeras
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


@login_required
@requiere_impresion_tarj_viajeras
def tarjeta_viajera_etiqueta(request, item_id=None):
    """Genera una etiqueta de impresión para una tarjeta viajera."""
    tarjeta = None

    if item_id is not None:
        tarjeta = get_object_or_404(
            _tarjetas_base_qs(),
            id_tarjeta=item_id,
        )
    else:
        codigo = request.GET.get('codigo', '').strip()
        if not codigo:
            messages.error(request, 'Debe escanear o indicar una tarjeta viajera.')
            return redirect('tarj_viajeras')

        codigo_separado = _separar_codigo_tarjeta(codigo)
        if codigo_separado is None:
            messages.error(request, 'El código escaneado no es válido.')
            return redirect('tarj_viajeras')

        orden, numero_tarjeta, sufijo = codigo_separado
        filtros = {
            'numero_tarjeta': numero_tarjeta,
            'sufijo': sufijo,
        }
        filtros['produccion__numero_orden_trabajo__iexact'] = orden
        tarjeta = _tarjetas_base_qs().filter(**filtros).first()
        if tarjeta is None:
            messages.error(request, 'No se encontró una tarjeta con ese código.')
            return redirect('tarj_viajeras')

    piezas = 0
    if tarjeta.numero_alambres is not None and tarjeta.piezas_por_alambre is not None:
        piezas = int(tarjeta.numero_alambres) * int(tarjeta.piezas_por_alambre)

    codigo_etiqueta = _codigo_barras_etiqueta(tarjeta)
    page_size = (152 * mm, 101 * mm)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="etiqueta_tarjeta_{tarjeta.folio_completo}.pdf"'
    )
    pdf = canvas.Canvas(response, pagesize=page_size)
    width, height = page_size
    margin_x = 7 * mm
    content_width = width - 2 * margin_x
    right_x = width - margin_x

    pdf.setFillColorRGB(0.07, 0.09, 0.12)
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawRightString(
        right_x,
        height - 8 * mm,
        timezone.localdate().strftime('%d/%m/%Y'),
    )
    pdf.setStrokeColorRGB(0.07, 0.09, 0.12)
    pdf.setLineWidth(1)
    pdf.line(margin_x, height - 10 * mm, right_x, height - 10 * mm)

    fields = [
        ('# parte VCL', tarjeta.produccion.laminacion.especificacion),
        ('# parte cliente', tarjeta.produccion.numero_parte_cliente.descripcion),
        ('Lote', tarjeta.produccion.lote),
        ('Piezas', piezas),
        ('Peso lbs', tarjeta.peso_lbs or '0.00'),
        ('Peso kgs', tarjeta.peso_kg or '0.00'),
        ('# Tarima', tarjeta.folio_completo),
        ('Alambres', tarjeta.numero_alambres or 0),
        ('# Orden de compra', tarjeta.produccion.numero_orden_compra or '-'),
    ]
    column_gap = 8 * mm
    column_width = (content_width - column_gap) / 2
    row_height = 13 * mm
    first_row_y = height - 16 * mm

    for index, (label, value) in enumerate(fields):
        if index == 8:
            x = margin_x
            y = first_row_y - 4 * row_height
            field_width = content_width
        else:
            row = index // 2
            column = index % 2
            x = margin_x + column * (column_width + column_gap)
            y = first_row_y - row * row_height
            field_width = column_width

        pdf.setFillColorRGB(0.28, 0.32, 0.37)
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawString(x, y, label.upper())
        pdf.setFillColorRGB(0.07, 0.09, 0.12)
        value_lines = simpleSplit(
            str(value),
            'Helvetica-Bold',
            13,
            field_width,
        )
        for line_number, line in enumerate(value_lines[:2]):
            pdf.setFont('Helvetica-Bold', 13)
            pdf.drawString(x, y - (5 * mm) - line_number * (4.5 * mm), line)

    pdf.setStrokeColorRGB(0.07, 0.09, 0.12)
    pdf.line(margin_x, 24 * mm, right_x, 24 * mm)
    barcode_code = code128.Code128(
        codigo_etiqueta,
        barHeight=13 * mm,
        barWidth=0.25 * mm,
        humanReadable=False,
    )
    barcode_code.drawOn(pdf, margin_x, 7 * mm)
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(margin_x + 60 * mm, 13 * mm, codigo_etiqueta)
    pdf.showPage()
    pdf.save()
    return response

# =========================================================
# EXCEL
# =========================================================

@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.view_produccion')
def tarj_viajeras_excel(request):

    return render(
        request,
        'tarj_viajeras/tarj_viajeras_excel.html'
    )

def _texto_pdf(v):
    return "" if v is None else str(v)


def _separar_codigo_tarjeta_legacy(codigo):
    codigo = unicodedata.normalize('NFKC', codigo or '')
    codigo = ''.join(caracter for caracter in codigo if caracter.isprintable())
    codigo = codigo.strip().replace('Ñ', ':').replace('ñ', ':')

    # Algunos lectores agregan el identificador AIM de Code 128.
    if codigo.startswith(']C1'):
        codigo = codigo[3:]

    codigo_partido = re.fullmatch(r'(.*?)(\d+)(?:-([A-Za-z]))?', codigo)
    if not codigo_partido:
        return None

    orden = codigo_partido.group(1).rstrip(' \t|¦¬:Çç')
    orden = orden or None
    sufijo = codigo_partido.group(3)
    return (
        orden,
        int(codigo_partido.group(2)),
        sufijo.upper() if sufijo else None,
    )


def _dibujar_tarjeta_pdf(c,t,x,y,w,h):
    import os
    from django.conf import settings
    p=t.produccion
    m=5*mm
    top=y+h
    c.setLineWidth(.45)

    # ENCABEZADO
    c.setFont("Helvetica-Bold",15)
    c.drawString(x+m,top-7*mm,"Tarjeta viajera")
    c.setFont("Helvetica",5)
    c.drawRightString(x+w-24*mm,top-3*mm,"PR0200-F-05")
    c.drawRightString(x+w-24*mm,top-5*mm,"Rev. 03")
    c.drawRightString(x+w-24*mm,top-7*mm,"21.07.20")

    def campo(label,valor,lx,vy,lw=19*mm,vw=40*mm):
        c.setFont("Helvetica-Bold",6.5)
        c.drawRightString(lx+lw-1.5*mm,vy+2*mm,label)
        c.rect(lx+lw,vy,vw,6*mm)

        texto=_texto_pdf(valor)[:32]
        tam=8
        ancho_max=vw-2*mm

        while c.stringWidth(texto,"Helvetica",tam)>ancho_max and tam>4:
            tam-=0.2

        c.setFont("Helvetica",tam)
        c.drawString(lx+lw+mm,vy+1.8*mm,texto)

    # DATOS SUPERIORES
    sy=top-14*mm
    c1=x+12*mm
    c2=x+65*mm
    c3=x+132*mm

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
    p1=x-5*mm
    p2=x+66*mm
    p3=x+126*mm
    inicio=top-39*mm
    paso=5.3*mm

    # ================= TROQUELADO =================
    # ================= TROQUELADO =================
    lw1=25*mm
    tw=46*mm
    tx=p1+lw1
    col=tw/3

    c.setFont("Helvetica-Bold",8)
    c.drawCentredString(tx+tw/2,inicio+6*mm,"TROQUELADO")

    def fila_troq(fy,label,valor="",tipo="triple"):
        c.setFont("Helvetica",6.2)
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
            c.setFont("Helvetica",6.2)
            texto=_texto_pdf(valor)[:18]

            if tipo.startswith("desde_col2"):
                c.drawString(tx+col+mm,fy+1.3*mm,texto)
            else:
                c.drawString(tx+mm,fy+1.3*mm,texto)

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
    hw=35*mm
    hx=p2+lw2
    mitad=hw/2

    c.setFont("Helvetica-Bold",8)
    c.drawCentredString(hx+hw/2,inicio+6*mm,"HORNEADO")

    def fila_h(fy,label,valor="",doble=False):
        c.setFont("Helvetica",6.2)
        c.drawRightString(hx-1.2*mm,fy+1.5*mm,label)
        if doble:
            c.rect(hx,fy,mitad,5*mm)
            c.rect(hx+mitad,fy,mitad,5*mm)
        else:
            c.rect(hx,fy,hw,5*mm)
        if valor not in ("",None):
            c.setFont("Helvetica",6.2)
            c.drawString(hx+mm,fy+1.3*mm,_texto_pdf(valor)[:18])

    fila_h(inicio,"NO. ORDEN",p.numero_orden_trabajo)

    # HORNEADO / P1 / P2
    fy=inicio-paso
    libre=17*mm
    pbox=(hw-libre)/2

    c.rect(hx,fy,libre,5*mm)
    c.rect(hx+libre,fy,pbox,5*mm)
    c.rect(hx+libre+pbox,fy,pbox,5*mm)

    c.setFont("Helvetica-Bold",6.5)
    c.drawCentredString(hx+libre+pbox/2,fy+1.3*mm,"P1")
    c.drawCentredString(hx+libre+pbox+pbox/2,fy+1.3*mm,"P2")

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
    ew=33*mm
    ex=p3+lw3

    c.setFont("Helvetica-Bold",8)
    c.drawCentredString(ex+ew/2,inicio+6*mm,"EMPAQUE")

    def fila_emp(fy,label,valor=""):
        c.setFont("Helvetica",6.2)
        c.drawRightString(ex-1.2*mm,fy+1.5*mm,label)
        c.rect(ex,fy,ew,5*mm)
        if valor not in ("",None):
            c.setFont("Helvetica",6.2)
            c.drawString(ex+mm,fy+1.3*mm,_texto_pdf(valor)[:18])

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
        barHeight=13*mm,
        barWidth=.21*mm
    )

    bx=x+w-3*mm
    by=top-60*mm

    c.saveState()
    c.translate(bx,by)
    c.rotate(90)
    bc.drawOn(c,0,0)
    c.restoreState()

    # TEXTO BARCODE
    c.saveState()
    c.translate(x+w-1*mm,by)
    c.rotate(90)
    c.setFont("Helvetica",5.5)
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
@requiere_impresion_tarj_viajeras
def tarjeta_viajera_pdf(request,item_id):
    t=get_object_or_404(_tarjetas_base_qs(),id_tarjeta=item_id)
    return _generar_pdf_tarjetas([t])

@login_required
@requiere_impresion_tarj_viajeras
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


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_tarjetaviajera')
def procesos_tarjeta(request):
    search_query = request.GET.get('search', '').strip()
    procesos = ProcesoTarjeta.objects.prefetch_related('estatus_proceso__status').all()
    if search_query:
        procesos = procesos.filter(
            Q(nombre__icontains=search_query) |
            Q(descripcion__icontains=search_query) |
            Q(estatus_proceso__status__descripcion__icontains=search_query)
        ).distinct()
    edit_id = request.GET.get('edit_id')
    edit_item = get_object_or_404(ProcesoTarjeta, pk=edit_id) if edit_id and edit_id.isdigit() else None
    return render(request, 'tarj_viajeras/procesos_tarjeta.html', {
        'procesos': procesos,
        'edit_item': edit_item,
        'estatus': StatusTar.objects.all().order_by('descripcion'),
        'search_query': search_query,
        'puede_editar_proceso': True,
        'puede_eliminar_proceso': True,
    })


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_tarjetaviajera')
def proceso_tarjeta_crear(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del proceso es obligatorio.')
        elif ProcesoTarjeta.objects.filter(nombre__iexact=nombre).exists():
            messages.error(request, 'Ese proceso ya existe.')
        else:
            _crear_proceso(
                nombre,
                request.POST.get('descripcion', '').strip(),
                _estatus_ids_del_formulario(request.POST),
            )
            messages.success(request, 'Proceso creado correctamente.')
    return redirect('procesos_tarjeta')


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_tarjetaviajera')
def proceso_tarjeta_editar(request, item_id):
    proceso = get_object_or_404(ProcesoTarjeta, pk=item_id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del proceso es obligatorio.')
        elif ProcesoTarjeta.objects.filter(nombre__iexact=nombre).exclude(pk=item_id).exists():
            messages.error(request, 'Ese proceso ya existe.')
        else:
            _actualizar_proceso(
                proceso,
                nombre,
                request.POST.get('descripcion', '').strip(),
                request.POST.get('activo') == 'on',
                _estatus_ids_del_formulario(request.POST),
            )
            messages.success(request, 'Proceso actualizado correctamente.')
    return redirect('procesos_tarjeta')


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_tarjetaviajera')
def proceso_tarjeta_eliminar(request, item_id):
    if request.method == 'POST':
        proceso = get_object_or_404(ProcesoTarjeta, pk=item_id)
        try:
            proceso.delete()
            messages.success(request, 'Proceso eliminado correctamente.')
        except ProtectedError:
            messages.error(request, 'No se puede eliminar porque hay tarjetas asignadas a este proceso.')
    return redirect('procesos_tarjeta')


from django.db.models import Count



@login_required
@requiere_gestion_tarj_viajeras
def tarj_viajeras_excel(request):
    estados=StatusTar.objects.annotate(
        total=Count('tarjetas_viajeras')
    ).order_by('id_status')

    labels=[e.descripcion for e in estados]
    datos=[e.total for e in estados]

    return render(request,'tarj_viajeras/tarj_viajeras_excel.html',{
        'labels':labels,
        'datos':datos,
        'total_tarjetas':sum(datos),
        'estados':estados
    })





@login_required
def reporte_produccion_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte Producción"
    encabezados = ["FOLIO", "OC", "LAMINACIÓN CLIENTE", "LAMINACIÓN VCL", "LOTE", "MATERIAL", "ESPESOR", "CLIENTES", "FOLIO DE TARJETAS VIAJERAS"]
    ws.append(encabezados)

    tarjetas = TarjetaViajera.objects.select_related(
        'produccion', 'produccion__cliente', 'produccion__material',
        'produccion__espesor', 'produccion__laminacion',
        'produccion__numero_parte_cliente'
    ).order_by('produccion__numero_orden_trabajo', 'numero_tarjeta', 'sufijo')

    for t in tarjetas.iterator():
        p = t.produccion
        folio_orden = str(p.numero_orden_trabajo or "").strip()
        folio_tarjeta = str(t.folio_completo or "")

        ws.append([
            folio_orden,
            str(p.numero_orden_compra or ""),
            str(p.numero_parte_cliente.descripcion) if p.numero_parte_cliente else "",
            str(p.laminacion.especificacion) if p.laminacion else "",
            str(p.lote or ""),
            str(p.material.especificacion) if p.material else "",
            str(p.espesor.espesor) if p.espesor else "",
            str(p.cliente.nombre) if p.cliente else "",
            folio_tarjeta
        ])

    verde = PatternFill(fill_type="solid", fgColor="AAE043")
    blanco = PatternFill(fill_type="solid", fgColor="FFFFFF")
    gris = PatternFill(fill_type="solid", fgColor="F2F5F7")
    borde = Side(style="thin", color="CAD5DC")
    anchos = [18, 20, 28, 35, 22, 24, 16, 30, 30]

    for i, ancho in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    for celda in ws[1]:
        celda.fill = verde
        celda.font = Font(name="Arial", size=11, bold=True, color="111111")
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        celda.border = Border(left=borde, right=borde, top=borde, bottom=borde)
    ws.row_dimensions[1].height = 40

    for fila in ws.iter_rows(min_row=2):
        numero = fila[0].row
        fondo = blanco if numero % 2 == 0 else gris
        for celda in fila:
            celda.fill = fondo
            celda.font = Font(name="Arial", size=10, color="111111")
            celda.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            celda.border = Border(left=borde, right=borde, top=borde, bottom=borde)
            celda.number_format = "@"
        ws.row_dimensions[numero].height = 32

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:1"
    ws.print_area = ws.dimensions

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="reporte_tarjetas_viajeras_VCL.xlsx"'
    wb.save(response)
    return response

@login_required
def reporte_kanban(request):
    producciones=Produccion.objects.select_related('cliente').order_by('-id_produccion')
    produccion_id=request.GET.get('produccion','')
    produccion=None
    columnas=[]
    total=0

    if produccion_id.isdigit():
        produccion=get_object_or_404(Produccion,id_produccion=produccion_id)
        tarjetas=list(TarjetaViajera.objects.filter(produccion=produccion).select_related('status').order_by('numero_tarjeta','sufijo'))
        total=len(tarjetas)

        for estado in StatusTar.objects.all().order_by('id_status'):
            grupo=[t for t in tarjetas if t.status_id==estado.id_status]
            columnas.append({'estado':estado,'tarjetas':grupo,'total':len(grupo)})

    return render(request,'tarj_viajeras/reporte_kanban.html',{
        'producciones':producciones,
        'produccion':produccion,
        'columnas':columnas,
        'total':total
    })
