from django.shortcuts import render
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from django.core.mail import EmailMessage
from apps.usuarios.models import Usuario

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.areas.models import Area
from apps.clientes.models import Cliente

from .models import (
    Categoria,
    Defecto,
    EstatusReclamacion,
    Ocurrencia,
    Reclamacion,
)

from .services import (
    actualizar_dias_retraso,
    actualizar_estatus_automatico,
    calcular_checklist,
    calcular_dias_retraso_actual,
)


# =========================================================================
# ESTATUS FIJOS DEL PIPELINE
# =========================================================================

ESTATUS_FIJOS = [
    (1, 'Confirmación'),
    (2, 'Contención (D0-D3)'),
    (3, 'CR y AC (D4-D7)'),
    (4, 'Cierre (D8)'),
    (5, 'Cerrado'),
]



def enviar_notificacion_nueva_reclamacion(reclamacion):
    areas=reclamacion.areas_involucradas.all()

    if not areas.exists():
        return

    usuarios=Usuario.objects.filter(
        area_id__in=areas.values_list('id_area',flat=True),
        puede_gestionar_reclamaciones=True,
        is_active=True
    ).exclude(
        email__isnull=True
    ).exclude(
        email=''
    ).distinct()

    destinatarios=list(
        usuarios.values_list('email',flat=True)
    )

    if not destinatarios:
        return

    areas_nombre=', '.join(
        areas.values_list('nombre',flat=True)
    )

    cliente=(
        reclamacion.cliente.nombre
        if reclamacion.cliente
        else 'N/A'
    )

    defecto=(
        reclamacion.defecto.descripcion
        if reclamacion.defecto
        else 'N/A'
    )

    asunto=f'Nueva Reclamación #{reclamacion.id_reporte_cliente or reclamacion.id}'

    cuerpo=f"""Hola,

Se ha registrado una nueva reclamación de cliente que involucra a tu área.

Reporte: {reclamacion.id_reporte_cliente or reclamacion.id}
Cliente: {cliente}
Áreas involucradas: {areas_nombre}
Fecha de reporte: {reclamacion.fecha_reporte}

Issue / Description:
{reclamacion.issue or 'Sin descripción registrada.'}

Defecto:
{defecto}

Por favor ingresa al sistema para revisar y dar seguimiento a la reclamación.
"""

    correo=EmailMessage(
        subject=asunto,
        body=cuerpo,
        to=destinatarios
    )

    correo.send(fail_silently=True)

def asegurar_estatus_fijos():
    """
    Garantiza que los cinco estatus del pipeline existan.

    Idealmente estos registros se pueden sembrar después mediante
    una migración de datos, pero esta función permite mantener el
    comportamiento que ya tenías en Flask.
    """

    for orden, descripcion in ESTATUS_FIJOS:
        EstatusReclamacion.objects.update_or_create(
            orden=orden,
            defaults={
                'descripcion_status': descripcion
            }
        )


# =========================================================================
# PERMISOS
# =========================================================================

def usuario_puede_ver_reclamaciones(user):
    """
    Comprueba que el usuario tenga permiso para entrar al módulo.
    """

    return (
        user.is_authenticated
        and user.is_active
        and user.puede_gestionar_reclamaciones
    )


def usuario_puede_modificar_reclamaciones(user):
    return usuario_puede_ver_reclamaciones(user) and user.rol_id in (1, 2)


# =========================================================================
# CONVERSIÓN DE FECHAS
# =========================================================================

def convertir_fecha(valor):
    """
    Convierte YYYY-MM-DD a date.

    Si el valor viene vacío regresa None.
    """

    if not valor:
        return None

    return datetime.strptime(
        valor,
        '%Y-%m-%d'
    ).date()


# =========================================================================
# VISTA PRINCIPAL DE RECLAMACIONES
# =========================================================================

@login_required
def reclamaciones(request):

    if not usuario_puede_ver_reclamaciones(request.user):
        messages.error(
            request,
            'No tienes autorización para acceder a este módulo.'
        )
        return redirect('home')

    asegurar_estatus_fijos()

    return render(
        request,
        'reclamaciones/reclamaciones.html'
    )


# =========================================================================
# CONTROLADOR DINÁMICO POR SECCIONES
# =========================================================================

