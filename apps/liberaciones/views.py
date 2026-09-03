from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import EstatusLiberacion, Maquina, TipoLaminacion, Liberacion
from django.core.paginator import Paginator
from apps.clientes.models import Cliente
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.utils import timezone
from functools import wraps






def usuario_puede_ver_liberaciones(user):
    return (
        user.is_authenticated
        and user.is_active
        and user.puede_gestionar_liberaciones
    )


def requiere_acceso_liberaciones(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not usuario_puede_ver_liberaciones(request.user):
            messages.error(request, 'No tienes permisos para acceder a liberaciones.')
            return redirect('home')
        return view(request, *args, **kwargs)

    return wrapped


def requiere_gestion_liberaciones(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not usuario_puede_ver_liberaciones(request.user) or request.user.rol_id not in (1, 2, 4):
            messages.error(request, 'Tu rol no permite gestionar liberaciones.')
            return redirect('home')
        return view(request, *args, **kwargs)

    return wrapped





@login_required
@requiere_acceso_liberaciones
def liberaciones(request):
    return render(request, 'liberaciones/liberaciones.html')

@login_required
@requiere_acceso_liberaciones
def ultima_liberacion_maquina(request,pk):
    maquina=get_object_or_404(Maquina,id_maquina=pk)

    ultima=Liberacion.objects.filter(
        maquina=maquina
    ).select_related(
        'cliente','tipo_laminacion','estatus','usuario'
    ).order_by(
        '-fecha_liberacion',
        '-hora_liberacion',
        '-id'
    ).first()

    from django.http import JsonResponse

    if not ultima:
        return JsonResponse({
            'existe':False
        })

    return JsonResponse({
        'existe':True,
        'cliente_id':ultima.cliente_id,
        'cliente':ultima.cliente.nombre if ultima.cliente else '',
        'tipo_id':ultima.tipo_laminacion_id,
        'tipo':ultima.tipo_laminacion.especificacion if ultima.tipo_laminacion else '',
        'estatus_id':ultima.estatus_id,
        'estatus':ultima.estatus.descripcion_status if ultima.estatus else '',
        'usuario':ultima.usuario.nombre if ultima.usuario else '',
        'fecha':ultima.fecha_liberacion.strftime('%d/%m/%Y'),
        'hora':ultima.hora_liberacion.strftime('%H:%M'),
    })

@login_required
@requiere_gestion_liberaciones
def generar_liberacion(request):
    search_query=request.GET.get('search','').strip()

    registros=Liberacion.objects.select_related(
        'cliente','maquina','tipo_laminacion','estatus','usuario'
    ).order_by('-fecha_liberacion','-hora_liberacion','-id')

    if search_query:
        registros=registros.filter(
            Q(cliente__nombre__icontains=search_query) |
            Q(maquina__nombre__icontains=search_query) |
            Q(tipo_laminacion__especificacion__icontains=search_query) |
            Q(estatus__descripcion_status__icontains=search_query) |
            Q(motivo__icontains=search_query)
        )

    paginator=Paginator(registros,10)
    page_obj=paginator.get_page(request.GET.get('page'))

    maquinas=Maquina.objects.all().order_by('nombre')
    clientes=Cliente.objects.all().order_by('nombre')
    tipos_laminacion=TipoLaminacion.objects.all().order_by('especificacion')
    estatus_list=EstatusLiberacion.objects.all().order_by('id_estatus')

    return render(request,'liberaciones/generar_liberacion.html',{
        'page_obj':page_obj,
        'search_query':search_query,
        'maquinas':maquinas,
        'clientes':clientes,
        'tipos_laminacion':tipos_laminacion,
        'estatus_list':estatus_list,
    })


@login_required
@requiere_gestion_liberaciones
def liberacion_crear(request):
    if request.method!='POST':
        return redirect('generar_liberacion')

    maquina_id=request.POST.get('id_maquina')
    cliente_id=request.POST.get('id_cliente') or None
    tipo_id=request.POST.get('id_tipo_laminacion') or None
    estatus_id=request.POST.get('id_status')
    motivo=request.POST.get('motivo','').strip()

    if not maquina_id:
        messages.error(request,'Selecciona una máquina.')
        return redirect('generar_liberacion')

    if not estatus_id:
        messages.error(request,'Selecciona un estatus.')
        return redirect('generar_liberacion')

    maquina=get_object_or_404(Maquina,id_maquina=maquina_id)
    estatus=get_object_or_404(EstatusLiberacion,id_estatus=estatus_id)

    status_normalizado=estatus.descripcion_status.strip().upper()

    ultima=Liberacion.objects.filter(
        maquina=maquina
    ).order_by(
        '-fecha_liberacion',
        '-hora_liberacion',
        '-id'
    ).first()

    if status_normalizado!='SIN PLAN':
        if not cliente_id and ultima:
            cliente_id=ultima.cliente_id

        if not tipo_id and ultima:
            tipo_id=ultima.tipo_laminacion_id

        if not cliente_id:
            messages.error(request,'Selecciona un cliente.')
            return redirect('generar_liberacion')

        if not tipo_id:
            messages.error(request,'Selecciona un tipo de laminación.')
            return redirect('generar_liberacion')

        cliente=get_object_or_404(
            Cliente,
            id_cliente=cliente_id
        )

        tipo=get_object_or_404(
            TipoLaminacion,
            id_tipo_laminacion=tipo_id
        )

    else:
        cliente=None
        tipo=None

    ahora=timezone.localtime()

    Liberacion.objects.create(
        maquina=maquina,
        cliente=cliente,
        tipo_laminacion=tipo,
        estatus=estatus,
        fecha_liberacion=ahora.date(),
        hora_liberacion=ahora.time().replace(microsecond=0),
        motivo=motivo,
        usuario=request.user
    )

    messages.success(
        request,
        'Estado de máquina actualizado correctamente.'
    )

    return redirect('generar_liberacion')

@login_required
@requiere_gestion_liberaciones
def liberacion_editar(request, pk):
    registro = get_object_or_404(
        Liberacion,
        id=pk
    )

    if request.method != 'POST':
        return redirect('generar_liberacion')

    cliente_id = request.POST.get('id_cliente')
    maquina_id = request.POST.get('id_maquina')
    tipo_id = request.POST.get('id_tipo_laminacion')
    estatus_id = request.POST.get('id_status')
    fecha = request.POST.get('fecha_liberacion')
    hora = request.POST.get('hora_liberacion')
    motivo = request.POST.get('motivo', '').strip()

    if not all([
        cliente_id,
        maquina_id,
        tipo_id,
        estatus_id,
        fecha,
        hora,
        motivo
    ]):
        messages.error(
            request,
            'Completa todos los campos obligatorios.'
        )
        return redirect('generar_liberacion')

    registro.cliente = get_object_or_404(
        Cliente,
        id_cliente=cliente_id
    )

    registro.maquina = get_object_or_404(
        Maquina,
        id_maquina=maquina_id
    )

    registro.tipo_laminacion = get_object_or_404(
        TipoLaminacion,
        id_tipo_laminacion=tipo_id
    )

    registro.estatus = get_object_or_404(
        EstatusLiberacion,
        id_estatus=estatus_id
    )

    registro.fecha_liberacion = fecha
    registro.hora_liberacion = hora
    registro.motivo = motivo

    registro.save()

    messages.success(
        request,
        'Liberación actualizada correctamente.'
    )

    return redirect('generar_liberacion')

@login_required
@requiere_gestion_liberaciones
def liberacion_eliminar(request, pk):
    if request.method != 'POST':
        return redirect('generar_liberacion')

    registro = get_object_or_404(
        Liberacion,
        id=pk
    )

    registro.delete()

    messages.success(
        request,
        'Liberación eliminada correctamente.'
    )

    return redirect('generar_liberacion')

# =========================
# CLIENTES
# =========================

@login_required
@requiere_gestion_liberaciones
def clientes_liberaciones(request):
    search_query = request.GET.get('search', '').strip()
    clientes = Cliente.objects.all().order_by('id_cliente')

    if search_query:
        clientes = clientes.filter(nombre__icontains=search_query)

    paginator = Paginator(clientes, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    edit_item = None
    edit_id = request.GET.get('edit_id')

    if edit_id:
        edit_item = get_object_or_404(
            Cliente,
            id_cliente=edit_id
        )

    return render(request, 'liberaciones/clientes.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'edit_item': edit_item
    })


@login_required
@requiere_gestion_liberaciones
def cliente_liberacion_crear(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()

        if not nombre:
            messages.error(request, 'El nombre del cliente es obligatorio.')
            return redirect('clientes_liberaciones')

        if Cliente.objects.filter(nombre__iexact=nombre).exists():
            messages.error(request, 'Ese cliente ya existe.')
            return redirect('clientes_liberaciones')

        Cliente.objects.create(nombre=nombre)
        messages.success(request, 'Cliente creado correctamente.')

    return redirect('clientes_liberaciones')


@login_required
@requiere_gestion_liberaciones
def cliente_liberacion_editar(request, pk):
    item = get_object_or_404(
        Cliente,
        id_cliente=pk
    )

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()

        if not nombre:
            messages.error(request, 'El nombre del cliente es obligatorio.')
            return redirect(f'/liberaciones/clientes/?edit_id={pk}')

        if Cliente.objects.filter(
            nombre__iexact=nombre
        ).exclude(
            id_cliente=pk
        ).exists():
            messages.error(request, 'Ese cliente ya existe.')
            return redirect(f'/liberaciones/clientes/?edit_id={pk}')

        item.nombre = nombre
        item.save()

        messages.success(request, 'Cliente actualizado correctamente.')

    return redirect('clientes_liberaciones')


@login_required
@requiere_gestion_liberaciones
def cliente_liberacion_eliminar(request, pk):
    if request.method == 'POST':
        item = get_object_or_404(
            Cliente,
            id_cliente=pk
        )

        try:
            item.delete()
            messages.success(request, 'Cliente eliminado correctamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar porque el cliente está siendo utilizado.'
            )

    return redirect('clientes_liberaciones')



# =========================
# TIPOS DE LAMINACION 
# =========================

@login_required
@requiere_gestion_liberaciones
def tipos_laminacion(request):
    items = TipoLaminacion.objects.all().order_by('id_tipo_laminacion')
    edit_item = None
    edit_id = request.GET.get('edit_id')

    if edit_id:
        edit_item = get_object_or_404(
            TipoLaminacion,
            id_tipo_laminacion=edit_id
        )

    return render(request, 'liberaciones/tipos_laminacion.html', {
        'items': items,
        'edit_item': edit_item
    })


@login_required
@requiere_gestion_liberaciones
def tipo_laminacion_crear(request):
    if request.method == 'POST':
        especificacion = request.POST.get('especificacion', '').strip()

        if not especificacion:
            messages.error(request, 'La especificación es obligatoria.')
            return redirect('tipos_laminacion')

        if TipoLaminacion.objects.filter(
            especificacion__iexact=especificacion
        ).exists():
            messages.error(request, 'Ese tipo de laminación ya existe.')
            return redirect('tipos_laminacion')

        TipoLaminacion.objects.create(
            especificacion=especificacion
        )

        messages.success(
            request,
            'Tipo de laminación creado correctamente.'
        )

    return redirect('tipos_laminacion')


@login_required
@requiere_gestion_liberaciones
def tipo_laminacion_editar(request, pk):
    item = get_object_or_404(
        TipoLaminacion,
        id_tipo_laminacion=pk
    )

    if request.method == 'POST':
        especificacion = request.POST.get(
            'especificacion',
            ''
        ).strip()

        if not especificacion:
            messages.error(
                request,
                'La especificación es obligatoria.'
            )
            return redirect(
                f'/liberaciones/tipos-laminacion/?edit_id={pk}'
            )

        if TipoLaminacion.objects.filter(
            especificacion__iexact=especificacion
        ).exclude(
            id_tipo_laminacion=pk
        ).exists():
            messages.error(
                request,
                'Ese tipo de laminación ya existe.'
            )
            return redirect(
                f'/liberaciones/tipos-laminacion/?edit_id={pk}'
            )

        item.especificacion = especificacion
        item.save()

        messages.success(
            request,
            'Tipo de laminación actualizado correctamente.'
        )

    return redirect('tipos_laminacion')


@login_required
@requiere_gestion_liberaciones
def tipo_laminacion_eliminar(request, pk):
    if request.method == 'POST':
        item = get_object_or_404(
            TipoLaminacion,
            id_tipo_laminacion=pk
        )

        try:
            item.delete()
            messages.success(
                request,
                'Tipo de laminación eliminado correctamente.'
            )
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar porque está siendo utilizado.'
            )

    return redirect('tipos_laminacion')





@login_required
@requiere_acceso_liberaciones
def maquinas_status(request):
    from datetime import datetime
    from django.utils import timezone

    search_query=request.GET.get('search','').strip()
    maquinas=Maquina.objects.all().order_by('nombre')

    maquinas_estado=[]
    total_liberadas=0
    total_no_liberadas=0
    total_sin_plan=0

    for maquina in maquinas:
        liberacion=Liberacion.objects.filter(
            maquina=maquina
        ).select_related(
            'estatus',
            'tipo_laminacion',
            'usuario',
            'cliente'
        ).order_by(
            '-fecha_liberacion',
            '-hora_liberacion',
            '-id'
        ).first()

        if liberacion and liberacion.estatus:
            status=liberacion.estatus.descripcion_status.strip().upper()
        else:
            status='SIN PLAN'

        if status=='LIBERADO':
            color='verde'
            total_liberadas+=1
        elif status=='NO LIBERADO':
            color='rojo'
            total_no_liberadas+=1
        else:
            status='SIN PLAN'
            color='amarillo'
            total_sin_plan+=1

        if search_query:
            texto=search_query.lower()

            if (
                texto not in maquina.nombre.lower()
                and texto not in status.lower()
            ):
                continue

        maquinas_estado.append({
            'maquina':maquina,
            'liberacion':liberacion,
            'status':status,
            'color':color,
        })

    hoy=timezone.localdate()

    liberaciones_hoy=Liberacion.objects.filter(
        fecha_liberacion=hoy
    ).select_related(
        'maquina',
        'estatus',
        'usuario'
    )

    cambios_por_hora={hora:0 for hora in range(24)}

    for registro in liberaciones_hoy:
        if registro.hora_liberacion:
            cambios_por_hora[registro.hora_liberacion.hour]+=1

    horas_labels=[
        f'{hora:02d}:00'
        for hora in range(24)
    ]

    horas_data=[
        cambios_por_hora[hora]
        for hora in range(24)
    ]

    total_maquinas=(
        total_liberadas+
        total_no_liberadas+
        total_sin_plan
    )

    return render(
        request,
        'liberaciones/maquinas_status.html',
        {
            'maquinas_estado':maquinas_estado,
            'search_query':search_query,
            'total_maquinas':total_maquinas,
            'total_liberadas':total_liberadas,
            'total_no_liberadas':total_no_liberadas,
            'total_sin_plan':total_sin_plan,
            'cambios_hoy':liberaciones_hoy.count(),
            'horas_labels':horas_labels,
            'horas_data':horas_data,
        }
    )



# =========================
# MAQUINAS
# =========================

@login_required
@requiere_gestion_liberaciones
def maquinas_liberaciones(request):
    items = Maquina.objects.all().order_by('id_maquina')
    edit_item = None
    edit_id = request.GET.get('edit_id')

    if edit_id:
        edit_item = get_object_or_404(
            Maquina,
            id_maquina=edit_id
        )

    return render(
        request,
        'liberaciones/maquinas_l.html',
        {
            'items': items,
            'edit_item': edit_item
        }
    )


@login_required
@requiere_gestion_liberaciones
def maquina_liberacion_crear(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        if not nombre:
            messages.error(request, 'El nombre de la máquina es obligatorio.')
            return redirect('maquinas_liberaciones')

        if Maquina.objects.filter(nombre__iexact=nombre).exists():
            messages.error(request, 'Ya existe una máquina con ese nombre.')
            return redirect('maquinas_liberaciones')

        Maquina.objects.create(
            nombre=nombre,
            descripcion=descripcion or None
        )

        messages.success(request, 'Máquina creada correctamente.')

    return redirect('maquinas_liberaciones')


@login_required
@requiere_gestion_liberaciones
def maquina_liberacion_editar(request, pk):
    item = get_object_or_404(
        Maquina,
        id_maquina=pk
    )

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        if not nombre:
            messages.error(request, 'El nombre de la máquina es obligatorio.')
            return redirect(f'/liberaciones/maquinas/?edit_id={pk}')

        if Maquina.objects.filter(
            nombre__iexact=nombre
        ).exclude(
            id_maquina=pk
        ).exists():
            messages.error(request, 'Ya existe una máquina con ese nombre.')
            return redirect(f'/liberaciones/maquinas/?edit_id={pk}')

        item.nombre = nombre
        item.descripcion = descripcion or None
        item.save()

        messages.success(request, 'Máquina actualizada correctamente.')

    return redirect('maquinas_liberaciones')


@login_required
@requiere_gestion_liberaciones
def maquina_liberacion_eliminar(request, pk):
    if request.method == 'POST':
        item = get_object_or_404(
            Maquina,
            id_maquina=pk
        )

        try:
            item.delete()
            messages.success(request, 'Máquina eliminada correctamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar porque está siendo utilizada.'
            )

    return redirect('maquinas_liberaciones')


# =========================
# ESTATUS
# =========================

@login_required
@requiere_gestion_liberaciones
def estatus_liberaciones(request):
    items = EstatusLiberacion.objects.all().order_by('id_estatus')
    edit_item = None
    edit_id = request.GET.get('edit_id')

    if edit_id:
        edit_item = get_object_or_404(
            EstatusLiberacion,
            id_estatus=edit_id
        )

    return render(
        request,
        'liberaciones/status_liberaciones.html',
        {
            'items': items,
            'edit_item': edit_item
        }
    )


@login_required
@requiere_gestion_liberaciones
def estatus_liberacion_crear(request):
    if request.method == 'POST':
        descripcion = request.POST.get(
            'descripcion_status',
            ''
        ).strip()

        if not descripcion:
            messages.error(request, 'La descripción es obligatoria.')
            return redirect('estatus_liberaciones')

        if EstatusLiberacion.objects.filter(
            descripcion_status__iexact=descripcion
        ).exists():
            messages.error(request, 'Ese estatus ya existe.')
            return redirect('estatus_liberaciones')

        EstatusLiberacion.objects.create(
            descripcion_status=descripcion
        )

        messages.success(request, 'Estatus creado correctamente.')

    return redirect('estatus_liberaciones')


@login_required
@requiere_gestion_liberaciones
def estatus_liberacion_editar(request, pk):
    item = get_object_or_404(
        EstatusLiberacion,
        id_estatus=pk
    )

    if request.method == 'POST':
        descripcion = request.POST.get(
            'descripcion_status',
            ''
        ).strip()

        if not descripcion:
            messages.error(request, 'La descripción es obligatoria.')
            return redirect(f'/liberaciones/estatus/?edit_id={pk}')

        if EstatusLiberacion.objects.filter(
            descripcion_status__iexact=descripcion
        ).exclude(
            id_estatus=pk
        ).exists():
            messages.error(request, 'Ese estatus ya existe.')
            return redirect(f'/liberaciones/estatus/?edit_id={pk}')

        item.descripcion_status = descripcion
        item.save()

        messages.success(request, 'Estatus actualizado correctamente.')

    return redirect('estatus_liberaciones')


@login_required
@requiere_gestion_liberaciones
def estatus_liberacion_eliminar(request, pk):
    if request.method == 'POST':
        item = get_object_or_404(
            EstatusLiberacion,
            id_estatus=pk
        )

        try:
            item.delete()
            messages.success(request, 'Estatus eliminado correctamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar porque está siendo utilizado por una liberación.'
            )

    return redirect('estatus_liberaciones')




