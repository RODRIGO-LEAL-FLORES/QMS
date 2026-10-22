"""Vistas del catálogo de estatus y del cambio por escáner."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from apps.usuarios.permissions import tiene_permiso
from .models import StatusTar, TarjetaViajera
from .services.estatus import (
    codigo_barras_estatus,
    descripcion_estatus_duplicada,
    id_estatus_desde_codigo,
    normalizar_descripcion_estatus,
    separar_codigo_tarjeta,
)


# =========================================================
# ESTATUS: PERMISOS DE VISTA
# =========================================================

def requiere_permiso(permiso):
    def decorador(vista):
        @wraps(vista)
        def vista_protegida(request, *args, **kwargs):
            if not tiene_permiso(request.user, permiso):
                messages.error(request, 'No tienes permisos para acceder a esta opción.')
                return redirect('tarj_viajeras')
            return vista(request, *args, **kwargs)
        return vista_protegida
    return decorador


def requiere_actualizar_estatus(vista):
    @wraps(vista)
    def vista_protegida(request, *args, **kwargs):
        permisos = (
            'tarj_viajeras.change_tarjetaviajera',
            'tarj_viajeras.update_status_tarjetaviajera',
            'tarj_viajeras.update_measurements_tarjetaviajera',
        )
        if not any(tiene_permiso(request.user, permiso) for permiso in permisos):
            messages.error(request, 'Tu rol no permite actualizar Tarjetas Viajeras.')
            return redirect('tarj_viajeras')
        return vista(request, *args, **kwargs)
    return vista_protegida


def _redirect_edicion(item_id):
    return redirect(f'{reverse("status_tarjeta")}?edit_id={item_id}')


# =========================================================
# ESTATUS: CATÁLOGO CRUD
# =========================================================

@login_required
@requiere_permiso('tarj_viajeras.view_statustar')
def status_tarjeta(request):
    search_query = request.GET.get('search', '').strip()
    items = StatusTar.objects.all().order_by('id_status')
    if search_query:
        items = items.filter(descripcion__icontains=search_query)

    edit_item = None
    edit_id = request.GET.get('edit_id')
    if (
        edit_id and edit_id.isdigit()
        and tiene_permiso(request.user, 'tarj_viajeras.change_statustar')
    ):
        edit_item = get_object_or_404(StatusTar, id_status=edit_id)

    return render(request, 'tarj_viajeras/status_tarjeta.html', {
        'items': items,
        'edit_item': edit_item,
        'search_query': search_query,
        'puede_agregar_status': tiene_permiso(request.user, 'tarj_viajeras.add_statustar'),
        'puede_editar_status': tiene_permiso(request.user, 'tarj_viajeras.change_statustar'),
        'puede_eliminar_status': tiene_permiso(request.user, 'tarj_viajeras.delete_statustar'),
    })


@login_required
@requiere_permiso('tarj_viajeras.add_statustar')
def status_tarjeta_crear(request):
    if request.method == 'POST':
        descripcion = normalizar_descripcion_estatus(request.POST.get('descripcion'))
        if not descripcion:
            messages.error(request, 'La descripción es obligatoria.')
        elif descripcion_estatus_duplicada(descripcion):
            messages.error(request, 'Ese estatus ya existe.')
        else:
            StatusTar.objects.create(descripcion=descripcion)
            messages.success(request, 'Estatus creado correctamente.')
    return redirect('status_tarjeta')


@login_required
@requiere_permiso('tarj_viajeras.change_statustar')
def status_tarjeta_editar(request, item_id):
    item = get_object_or_404(StatusTar, id_status=item_id)
    if request.method == 'POST':
        descripcion = normalizar_descripcion_estatus(request.POST.get('descripcion'))
        if not descripcion:
            messages.error(request, 'La descripción es obligatoria.')
            return _redirect_edicion(item_id)
        if descripcion_estatus_duplicada(descripcion, excluir_id=item_id):
            messages.error(request, 'Ese estatus ya existe.')
            return _redirect_edicion(item_id)
        item.descripcion = descripcion
        item.save()
        messages.success(request, 'Estatus actualizado correctamente.')
    return redirect('status_tarjeta')


@login_required
@requiere_permiso('tarj_viajeras.delete_statustar')
def status_tarjeta_eliminar(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(StatusTar, id_status=item_id)
        try:
            item.delete()
            messages.success(request, 'Estatus eliminado correctamente.')
        except ProtectedError:
            messages.error(request, 'No se puede eliminar porque está siendo utilizado por una tarjeta viajera.')
    return redirect('status_tarjeta')


# =========================================================
# ESTATUS: CÓDIGOS PDF Y ACTUALIZACIÓN POR ESCÁNER
# =========================================================

@login_required
@requiere_permiso('tarj_viajeras.view_statustar')
def status_tarjetas_pdf(request):
    estados = StatusTar.objects.all().order_by('id_status')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="codigos_estatus.pdf"'
    pdf = canvas.Canvas(response, pagesize=letter)
    ancho_pagina, alto_pagina = letter

    def encabezado():
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawCentredString(ancho_pagina / 2, alto_pagina - 20 * mm, 'CÓDIGOS DE ESTATUS')
        pdf.setFont('Helvetica', 9)
        pdf.drawCentredString(ancho_pagina / 2, alto_pagina - 27 * mm, 'Tarjetas Viajeras - Cambio de estatus')

    encabezado()
    y = alto_pagina - 50 * mm
    for estado in estados:
        codigo = codigo_barras_estatus(estado.id_status)
        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(25 * mm, y + 7 * mm, estado.descripcion)
        barcode = code128.Code128(codigo, barHeight=18 * mm, barWidth=.65 * mm,
                                  humanReadable=False, quiet=True)
        barcode.drawOn(pdf, 80 * mm, y)
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawCentredString(80 * mm + barcode.width / 2, y - 5 * mm, codigo)
        y -= 30 * mm
        if y < 30 * mm:
            pdf.showPage()
            encabezado()
            y = alto_pagina - 50 * mm

    pdf.save()
    return response


@login_required
@requiere_actualizar_estatus
def escaner_tarjetas(request):
    return render(request, 'tarj_viajeras/escaner_tarjetas.html')


@login_required
@requiere_actualizar_estatus
def cambiar_status_barcode(request):
    if request.method != 'POST':
        return redirect('tarjetas_viajeras')

    codigo_tarjeta = request.POST.get('tarjeta', '').strip()
    codigo_status = request.POST.get('status', '').strip()
    codigo_separado = separar_codigo_tarjeta(codigo_tarjeta)
    if codigo_separado is None:
        messages.error(request, 'El código escaneado no contiene un folio de tarjeta válido.')
        return redirect('tarjetas_viajeras')
    if not codigo_status.isdigit():
        messages.error(request, 'El código de estatus debe ser numérico. Escanea primero la tarjeta y después el código del estatus.')
        return redirect('tarjetas_viajeras')

    orden, numero_tarjeta, sufijo = codigo_separado
    status_id = id_estatus_desde_codigo(codigo_status)
    if status_id is None:
        messages.error(request, 'Código de estatus inválido.')
        return redirect('tarjetas_viajeras')

    filtros_tarjeta = {'numero_tarjeta': numero_tarjeta, 'sufijo': sufijo}
    if orden:
        filtros_tarjeta['produccion__numero_orden_trabajo__iexact'] = orden

    try:
        tarjeta = TarjetaViajera.objects.select_related('produccion', 'status').get(**filtros_tarjeta)
        nuevo_status = StatusTar.objects.get(id_status=status_id)
        anterior = tarjeta.status.descripcion if tarjeta.status else 'SIN ESTATUS'
        tarjeta.status = nuevo_status
        tarjeta.save(update_fields=['status'])
        messages.success(request, f'Tarjeta {tarjeta.folio_completo}: {anterior} → {nuevo_status.descripcion}')
    except TarjetaViajera.DoesNotExist:
        orden_texto = f'{orden}|' if orden else ''
        sufijo_texto = f'-{sufijo}' if sufijo else ''
        messages.error(request, f'No se encontró la tarjeta {orden_texto}{numero_tarjeta}{sufijo_texto}. Verifica la OT y el folio.')
    except TarjetaViajera.MultipleObjectsReturned:
        messages.error(request, 'Se encontró más de una tarjeta con ese código.')
    except StatusTar.DoesNotExist:
        messages.error(request, f'No existe un estatus con código {status_id}.')

    return redirect('tarjetas_viajeras')