@login_required
def reclamaciones_section(request, section):
    if not usuario_puede_ver_reclamaciones(request.user):
        messages.error(request,'No tienes autorización para acceder a este módulo.')
        return redirect('home')

    if request.method == 'POST' and not usuario_puede_modificar_reclamaciones(request.user):
        messages.error(request, 'Tu rol no permite modificar reclamaciones.')
        return redirect('reclamaciones_section', section=section)

    asegurar_estatus_fijos()
    edit_id=request.GET.get('edit_id')

    if section=='nuevo':
        if request.method=='POST':
            try:
                with transaction.atomic():
                    fecha_reporte=convertir_fecha(request.POST.get('fecha_reporte')) or date.today()
                    fecha_confirmacion=convertir_fecha(request.POST.get('fecha_confirmacion'))
                    fecha_contencion=convertir_fecha(request.POST.get('fecha_contencion'))
                    fecha_CR_AC=convertir_fecha(request.POST.get('fecha_CR_AC'))
                    fecha_cierre=convertir_fecha(request.POST.get('fecha_cierre'))

                    if fecha_cierre and not (fecha_confirmacion and fecha_contencion and fecha_CR_AC):
                        messages.error(request,'No puedes registrar el Cierre (D8) si Confirmación, Contención y CR y AC no están completadas.')
                        return redirect('reclamaciones_section',section='nuevo')

                    cantidad_kg=request.POST.get('cantidad_kg','').strip() or None

                    nueva_reclamacion=Reclamacion(
                        id_reporte_cliente=request.POST.get('id_reporte_cliente','').strip(),
                        issue=request.POST.get('issue','').strip(),
                        defecto_id=request.POST.get('id_defecto'),
                        categoria_id=request.POST.get('id_categoria'),
                        ocurrencia_id=request.POST.get('id_ocurrencia'),
                        cliente_id=request.POST.get('id_cliente') or None,
                        numero_contenedor=request.POST.get('numero_contenedor','').strip() or None,
                        numero_parte=request.POST.get('numero_parte','').strip() or None,
                        lote=request.POST.get('lote','').strip() or None,
                        cantidad_kg=cantidad_kg,
                        causa_raiz=request.POST.get('causa_raiz','').strip() or None,
                        fecha_reporte=fecha_reporte,
                        fecha_confirmacion=fecha_confirmacion,
                        fecha_contencion=fecha_contencion,
                        fecha_CR_AC=fecha_CR_AC,
                        fecha_cierre=fecha_cierre,
                        periodo=date.today().strftime('%Y-P%m')
                    )

                    if request.FILES.get('imagen_defecto'):
                        nueva_reclamacion.imagen_defecto=request.FILES['imagen_defecto']

                    actualizar_estatus_automatico(nueva_reclamacion)
                    actualizar_dias_retraso(nueva_reclamacion)
                    nueva_reclamacion.save()

                    # ÁREAS INVOLUCRADAS
                    areas_ids=request.POST.getlist('areas_involucradas')
                    if areas_ids:
                        nueva_reclamacion.areas_involucradas.set(
                            Area.objects.filter(id_area__in=areas_ids)
                        )

                    # PDF DE CIERRE
                    archivo_pdf=request.FILES.get('archivo_cierre_pdf')
                    if archivo_pdf:
                        if not archivo_pdf.name.lower().endswith('.pdf'):
                            raise ValueError('El archivo de cierre debe ser PDF.')

                        timestamp=datetime.now().strftime('%Y%m%d_%H%M%S')
                        ruta_pdf=f'reclamaciones/cierres/cierre_{timestamp}_{archivo_pdf.name}'
                        nombre_guardado=default_storage.save(ruta_pdf,archivo_pdf)
                        nueva_reclamacion.archivo_cierre_pdf=nombre_guardado
                        nueva_reclamacion.save(update_fields=['archivo_cierre_pdf'])

                    # ENVIAR CORREO SOLO CUANDO LA TRANSACCIÓN SE GUARDE
                    if areas_ids:
                        reclamacion_id=nueva_reclamacion.id
                        transaction.on_commit(
                            lambda reclamacion_id=reclamacion_id: enviar_notificacion_nueva_reclamacion(
                                Reclamacion.objects.get(id=reclamacion_id)
                            )
                        )

                messages.success(request,'Reclamación registrada exitosamente.')

            except Exception as e:
                messages.error(request,f'Error al guardar: {e}')

            return redirect('reclamaciones_section',section='nuevo')

        registros=(
            Reclamacion.objects
            .select_related('defecto','categoria','ocurrencia','cliente','estatus')
            .prefetch_related('areas_involucradas')
            .order_by('-id')[:20]
        )

        checklists={registro.id:calcular_checklist(registro) for registro in registros}
        retrasos={registro.id:calcular_dias_retraso_actual(registro) for registro in registros}

        context={
            'registros':registros,
            'checklists':checklists,
            'retrasos':retrasos,
            'categorias':Categoria.objects.order_by('categoria'),
            'defectos':Defecto.objects.order_by('descripcion'),
            'ocurrencias':Ocurrencia.objects.order_by('ocurrencia'),
            'estatus_list':EstatusReclamacion.objects.order_by('orden'),
            'clientes':Cliente.objects.order_by('nombre'),
            'areas':Area.objects.all().order_by('nombre'),
        }
        return render(request,'reclamaciones/generar_registro.html',context)

    mapping={
        'categorias':(Categoria,'reclamaciones/categorias.html','categoria'),
        'defectos':(Defecto,'reclamaciones/defectos.html','descripcion'),
        'ocurrencias':(Ocurrencia,'reclamaciones/ocurrencias.html','ocurrencia'),
        'estatus':(EstatusReclamacion,'reclamaciones/estatus.html','descripcion_status'),
        'clientes':(Cliente,'reclamaciones/clientes.html','nombre'),
    }

    if section in mapping:
        model,template,field=mapping[section]
        search_query=request.GET.get('search','').strip()
        queryset=model.objects.all()

        if search_query:
            queryset=queryset.filter(**{f'{field}__icontains':search_query})

        queryset=queryset.order_by(field)
        paginator=Paginator(queryset,20)
        page_obj=paginator.get_page(request.GET.get('page',1))
        edit_item=model.objects.filter(pk=edit_id).first() if edit_id else None

        context={
            'items':page_obj.object_list,
            'page_obj':page_obj,
            'edit_item':edit_item,
            'search_query':search_query,
            'total_results':paginator.count,
            'section':section,
        }
        return render(request,template,context)

    return redirect('reclamaciones_section',section='nuevo')

