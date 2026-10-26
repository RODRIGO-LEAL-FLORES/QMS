"""Vistas CRUD de catálogos utilizados por Tarjetas Viajeras."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.liberaciones.models import TipoLaminacion
from apps.scrap.models import TipoAcero

from .models import Espesor, NumeroParteCliente
from apps.usuarios.permissions import tiene_permiso


def usuario_puede(user, permiso):
    return tiene_permiso(user, permiso)


def requiere_permiso_tarj_viajeras(permiso):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not tiene_permiso(request.user, permiso):
                messages.error(request, 'No tienes permisos para acceder a esta opción.')
                return redirect('tarj_viajeras')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


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


def redirect_edicion(nombre_url, item_id):
    return redirect(f'{reverse(nombre_url)}?edit_id={item_id}')


@login_required
@requiere_permiso_tipo_laminacion('liberaciones.view_tipolaminacion')
def tipo_laminacion(request):
    search_query = request.GET.get('search', '').strip()
    items = TipoLaminacion.objects.all().order_by('especificacion')
    if search_query:
        items = items.filter(especificacion__icontains=search_query)

    edit_item = None
    edit_id = request.GET.get('edit_id')
    if edit_id and edit_id.isdigit():
        edit_item = get_object_or_404(TipoLaminacion, id_tipo_laminacion=edit_id)

    return render(request, 'tarj_viajeras/tipo_laminacion.html', {
        'items': items,
        'edit_item': edit_item if tiene_permiso(request.user, 'liberaciones.change_tipolaminacion') else None,
        'search_query': search_query,
        'puede_agregar_tipo_laminacion': tiene_permiso(request.user, 'liberaciones.add_tipolaminacion'),
        'puede_editar_tipo_laminacion': tiene_permiso(request.user, 'liberaciones.change_tipolaminacion'),
        'puede_eliminar_tipo_laminacion': tiene_permiso(request.user, 'liberaciones.delete_tipolaminacion'),
    })


@login_required
@requiere_permiso_tipo_laminacion('liberaciones.add_tipolaminacion')
def tipo_laminacion_crear(request):
    if request.method == 'POST':
        especificacion = request.POST.get('especificacion', '').strip()
        if not especificacion:
            messages.error(request, 'La especificación es obligatoria.')
        elif TipoLaminacion.objects.filter(especificacion__iexact=especificacion).exists():
            messages.error(request, 'Ese tipo de laminación ya existe.')
        else:
            TipoLaminacion.objects.create(especificacion=especificacion)
            messages.success(request, 'Tipo de laminación creado correctamente.')
    return redirect('tarj_tipo_laminacion')


@login_required
@requiere_permiso_tipo_laminacion('liberaciones.change_tipolaminacion')
def tipo_laminacion_editar(request, item_id):
    item = get_object_or_404(TipoLaminacion, id_tipo_laminacion=item_id)
    if request.method == 'POST':
        especificacion = request.POST.get('especificacion', '').strip()
        if not especificacion:
            messages.error(request, 'La especificación es obligatoria.')
            return redirect_edicion('tarj_tipo_laminacion', item_id)
        if TipoLaminacion.objects.filter(especificacion__iexact=especificacion).exclude(id_tipo_laminacion=item_id).exists():
            messages.error(request, 'Ese tipo de laminación ya existe.')
            return redirect_edicion('tarj_tipo_laminacion', item_id)
        item.especificacion = especificacion
        item.save()
        messages.success(request, 'Tipo de laminación actualizado correctamente.')
    return redirect('tarj_tipo_laminacion')


@login_required
@requiere_permiso_tipo_laminacion('liberaciones.delete_tipolaminacion')
def tipo_laminacion_eliminar(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(TipoLaminacion, id_tipo_laminacion=item_id)
        try:
            item.delete()
            messages.success(request, 'Tipo de laminación eliminado correctamente.')
        except ProtectedError:
            messages.error(request, 'No se puede eliminar porque el tipo de laminación está siendo utilizado.')
    return redirect('tarj_tipo_laminacion')
# ESPESORES
# =========================================================

@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.view_espesor')
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
        {
            'items': items,
            'edit_item': edit_item if usuario_puede(request.user, 'tarj_viajeras.change_espesor') else None,
            'search_query': search_query,
            'puede_agregar_espesor': usuario_puede(request.user, 'tarj_viajeras.add_espesor'),
            'puede_editar_espesor': usuario_puede(request.user, 'tarj_viajeras.change_espesor'),
            'puede_eliminar_espesor': usuario_puede(request.user, 'tarj_viajeras.delete_espesor'),
        }
    )


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.add_espesor')
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
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_espesor')
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
@requiere_permiso_tarj_viajeras('tarj_viajeras.delete_espesor')
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
@requiere_permiso_tarj_viajeras('tarj_viajeras.view_numeropartecliente')
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
        {
            'items': items,
            'edit_item': edit_item if usuario_puede(request.user, 'tarj_viajeras.change_numeropartecliente') else None,
            'search_query': search_query,
            'puede_agregar_numero_parte': usuario_puede(request.user, 'tarj_viajeras.add_numeropartecliente'),
            'puede_editar_numero_parte': usuario_puede(request.user, 'tarj_viajeras.change_numeropartecliente'),
            'puede_eliminar_numero_parte': usuario_puede(request.user, 'tarj_viajeras.delete_numeropartecliente'),
        }
    )


@login_required
@requiere_permiso_tarj_viajeras('tarj_viajeras.add_numeropartecliente')
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
@requiere_permiso_tarj_viajeras('tarj_viajeras.change_numeropartecliente')
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
@requiere_permiso_tarj_viajeras('tarj_viajeras.delete_numeropartecliente')
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
# TIPO DE ACERO
# =========================================================

@login_required
@requiere_permiso_tarj_viajeras('scrap.view_tipoacero')
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
        {
            'items': items,
            'edit_item': edit_item if usuario_puede(request.user, 'scrap.change_tipoacero') else None,
            'search_query': search_query,
            'puede_agregar_tipo_acero': usuario_puede(request.user, 'scrap.add_tipoacero'),
            'puede_editar_tipo_acero': usuario_puede(request.user, 'scrap.change_tipoacero'),
            'puede_eliminar_tipo_acero': usuario_puede(request.user, 'scrap.delete_tipoacero'),
        }
    )


@login_required
@requiere_permiso_tarj_viajeras('scrap.add_tipoacero')
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
@requiere_permiso_tarj_viajeras('scrap.change_tipoacero')
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
@requiere_permiso_tarj_viajeras('scrap.delete_tipoacero')
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
