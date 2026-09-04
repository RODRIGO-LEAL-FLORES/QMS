from django.shortcuts import render
import csv
import io
from collections import Counter
from datetime import date, datetime, timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models.deletion import ProtectedError
from apps.reclamaciones.models import Reclamacion
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from functools import wraps
from apps.areas.models import Area
from core.user_messages import mensaje_error_guardado
from .models import Prioridad, EstatusReclamacionInterna, ReclamacionInterna, EvidenciaReclamacionInterna

Usuario = get_user_model()


@login_required
def areas(request):
    search_query = request.GET.get('search', '').strip()
    queryset = Area.objects.all()

    if search_query:
        queryset = queryset.filter(nombre__icontains=search_query)

    queryset = queryset.order_by('nombre')
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    edit_id = request.GET.get('edit_id')
    edit_item = Area.objects.filter(pk=edit_id).first() if edit_id else None

    return render(request, 'reclamaciones_internas/areas.html', {
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'edit_item': edit_item,
        'search_query': search_query,
        'total_results': paginator.count,
    })


@login_required
def area_crear(request):
    if request.method != 'POST':
        return redirect('areas')

    nombre = request.POST.get('nombre', '').strip()

    if not nombre:
        messages.error(request, 'El nombre del área es obligatorio.')
        return redirect('areas')

    if Area.objects.filter(nombre__iexact=nombre).exists():
        messages.error(request, 'Esta área ya existe.')
        return redirect('areas')

    Area.objects.create(nombre=nombre)
    messages.success(request, 'Área creada correctamente.')
    return redirect('areas')


@login_required
def area_editar(request, item_id):
    area = get_object_or_404(Area, pk=item_id)

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()

        if not nombre:
            messages.error(request, 'El nombre del área es obligatorio.')
            return redirect('areas')

        if Area.objects.filter(nombre__iexact=nombre).exclude(pk=item_id).exists():
            messages.error(request, 'Ya existe otra área con ese nombre.')
        else:
            area.nombre = nombre
            area.save()
            messages.success(request, 'Área actualizada correctamente.')

    return redirect('areas')


@login_required
def area_eliminar(request, item_id):
    area = get_object_or_404(Area, pk=item_id)

    if request.method == 'POST':
        tiene_usuarios = Usuario.objects.filter(area=area).exists()
        tiene_reclamaciones_internas = ReclamacionInterna.objects.filter(
            area_responsable=area
        ).exists()
        tiene_reclamaciones = Reclamacion.objects.filter(
            areas_involucradas=area
        ).exists()

        if (
            tiene_usuarios
            or tiene_reclamaciones_internas
            or tiene_reclamaciones
        ):
            mensajes_relaciones = []

            if tiene_usuarios:
                mensajes_relaciones.append('usuarios')
            if tiene_reclamaciones_internas:
                mensajes_relaciones.append('reclamaciones internas')
            if tiene_reclamaciones:
                mensajes_relaciones.append('reclamaciones')

            messages.error(
                request,
                'No se puede eliminar el área porque está relacionada con '
                + ', '.join(mensajes_relaciones)
                + '. Conserva el área para mantener el historial.'
            )
        else:
            area.delete()
            messages.success(request, 'Área eliminada correctamente.')

    return redirect('areas')

def get_status(status_name):
    """
    Regresa el objeto EstatusReclamacionInterna por descripción.

    Los estatus válidos son:
        1 - Sin atender
        2 - En proceso
        3 - Pendiente de validación
        4 - Cerrado
    """
    status = EstatusReclamacionInterna.objects.filter(descripcion=status_name).first()
    if status:
        return status
    return EstatusReclamacionInterna.objects.order_by('id_estatus').first()

def get_status_id(status_name):
    status = get_status(status_name)
    return status.id_estatus if status else None

def get_cerrado_id():
    return get_status_id('Cerrado')