# =========================================================================
# CRUD DE CATÁLOGOS
# =========================================================================

@login_required
def reclamaciones_actions(
    request,
    section,
    action_type,
    item_id=None
):

    if not usuario_puede_ver_reclamaciones(request.user):
        messages.error(
            request,
            'No tienes autorización.'
        )
        return redirect('home')

    if not usuario_puede_modificar_reclamaciones(request.user):
        messages.error(request, 'Tu rol no permite gestionar este catálogo.')
        return redirect('reclamaciones_section', section=section)

    if request.method != 'POST':
        return redirect(
            'reclamaciones_section',
            section=section
        )

    # ---------------------------------------------------------------------
    # Los estatus no se crean ni eliminan manualmente
    # ---------------------------------------------------------------------

    if (
        section == 'estatus'
        and action_type in (
            'crear',
            'eliminar'
        )
    ):
        messages.warning(
            request,
            (
                'Los estatus del pipeline son fijos. '
                'Solo puedes modificar su descripción.'
            )
        )

        return redirect(
            'reclamaciones_section',
            section=section
        )

    model_mapping = {
        'categorias': (
            Categoria,
            'categoria'
        ),

        'defectos': (
            Defecto,
            'descripcion'
        ),

        'ocurrencias': (
            Ocurrencia,
            'ocurrencia'
        ),

        'estatus': (
            EstatusReclamacion,
            'descripcion_status'
        ),

        'clientes': (
            Cliente,
            'nombre'
        ),
    }

    if section not in model_mapping:

        return redirect(
            'reclamaciones_section',
            section='nuevo'
        )

    model, field_name = model_mapping[section]

    # ---------------------------------------------------------------------
    # CREAR
    # ---------------------------------------------------------------------

    if action_type == 'crear':

        value = request.POST.get(
            field_name,
            ''
        ).strip()

        if not value:

            messages.error(
                request,
                'El campo requerido no puede estar vacío.'
            )

            return redirect(
                'reclamaciones_section',
                section=section
            )

        if model.objects.filter(
            **{
                field_name: value
            }
        ).exists():

            messages.error(
                request,
                'Este registro ya existe.'
            )

        else:

            model.objects.create(
                **{
                    field_name: value
                }
            )

            messages.success(
                request,
                'Registro creado correctamente.'
            )

    # ---------------------------------------------------------------------
    # EDITAR
    # ---------------------------------------------------------------------

    elif (
        action_type == 'editar'
        and item_id
    ):

        obj = get_object_or_404(
            model,
            pk=item_id
        )

        value = request.POST.get(
            field_name,
            ''
        ).strip()

        if not value:

            messages.error(
                request,
                'El campo requerido no puede estar vacío.'
            )

            return redirect(
                'reclamaciones_section',
                section=section
            )

        filtros = {
            field_name: value
        }

        existing = (
            model.objects
            .filter(**filtros)
            .exclude(pk=item_id)
            .exists()
        )

        if existing:

            messages.error(
                request,
                'Ya existe otro registro con ese valor.'
            )

        else:

            setattr(
                obj,
                field_name,
                value
            )

            obj.save()

            messages.success(
                request,
                'Registro actualizado correctamente.'
            )

    # ---------------------------------------------------------------------
    # ELIMINAR
    # ---------------------------------------------------------------------

    elif (
        action_type == 'eliminar'
        and item_id
    ):

        obj = get_object_or_404(
            model,
            pk=item_id
        )

        try:

            obj.delete()

            messages.success(
                request,
                'Registro eliminado correctamente.'
            )

        except ProtectedError:

            messages.error(
                request,
                (
                    'No se puede eliminar el registro '
                    'porque tiene información relacionada.'
                )
            )

    return redirect(
        'reclamaciones_section',
        section=section
    )


# =========================================================================
# EDITAR UNA RECLAMACIÓN
# =========================================================================

@login_required
def reclamaciones_editar(
    request,
    item_id
):

    if not usuario_puede_ver_reclamaciones(request.user):
        messages.error(
            request,
            'No tienes autorización.'
        )
        return redirect('home')

    if request.method != 'POST':
        return redirect(
            'reclamaciones_section',
            section='nuevo'
        )

    registro = get_object_or_404(
        Reclamacion,
        pk=item_id
    )

    try:

        with transaction.atomic():

            # -------------------------------------------------------------
            # Fechas
            # -------------------------------------------------------------

            fecha_reporte = (
                convertir_fecha(
                    request.POST.get('fecha_reporte')
                )
                or registro.fecha_reporte
            )

            fecha_confirmacion = convertir_fecha(
                request.POST.get('fecha_confirmacion')
            )

            fecha_contencion = convertir_fecha(
                request.POST.get('fecha_contencion')
            )

            fecha_CR_AC = convertir_fecha(
                request.POST.get('fecha_CR_AC')
            )

            fecha_cierre = convertir_fecha(
                request.POST.get('fecha_cierre')
            )

            # -------------------------------------------------------------
            # Validación de cierre
            # -------------------------------------------------------------

            if fecha_cierre and not (
                fecha_confirmacion
                and fecha_contencion
                and fecha_CR_AC
            ):

                messages.error(
                    request,
                    (
                        'No puedes cerrar la reclamación '
                        'si faltan etapas anteriores.'
                    )
                )

                return redirect(
                    'reclamaciones_section',
                    section='nuevo'
                )

            # -------------------------------------------------------------
            # Datos
            # -------------------------------------------------------------

            registro.id_reporte_cliente = request.POST.get(
                'id_reporte_cliente',
                ''
            ).strip()

            registro.issue = request.POST.get(
                'issue',
                ''
            ).strip()

            registro.defecto_id = request.POST.get(
                'id_defecto'
            )

            registro.categoria_id = request.POST.get(
                'id_categoria'
            )

            registro.ocurrencia_id = request.POST.get(
                'id_ocurrencia'
            )

            registro.cliente_id = (
                request.POST.get('id_cliente')
                or None
            )

            registro.numero_contenedor = (
                request.POST.get(
                    'numero_contenedor',
                    ''
                ).strip()
                or None
            )

            registro.numero_parte = (
                request.POST.get(
                    'numero_parte',
                    ''
                ).strip()
                or None
            )

            registro.lote = (
                request.POST.get(
                    'lote',
                    ''
                ).strip()
                or None
            )

            cantidad = request.POST.get(
                'cantidad_kg',
                ''
            ).strip()

            registro.cantidad_kg = (
                cantidad
                or None
            )

            registro.causa_raiz = (
                request.POST.get(
                    'causa_raiz',
                    ''
                ).strip()
                or None
            )

            registro.fecha_reporte = fecha_reporte
            registro.fecha_confirmacion = fecha_confirmacion
            registro.fecha_contencion = fecha_contencion
            registro.fecha_CR_AC = fecha_CR_AC
            registro.fecha_cierre = fecha_cierre

            # -------------------------------------------------------------
            # Nueva imagen
            # -------------------------------------------------------------

            imagen = request.FILES.get(
                'imagen_defecto'
            )

            if imagen:
                registro.imagen_defecto = imagen

            # -------------------------------------------------------------
            # Nuevo PDF
            # -------------------------------------------------------------

            archivo_pdf = request.FILES.get(
                'archivo_cierre_pdf'
            )

            if archivo_pdf:

                if not archivo_pdf.name.lower().endswith(
                    '.pdf'
                ):
                    raise ValueError(
                        'El archivo de cierre debe ser PDF.'
                    )

                # Eliminar anterior
                if (
                    registro.archivo_cierre_pdf
                    and default_storage.exists(
                        registro.archivo_cierre_pdf
                    )
                ):
                    default_storage.delete(
                        registro.archivo_cierre_pdf
                    )

                timestamp = datetime.now().strftime(
                    '%Y%m%d_%H%M%S'
                )

                ruta_pdf = (
                    f'reclamaciones/cierres/'
                    f'cierre_{timestamp}_{archivo_pdf.name}'
                )

                registro.archivo_cierre_pdf = (
                    default_storage.save(
                        ruta_pdf,
                        archivo_pdf
                    )
                )

            # -------------------------------------------------------------
            # Pipeline
            # -------------------------------------------------------------

            actualizar_estatus_automatico(
                registro
            )

            actualizar_dias_retraso(
                registro
            )

            registro.save()

            # -------------------------------------------------------------
            # Áreas involucradas
            # -------------------------------------------------------------

            areas_ids = request.POST.getlist(
                'areas_involucradas'
            )

            registro.areas_involucradas.set(
                Area.objects.filter(
                    id_area__in=areas_ids
                )
            )

        messages.success(
            request,
            'Reclamación actualizada correctamente.'
        )

    except Exception as e:

        messages.error(
            request,
            f'Error al actualizar: {e}'
        )

    return redirect(
        'reclamaciones_section',
        section='nuevo'
    )