def calcular_dias_retraso(reclamacion):
    """
    Calcula días de retraso en vivo.

    - Sin fecha compromiso: 0
    - Cerrada: fecha_cierre - fecha_compromiso
    - Abierta: hoy - fecha_compromiso
    """
    if not reclamacion.fecha_compromiso:
        return 0

    cerrado_id = get_cerrado_id()

    if reclamacion.estatus_id == cerrado_id:
        if not reclamacion.fecha_cierre:
            return 0
        dias = (reclamacion.fecha_cierre - reclamacion.fecha_compromiso).days
    else:
        dias = (date.today() - reclamacion.fecha_compromiso).days

    return max(dias, 0)

def usuario_puede_ver_reclamaciones_internas(user):
    return user.is_authenticated and user.is_active and getattr(user, 'puede_gestionar_reclamaciones_internas', False)


def usuario_puede_modificar_reclamaciones_internas(user):
    return usuario_puede_ver_reclamaciones_internas(user) and user.rol_id in (1, 2)


def requiere_operacion_reclamaciones_internas(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not usuario_puede_ver_reclamaciones_internas(request.user):
            messages.error(request, 'No tienes autorización para acceder a este módulo.')
            return redirect('home')
        if request.user.rol_id == 4:
            messages.info(request, 'Los auditores solo pueden consultar reportes.')
            return redirect('reportes_reclamaciones_internas')
        return view(request, *args, **kwargs)

    return wrapped


def requiere_catalogo_reclamaciones_internas(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not usuario_puede_modificar_reclamaciones_internas(request.user):
            messages.error(request, 'Tu rol no permite administrar este catálogo.')
            return redirect('reclamaciones_int')
        return view(request, *args, **kwargs)

    return wrapped

def enviar_notificacion_nueva_reclamacion(reclamacion):
    if not reclamacion.area_responsable_id:
        return

    usuarios = Usuario.objects.filter(
        area_id=reclamacion.area_responsable_id,
        puede_gestionar_reclamaciones_internas=True,
        is_active=True
    ).exclude(email='')

    destinatarios = list(usuarios.values_list('email', flat=True))

    if not destinatarios:
        return

    area_nombre = reclamacion.area_responsable.nombre if reclamacion.area_responsable else 'N/A'
    asunto = f'Nueva Reclamación Interna #{reclamacion.id_folio}'

    cuerpo = f"""
Hola,

Se ha registrado una nueva reclamación interna para tu área.

Folio: {reclamacion.id_folio}
Área responsable: {area_nombre}
Emisor: {reclamacion.emisor or 'N/A'}

Fecha de emisión: {reclamacion.fecha_emision}

Problemática:
{reclamacion.problematica or 'Sin descripción registrada.'}

Por favor ingresa al sistema para atenderla.
"""

    correo = EmailMessage(subject=asunto, body=cuerpo, to=destinatarios)
    correo.send(fail_silently=True)

def enviar_notificacion_rechazo(reclamacion, motivo=None):
    if not reclamacion.area_responsable_id:
        return

    usuarios = Usuario.objects.filter(
        area_id=reclamacion.area_responsable_id,
        puede_gestionar_reclamaciones_internas=True,
        is_active=True
    ).exclude(email='')

    destinatarios = list(usuarios.values_list('email', flat=True))

    if not destinatarios:
        return

    area_nombre = reclamacion.area_responsable.nombre if reclamacion.area_responsable else 'N/A'
    asunto = f'Reclamación interna #{reclamacion.id_folio} rechazada'

    cuerpo = f"""
Hola,

La reclamación interna #{reclamacion.id_folio}
fue RECHAZADA por el emisor.

Regresó al estatus "En proceso" para que el área responsable
corrija la acción correctiva y/o cargue nueva evidencia.

Folio: {reclamacion.id_folio}
Área responsable: {area_nombre}
Emisor: {reclamacion.emisor or 'N/A'}

Motivo del rechazo:
{motivo or 'El emisor no especificó un motivo.'}

Acción correctiva registrada:
{reclamacion.accion_correctiva or 'Sin acción correctiva registrada.'}

Por favor ingresa al sistema para corregir la reclamación.
"""

    correo = EmailMessage(subject=asunto, body=cuerpo, to=destinatarios)
    correo.send(fail_silently=True)

def crear_reclamacion_desde_formulario(request):
    prioridad_id = request.POST.get('id_prioridad') or None
    prioridad = None

    if prioridad_id:
        prioridad = Prioridad.objects.filter(id_prioridad=prioridad_id).first()

    fecha_emision = date.today()
    fecha_compromiso = None

    if prioridad and prioridad.dias_resolucion is not None:
        fecha_compromiso = fecha_emision + timedelta(days=prioridad.dias_resolucion)

    estatus = get_status('Sin atender')

    if not estatus:
        raise ValueError('No existen estatus configurados.')

    reclamacion = ReclamacionInterna.objects.create(
        prioridad=prioridad,
        usuario_creador=request.user,
        emisor=request.user.nombre or request.user.username,
        area_responsable_id=request.POST.get('id_area_responsable') or None,
        fecha_emision=fecha_emision,
        fecha_compromiso=fecha_compromiso,
        estatus=estatus,
        dias_retraso=0,
        problematica=request.POST.get('problematica', '').strip() or None
    )

    enviar_notificacion_nueva_reclamacion(reclamacion)
    return reclamacion

@login_required
def reclamaciones_internas(request):
    if not usuario_puede_ver_reclamaciones_internas(request.user):
        messages.error(request, 'No tienes autorización para acceder a este módulo.')
        return redirect('home')

    registros = ReclamacionInterna.objects.filter(
        usuario_creador=request.user
    ).select_related(
        'prioridad',
        'area_responsable',
        'estatus'
    ).order_by('-id_folio')[:20]

    return render(request, 'reclamaciones_internas/reclamaciones_internas.html', {
        'today': date.today(),
        'prioridades': Prioridad.objects.order_by('Prioridad'),
        'areas': Area.objects.order_by('nombre'),
        'registros': registros
    })

@login_required
def reclamaciones_internas_create(request):
    if not usuario_puede_ver_reclamaciones_internas(request.user):
        messages.error(request, 'No tienes autorización.')
        return redirect('home')

    if request.method == 'POST':
        try:
            crear_reclamacion_desde_formulario(request)
            messages.success(request, 'Reclamación interna registrada correctamente.')
            return redirect('reclamaciones_internas_create')
        except Exception as error:
            messages.error(
                request,
                f'No se pudo registrar la reclamación interna: {mensaje_error_guardado(error)}'
            )

    search_query = request.GET.get('search', '').strip()

    queryset = ReclamacionInterna.objects.filter(
        usuario_creador=request.user
    ).select_related(
        'prioridad',
        'area_responsable',
        'estatus'
    )

    if search_query and search_query.isdigit():
        queryset = queryset.filter(id_folio__icontains=search_query)

    queryset = queryset.order_by('-id_folio')

    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    retraso_map = {
        r.id_folio: calcular_dias_retraso(r)
        for r in page_obj.object_list
    }

    return render(request, 'reclamaciones_internas/generar_registro.html', {
        'today': date.today(),
        'prioridades': Prioridad.objects.order_by('Prioridad'),
        'areas': Area.objects.order_by('nombre'),
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'total_results': paginator.count,
        'search_query': search_query,
        'retraso_map': retraso_map
    })
    
@login_required
def reclamacion_interna_editar(request, item_id):
    if not usuario_puede_modificar_reclamaciones_internas(request.user):
        messages.error(request, 'Tu rol no permite editar reclamaciones internas.')
        return redirect('reclamaciones_internas_create')

    reclamacion = get_object_or_404(
        ReclamacionInterna,
        id_folio=item_id,
        usuario_creador=request.user
    )

    if request.method != 'POST':
        return redirect('reclamaciones_internas_create')

    prioridad_id = request.POST.get('id_prioridad') or None
    area_id = request.POST.get('id_area_responsable') or None
    problematica = request.POST.get('problematica', '').strip() or None

    # Validar prioridad
    prioridad = None
    if prioridad_id:
        prioridad = Prioridad.objects.filter(
            id_prioridad=prioridad_id
        ).first()

        if not prioridad:
            messages.error(request, 'La prioridad seleccionada no existe.')
            return redirect('reclamaciones_internas_create')

    # Validar área
    area = None
    if area_id:
        area = Area.objects.filter(
            pk=area_id
        ).first()

        if not area:
            messages.error(request, 'El área seleccionada no existe.')
            return redirect('reclamaciones_internas_create')

    # Guardar cambios
    reclamacion.prioridad = prioridad
    reclamacion.area_responsable = area
    reclamacion.problematica = problematica

    # Recalcular fecha compromiso si cambia prioridad
    if prioridad and prioridad.dias_resolucion is not None:
        reclamacion.fecha_compromiso = (
            reclamacion.fecha_emision
            + timedelta(days=prioridad.dias_resolucion)
        )
    else:
        reclamacion.fecha_compromiso = None

    reclamacion.dias_retraso = calcular_dias_retraso(reclamacion)

    reclamacion.save()

    messages.success(
        request,
        f'Reclamación interna #{reclamacion.id_folio} actualizada correctamente.'
    )

    return redirect('reclamaciones_internas_create')


@login_required
def reclamacion_interna_eliminar(request, item_id):
    if not usuario_puede_modificar_reclamaciones_internas(request.user):
        messages.error(request, 'Tu rol no permite eliminar reclamaciones internas.')
        return redirect('reclamaciones_internas_create')

    reclamacion = get_object_or_404(
        ReclamacionInterna,
        id_folio=item_id,
        usuario_creador=request.user
    )

    if request.method != 'POST':
        return redirect('reclamaciones_internas_create')

    folio = reclamacion.id_folio

    try:
        reclamacion.delete()

        messages.success(
            request,
            f'Reclamación interna #{folio} eliminada correctamente.'
        )

    except Exception as error:
        messages.error(
            request,
            f'No se pudo eliminar la reclamación interna #{folio}: '
            f'{mensaje_error_guardado(error)}'
        )

    return redirect('reclamaciones_internas_create')

@login_required
def mis_reclamaciones_internas(request):
    cerrado_id = get_cerrado_id()

    reclamaciones = ReclamacionInterna.objects.filter(
        area_responsable_id=request.user.area_id
    ).exclude(
        estatus_id=cerrado_id
    ).select_related(
        'prioridad',
        'estatus',
        'usuario_creador',
        'area_responsable'
    ).order_by('fecha_compromiso')

    retraso_map = {
        r.id_folio: calcular_dias_retraso(r)
        for r in reclamaciones
    }

    return render(request, 'reclamaciones_internas/mis_reclamaciones.html', {
        'reclamaciones': reclamaciones,
        'today': date.today(),
        'cerrado_id': cerrado_id,
        'retraso_map': retraso_map
    })

@login_required
def seguimiento_reclamaciones_internas(request):
    if not usuario_puede_ver_reclamaciones_internas(request.user):
        messages.error(request, 'No tienes autorización para acceder a este módulo.')
        return redirect('home')

    cerrado_id = get_cerrado_id()
    search_query = request.GET.get('search', '').strip()

    queryset = ReclamacionInterna.objects.filter(
        area_responsable_id=request.user.area_id
    ).exclude(
        estatus_id=cerrado_id
    ).select_related(
        'prioridad',
        'estatus',
        'usuario_creador',
        'area_responsable'
    )

    if search_query.isdigit():
        queryset = queryset.filter(id_folio=int(search_query))

    queryset = queryset.order_by('fecha_compromiso')

    retraso_map = {
        r.id_folio: calcular_dias_retraso(r)
        for r in queryset
    }

    return render(request, 'reclamaciones_internas/seguimiento.html', {
        'reclamaciones': queryset,
        'today': date.today(),
        'cerrado_id': cerrado_id,
        'retraso_map': retraso_map,
        'search_query': search_query
    })

@login_required
def reclamaciones_por_cerrar(request):
    if not usuario_puede_ver_reclamaciones_internas(request.user):
        messages.error(request, 'No tienes autorización para acceder a este módulo.')
        return redirect('home')

    pendiente_id = get_status_id('Pendiente de validación')

    reclamaciones = ReclamacionInterna.objects.filter(
        usuario_creador=request.user,
        estatus_id=pendiente_id
    ).select_related(
        'prioridad',
        'estatus',
        'area_responsable'
    ).order_by('fecha_compromiso')

    return render(request, 'reclamaciones_internas/por_cerrar.html', {
        'reclamaciones': reclamaciones,
        'today': date.today()
    })

@login_required
def reclamacion_interna_detail(request, item_id):
    if not usuario_puede_ver_reclamaciones_internas(request.user):
        messages.error(request, 'No tienes autorización para acceder a este módulo.')
        return redirect('home')

    reclamacion = get_object_or_404(
        ReclamacionInterna.objects.select_related(
            'prioridad',
            'estatus',
            'area_responsable',
            'usuario_creador'
        ).prefetch_related('evidencias'),
        pk=item_id
    )

    en_proceso_id = get_status_id('En proceso')
    pendiente_validacion_id = get_status_id('Pendiente de validación')
    cerrado_id = get_cerrado_id()

    if request.method == 'POST':
        if request.user.rol_id == 4:
            messages.error(request, 'El auditor tiene permisos de solo lectura en este módulo.')
            return redirect('reclamacion_interna_detail', item_id=item_id)

        if request.user.id == reclamacion.usuario_creador_id and reclamacion.estatus_id == pendiente_validacion_id:

            if request.POST.get('cerrar_reclamacion'):
                reclamacion.estatus_id = cerrado_id
                reclamacion.fecha_cierre = date.today()
                reclamacion.dias_retraso = calcular_dias_retraso(reclamacion)
                reclamacion.save()

                messages.success(request, 'Reclamación interna cerrada correctamente.')
                return redirect('reclamacion_interna_detail', item_id=item_id)

            if request.POST.get('rechazar_reclamacion'):
                motivo = request.POST.get('motivo_rechazo', '').strip() or None
                reclamacion.estatus_id = en_proceso_id
                reclamacion.dias_retraso = calcular_dias_retraso(reclamacion)
                reclamacion.save()

                enviar_notificacion_rechazo(reclamacion, motivo)

                messages.warning(request, 'La reclamación fue rechazada y regresó a En proceso.')
                return redirect('reclamacion_interna_detail', item_id=item_id)

        if request.user.area_id == reclamacion.area_responsable_id:
            accion_correctiva = request.POST.get('acciones_correctivas', '').strip() or None
            evidencia_resolucion = request.POST.get('evidencia_resolucion', '').strip() or None

            if accion_correctiva:
                reclamacion.accion_correctiva = accion_correctiva
                reclamacion.estatus_id = en_proceso_id

            if evidencia_resolucion:
                reclamacion.evidencia_resolucion = evidencia_resolucion
                reclamacion.estatus_id = pendiente_validacion_id

            archivos = request.FILES.getlist('evidence_files')
            archivos_validos = False

            for archivo in archivos:
                if not archivo:
                    continue

                if not archivo.name.lower().endswith('.pdf'):
                    messages.error(request, f'El archivo {archivo.name} no es PDF.')
                    continue

                EvidenciaReclamacionInterna.objects.create(
                    reclamacion=reclamacion,
                    archivo=archivo
                )

                archivos_validos = True

            if archivos_validos:
                reclamacion.estatus_id = pendiente_validacion_id

            reclamacion.dias_retraso = calcular_dias_retraso(reclamacion)
            reclamacion.save()

            messages.success(request, 'Reclamación interna actualizada correctamente.')
            return redirect('reclamacion_interna_detail', item_id=item_id)

    dias_retraso = calcular_dias_retraso(reclamacion)

    return render(request, 'reclamaciones_internas/detalle.html', {
        'reclamacion': reclamacion,
        'today': date.today(),
        'cerrado_id': cerrado_id,
        'pendiente_validacion_id': pendiente_validacion_id,
        'dias_retraso': dias_retraso
    })

@login_required
def prioridades(request):
    search_query = request.GET.get('search', '').strip()
    queryset = Prioridad.objects.all()

    if search_query:
        queryset = queryset.filter(Prioridad__icontains=search_query)

    queryset = queryset.order_by('Prioridad')

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    edit_id = request.GET.get('edit_id')
    edit_item = Prioridad.objects.filter(pk=edit_id).first() if edit_id else None

    return render(request, 'reclamaciones_internas/prioridades.html', {
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'edit_item': edit_item,
        'search_query': search_query,
        'total_results': paginator.count
    })

@login_required
def prioridad_crear(request):
    if request.method != 'POST':
        return redirect('prioridades')

    nombre = request.POST.get('prioridad', '').strip()
    descripcion = request.POST.get('descripcion', '').strip() or None
    dias = request.POST.get('dias_resolucion', '0').strip()

    if not nombre:
        messages.error(request, 'El nombre de la prioridad es obligatorio.')
        return redirect('prioridades')

    if Prioridad.objects.filter(Prioridad__iexact=nombre).exists():
        messages.error(request, 'Esta prioridad ya existe.')
        return redirect('prioridades')

    Prioridad.objects.create(
        Prioridad=nombre,
        descripcion=descripcion,
        dias_resolucion=int(dias) if dias.isdigit() else 0
    )

    messages.success(request, 'Prioridad creada correctamente.')
    return redirect('prioridades')


@login_required
def prioridad_editar(request, item_id):
    prioridad = get_object_or_404(Prioridad, pk=item_id)

    if request.method == 'POST':
        nombre = request.POST.get('prioridad', '').strip()
        descripcion = request.POST.get('descripcion', '').strip() or None
        dias = request.POST.get('dias_resolucion', '0').strip()

        if not nombre:
            messages.error(request, 'El nombre de la prioridad es obligatorio.')
            return redirect('prioridades')

        if Prioridad.objects.filter(Prioridad__iexact=nombre).exclude(pk=item_id).exists():
            messages.error(request, 'Ya existe otra prioridad con ese nombre.')
            return redirect('prioridades')

        prioridad.Prioridad = nombre
        prioridad.descripcion = descripcion
        prioridad.dias_resolucion = int(dias) if dias.isdigit() else 0
        prioridad.save()

        messages.success(request, 'Prioridad actualizada correctamente.')

    return redirect('prioridades')

@login_required
def prioridad_eliminar(request, item_id):
    prioridad = get_object_or_404(Prioridad, pk=item_id)

    if request.method == 'POST':
        if ReclamacionInterna.objects.filter(prioridad=prioridad).exists():
            messages.error(
                request,
                'No se puede eliminar la prioridad porque tiene reclamaciones internas relacionadas.'
            )
        else:
            prioridad.delete()
            messages.success(request, 'Prioridad eliminada correctamente.')

    return redirect('prioridades')

def _reportes_filtered_query(request):
    queryset = ReclamacionInterna.objects.select_related(
        'prioridad',
        'area_responsable',
        'estatus',
        'usuario_creador'
    )

    search = request.GET.get('search', '').strip()
    area_id = request.GET.get('area')
    prioridad_id = request.GET.get('prioridad')
    estatus_id = request.GET.get('estatus')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    if search.isdigit():
        queryset = queryset.filter(id_folio=int(search))

    if area_id:
        queryset = queryset.filter(area_responsable_id=area_id)

    if prioridad_id:
        queryset = queryset.filter(prioridad_id=prioridad_id)

    if estatus_id:
        queryset = queryset.filter(estatus_id=estatus_id)

    if fecha_desde:
        queryset = queryset.filter(fecha_emision__gte=fecha_desde)

    if fecha_hasta:
        queryset = queryset.filter(fecha_emision__lte=fecha_hasta)

    return queryset.order_by('-id_folio')

@login_required
def reportes_reclamaciones_internas(request):
    if not request.user.puede_gestionar_reportes:
        messages.error(request, 'No tienes permisos para consultar reportes.')
        return redirect('home')

    queryset = _reportes_filtered_query(request)

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    retraso_map = {
        r.id_folio: calcular_dias_retraso(r)
        for r in page_obj.object_list
    }

    return render(request, 'reclamaciones_internas/reportes.html', {
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'total_results': paginator.count,
        'prioridades': Prioridad.objects.order_by('Prioridad'),
        'areas': Area.objects.order_by('nombre'),
        'estatus_list': EstatusReclamacionInterna.objects.order_by('id_estatus'),
        'selected_area': request.GET.get('area'),
        'selected_prioridad': request.GET.get('prioridad'),
        'selected_estatus': request.GET.get('estatus'),
        'fecha_desde': request.GET.get('fecha_desde', ''),
        'fecha_hasta': request.GET.get('fecha_hasta', ''),
        'search_query': request.GET.get('search', ''),
        'retraso_map': retraso_map,
        'today': date.today()
    })

@login_required
def reportes_exportar_csv(request):
    if not request.user.puede_gestionar_reportes:
        messages.error(request, 'No tienes permisos para consultar reportes.')
        return redirect('home')

    reclamaciones = _reportes_filtered_query(request)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"reporte_reclamaciones_internas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response)

    writer.writerow([
        'Folio',
        'Emisor',
        'Área',
        'Prioridad',
        'Estatus',
        'Fecha Emisión',
        'Fecha Compromiso',
        'Fecha Cierre',
        'Días Retraso',
        'Problemática',
        'Acción Correctiva',
        'Evidencia Resolución'
    ])

    for r in reclamaciones:
        writer.writerow([
            r.id_folio,
            r.emisor or '',
            r.area_responsable.nombre if r.area_responsable else '',
            r.prioridad.Prioridad if r.prioridad else '',
            r.estatus.descripcion if r.estatus else '',
            r.fecha_emision.strftime('%Y-%m-%d') if r.fecha_emision else '',
            r.fecha_compromiso.strftime('%Y-%m-%d') if r.fecha_compromiso else '',
            r.fecha_cierre.strftime('%Y-%m-%d') if r.fecha_cierre else '',
            calcular_dias_retraso(r),
            (r.problematica or '').replace('\n', ' '),
            (r.accion_correctiva or '').replace('\n', ' '),
            (r.evidencia_resolucion or '').replace('\n', ' ')
        ])

    return response


@login_required
def estatus_reclamaciones_internas(request):
    search_query = request.GET.get('search', '').strip()
    queryset = EstatusReclamacionInterna.objects.all()

    if search_query:
        queryset = queryset.filter(descripcion__icontains=search_query)

    queryset = queryset.order_by('id_estatus')
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    edit_id = request.GET.get('edit_id')
    edit_item = EstatusReclamacionInterna.objects.filter(pk=edit_id).first() if edit_id else None

    return render(request, 'reclamaciones_internas/estatus.html', {
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'edit_item': edit_item,
        'search_query': search_query,
        'total_results': paginator.count,
    })


@login_required
def estatus_crear(request):
    if request.method != 'POST':
        return redirect('estatus_reclamaciones_internas')

    descripcion = request.POST.get('descripcion', '').strip()

    if not descripcion:
        messages.error(request, 'La descripción del estatus es obligatoria.')
        return redirect('estatus_reclamaciones_internas')

    if EstatusReclamacionInterna.objects.filter(descripcion__iexact=descripcion).exists():
        messages.error(request, 'Este estatus ya existe.')
        return redirect('estatus_reclamaciones_internas')

    EstatusReclamacionInterna.objects.create(descripcion=descripcion)

    messages.success(request, 'Estatus creado correctamente.')
    return redirect('estatus_reclamaciones_internas')


@login_required
def estatus_editar(request, item_id):
    estatus = get_object_or_404(EstatusReclamacionInterna, id_estatus=item_id)

    if request.method == 'POST':
        descripcion = request.POST.get('descripcion', '').strip()

        if not descripcion:
            messages.error(request, 'La descripción del estatus es obligatoria.')
            return redirect('estatus_reclamaciones_internas')

        if EstatusReclamacionInterna.objects.filter(descripcion__iexact=descripcion).exclude(id_estatus=item_id).exists():
            messages.error(request, 'Ya existe otro estatus con esa descripción.')
            return redirect('estatus_reclamaciones_internas')

        estatus.descripcion = descripcion
        estatus.save()

        messages.success(request, 'Estatus actualizado correctamente.')

    return redirect('estatus_reclamaciones_internas')


@login_required
def estatus_eliminar(request, item_id):
    if request.method != 'POST':
        return redirect('estatus_reclamaciones_internas')

    estatus = get_object_or_404(EstatusReclamacionInterna, id_estatus=item_id)

    try:
        estatus.delete()
        messages.success(request, 'Estatus eliminado correctamente.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar este estatus porque está siendo utilizado por una reclamación.')

    return redirect('estatus_reclamaciones_internas')