# =========================================================================
# ELIMINAR UNA RECLAMACIÓN
# =========================================================================

@login_required
def reclamaciones_eliminar(
    request,
    item_id
):

    if not usuario_puede_ver_reclamaciones(request.user):
        messages.error(
            request,
            'No tienes autorización.'
        )
        return redirect('home')

    if not usuario_puede_modificar_reclamaciones(request.user):
        messages.error(request, 'Tu rol no permite eliminar reclamaciones.')
        return redirect('reclamaciones_section', section='nuevo')

    if request.method != 'POST':

        return redirect(
            'reclamaciones_section',
            section='nuevo'
        )

    registro = get_object_or_404(
        Reclamacion,
        pk=item_id
    )

    try:

        # -----------------------------------------------------------------
        # Eliminar archivos
        # -----------------------------------------------------------------

        if registro.imagen_defecto:

            try:
                registro.imagen_defecto.delete(
                    save=False
                )
            except Exception:
                pass

        if (
            registro.archivo_cierre_pdf
            and default_storage.exists(
                registro.archivo_cierre_pdf
            )
        ):
            default_storage.delete(
                registro.archivo_cierre_pdf
            )

        registro.delete()

        messages.success(
            request,
            'Reclamación eliminada correctamente.'
        )

    except Exception as e:

        messages.error(
            request,
            f'No se pudo eliminar: {e}'
        )

    return redirect(
        'reclamaciones_section',
        section='nuevo'
    )


# =========================================================================
# QUERY PARA FILTROS / REPORTES
# =========================================================================

def construir_query_reclamaciones(params):

    queryset = (
        Reclamacion.objects
        .select_related(
            'cliente',
            'estatus',
            'defecto',
            'categoria',
            'ocurrencia',
        )
        .prefetch_related(
            'areas_involucradas'
        )
    )

    fecha_desde = params.get(
        'fecha_desde'
    )

    fecha_hasta = params.get(
        'fecha_hasta'
    )

    if fecha_desde:
        queryset = queryset.filter(
            fecha_reporte__gte=fecha_desde
        )

    if fecha_hasta:
        queryset = queryset.filter(
            fecha_reporte__lte=fecha_hasta
        )

    if params.get('id_cliente'):
        queryset = queryset.filter(
            cliente_id=params.get(
                'id_cliente'
            )
        )

    if params.get('id_estatus'):
        queryset = queryset.filter(
            estatus_id=params.get(
                'id_estatus'
            )
        )

    if params.get('id_defecto'):
        queryset = queryset.filter(
            defecto_id=params.get(
                'id_defecto'
            )
        )

    if params.get('id_categoria'):
        queryset = queryset.filter(
            categoria_id=params.get(
                'id_categoria'
            )
        )

    if params.get('id_ocurrencia'):
        queryset = queryset.filter(
            ocurrencia_id=params.get(
                'id_ocurrencia'
            )
        )

    # ---------------------------------------------------------------------
    # NUEVO: área involucrada
    # ---------------------------------------------------------------------

    if params.get('id_area'):
        queryset = queryset.filter(
            areas_involucradas__id_area=params.get(
                'id_area'
            )
        )

    numero_contenedor = params.get(
        'numero_contenedor',
        ''
    ).strip()

    if numero_contenedor:
        queryset = queryset.filter(
            numero_contenedor__icontains=numero_contenedor
        )

    numero_parte = params.get(
        'numero_parte',
        ''
    ).strip()

    if numero_parte:
        queryset = queryset.filter(
            numero_parte__icontains=numero_parte
        )

    lote = params.get(
        'lote',
        ''
    ).strip()

    if lote:
        queryset = queryset.filter(
            lote__icontains=lote
        )

    periodo = params.get(
        'periodo',
        ''
    ).strip()

    if periodo:
        queryset = queryset.filter(
            periodo__icontains=periodo
        )

    causa_raiz = params.get(
        'causa_raiz',
        ''
    ).strip()

    if causa_raiz:
        queryset = queryset.filter(
            causa_raiz__icontains=causa_raiz
        )

    return queryset.distinct().order_by(
        '-fecha_reporte'
    )


# =========================================================================
# REPORTES
# =========================================================================

@login_required
def reclamaciones_reportes(request):

    if not usuario_puede_ver_reclamaciones(request.user):

        messages.error(
            request,
            'No tienes autorización.'
        )

        return redirect('home')

    if not request.user.puede_gestionar_reportes:
        messages.error(request, 'No tienes permisos para consultar reportes.')
        return redirect('home')

    filtros = {
        'fecha_desde': request.GET.get(
            'fecha_desde',
            ''
        ),

        'fecha_hasta': request.GET.get(
            'fecha_hasta',
            ''
        ),

        'id_cliente': request.GET.get(
            'id_cliente',
            ''
        ),

        'id_estatus': request.GET.get(
            'id_estatus',
            ''
        ),

        'id_defecto': request.GET.get(
            'id_defecto',
            ''
        ),

        'id_categoria': request.GET.get(
            'id_categoria',
            ''
        ),

        'id_ocurrencia': request.GET.get(
            'id_ocurrencia',
            ''
        ),

        'id_area': request.GET.get(
            'id_area',
            ''
        ),

        'numero_contenedor': request.GET.get(
            'numero_contenedor',
            ''
        ),

        'numero_parte': request.GET.get(
            'numero_parte',
            ''
        ),

        'lote': request.GET.get(
            'lote',
            ''
        ),

        'periodo': request.GET.get(
            'periodo',
            ''
        ),
    }

    registros = list(
        construir_query_reclamaciones(
            request.GET
        )
    )

    retrasos = {
        r.id: calcular_dias_retraso_actual(r)
        for r in registros
    }

    total_registros = len(registros)

    total_kg = sum(
        r.cantidad_kg or 0
        for r in registros
    )

    total_abiertas = sum(
        1
        for r in registros
        if r.estatus
        and r.estatus.orden < 5
    )

    total_cerradas = sum(
        1
        for r in registros
        if r.estatus
        and r.estatus.orden == 5
    )

    retrasos_positivos = [
        dias
        for dias in retrasos.values()
        if dias > 0
    ]

    promedio_retraso = (
        sum(retrasos_positivos)
        / len(retrasos_positivos)
        if retrasos_positivos
        else 0
    )

    kpis = {
        'total_registros': total_registros,
        'total_kg': total_kg,
        'total_abiertas': total_abiertas,
        'total_cerradas': total_cerradas,
        'promedio_retraso': promedio_retraso,
    }

    context = {
        'registros': registros,
        'retrasos': retrasos,
        'kpis': kpis,
        'filtros': filtros,
        'clientes': Cliente.objects.order_by('nombre'),
        'estatus_list': EstatusReclamacion.objects.order_by('orden'),
        'defectos': Defecto.objects.order_by('descripcion'),
        'categorias': Categoria.objects.order_by('categoria'),
        'ocurrencias': Ocurrencia.objects.order_by('ocurrencia'),
        'areas': Area.objects.order_by('nombre'),
    }

    return render(
        request,
        'reclamaciones/reportes.html',
        context
    )


# =========================================================================
# PDF DE REPORTES
# =========================================================================

@login_required
def reclamaciones_reportes_pdf(request):
    if not usuario_puede_ver_reclamaciones(request.user):
        messages.error(request, 'No tienes autorización.')
        return redirect('home')

    if not request.user.puede_gestionar_reportes:
        messages.error(request, 'No tienes permisos para consultar reportes.')
        return redirect('home')

    registros = construir_query_reclamaciones(request.GET)
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
    )

    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        'titulo',
        parent=styles['Heading1'],
        alignment=TA_LEFT,
        fontSize=16,
    )

    subtitulo_style = ParagraphStyle(
        'subtitulo',
        parent=styles['Normal'],
        alignment=TA_LEFT,
        fontSize=9,
        textColor=colors.grey,
    )

    elementos = [
        Paragraph('Reporte de Reclamaciones', titulo_style),
        Paragraph(
            f'Generado el {date.today().strftime("%d/%m/%Y")} — {registros.count()} registro(s)',
            subtitulo_style
        ),
        Spacer(1, 8),
    ]

    encabezados = [
        'ID Reporte',
        'Cliente',
        'Issue',
        'Defecto',
        'Estatus',
        'F. Reporte',
        'F. Confirmación',
        'Días Retraso',
        'Periodo',
    ]

    data = [encabezados]

    for reclamacion in registros:
        data.append([
            reclamacion.id_reporte_cliente or '',
            reclamacion.cliente.nombre if reclamacion.cliente else '',
            (reclamacion.issue or '')[:40],
            reclamacion.defecto.descripcion if reclamacion.defecto else '',
            reclamacion.estatus.descripcion_status if reclamacion.estatus else '',
            reclamacion.fecha_reporte.strftime('%d/%m/%Y') if reclamacion.fecha_reporte else '',
            reclamacion.fecha_confirmacion.strftime('%d/%m/%Y') if reclamacion.fecha_confirmacion else '',
            str(calcular_dias_retraso_actual(reclamacion)),
            reclamacion.periodo or '',
        ])

    tabla = Table(data, repeatRows=1)

    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    elementos.append(tabla)
    doc.build(elementos)
    buffer.seek(0)

    descargar = request.GET.get('download')
    disposition = 'attachment' if descargar else 'inline'

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'{disposition}; filename="reporte_reclamaciones.pdf"'
    )

    return response