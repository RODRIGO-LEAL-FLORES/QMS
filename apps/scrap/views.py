from functools import wraps
from decimal import Decimal,InvalidOperation
from datetime import datetime,date,time
from io import BytesIO
import logging
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.http import JsonResponse,HttpResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from reportlab.lib.pagesizes import landscape,A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Table,TableStyle,Paragraph,Spacer,HRFlowable,Image,PageBreak

from .models import Scrap,Operador,Turno,DefectoScrap,ClasificacionScrap,Supervisor,TipoAcero,EstatusScrap
from apps.liberaciones.models import Maquina,TipoLaminacion
from apps.clientes.models import Cliente
from apps.usuarios.models import Usuario

logger=logging.getLogger(__name__)
LIMITE_NG_KG=500


# ============================================================
# SEGURIDAD
# ============================================================

def requiere_gestion_scrap(view_func):
    @wraps(view_func)
    def wrapper(request,*args,**kwargs):
        if not request.user.is_authenticated or not request.user.puede_gestionar_scrap:
            messages.error(request,'No tienes permisos para acceder al módulo de Scrap.')
            return redirect('home')
        return view_func(request,*args,**kwargs)
    return wrapper


# ============================================================
# UTILIDADES
# ============================================================

def decimal_post(request,nombre,default='0'):
    valor=(request.POST.get(nombre) or default).strip()
    try:
        return Decimal(valor)
    except (InvalidOperation,TypeError,ValueError):
        return Decimal(default)


def detectar_turno(hora_obj):
    for turno in Turno.objects.all():
        if turno.hora_inicio<=turno.hora_fin:
            if turno.hora_inicio<=hora_obj<turno.hora_fin:
                return turno
        else:
            if hora_obj>=turno.hora_inicio or hora_obj<turno.hora_fin:
                return turno
    return None


def construir_fecha_registro(fecha_str=None,hora_str=None,fecha_actual=None):
    ahora=timezone.localtime()

    if fecha_str and hora_str:
        dt=datetime.strptime(f'{fecha_str} {hora_str}','%Y-%m-%d %H:%M')
    elif fecha_str:
        hora_base=timezone.localtime(fecha_actual).time() if fecha_actual else ahora.time()
        dt=datetime.combine(datetime.strptime(fecha_str,'%Y-%m-%d').date(),hora_base.replace(tzinfo=None))
    elif hora_str:
        fecha_base=timezone.localtime(fecha_actual).date() if fecha_actual else ahora.date()
        dt=datetime.combine(fecha_base,datetime.strptime(hora_str,'%H:%M').time())
    else:
        return ahora

    if timezone.is_naive(dt):
        dt=timezone.make_aware(dt,timezone.get_current_timezone())

    return dt


# ============================================================
# ALERTA DE SCRAP NG
# ============================================================

def scrap_ticket_notification(registro):
    if not registro.cantidad_ng or registro.cantidad_ng<=LIMITE_NG_KG:
        return

    usuarios=Usuario.objects.filter(
        puede_gestionar_scrap=True,
        is_active=True
    ).exclude(email__isnull=True).exclude(email='').distinct()

    destinatarios=list(usuarios.values_list('email',flat=True))
    if not destinatarios:
        return

    maquina=registro.maquina.nombre if registro.maquina else 'N/A'
    operador=registro.operador.nombre if registro.operador else 'N/A'
    defecto=registro.defecto.defecto if registro.defecto else 'N/A'
    cliente=registro.cliente.nombre if registro.cliente else 'N/A'

    if registro.fecha_registro:
        fecha=timezone.localtime(registro.fecha_registro).strftime('%Y-%m-%d %H:%M')
    else:
        fecha='N/A'

    asunto=f'Alerta de Scrap — Registro #{registro.id} excede el límite de NG'

    cuerpo=f"""Hola,

Un registro de Scrap ha sobrepasado el límite permitido de {LIMITE_NG_KG} KG en peso NG.

Registro: #{registro.id}
Máquina: {maquina}
Operador: {operador}
Defecto: {defecto}
Cliente: {cliente}
Lote: {registro.lote or 'N/A'}

Peso total: {registro.peso or 0} kg
Cantidad NG: {registro.cantidad_ng or 0} kg
Fecha de registro: {fecha}

Por favor ingresa al sistema para revisar este registro.
"""

    EmailMessage(
        subject=asunto,
        body=cuerpo,
        to=destinatarios
    ).send(fail_silently=True)


# ============================================================
# MENÚ PRINCIPAL
# ============================================================

@login_required
def scrap(request):
    if not request.user.puede_gestionar_scrap:
        messages.error(request,'No tienes autorización para acceder al módulo de Scrap.')
        return redirect('home')

    return render(request,'scrap/scrap.html')


# ============================================================
# CONTROLADOR PRINCIPAL
# ============================================================

@login_required
@requiere_gestion_scrap
def scrap_section(request,section):
    edit_id=request.GET.get('edit_id')

    # ========================================================
    # NUEVO REGISTRO DE SCRAP
    # ========================================================

    if section=='nuevo':
        if request.method=='POST':
            hora_manual=(request.POST.get('hora_registro') or '').strip()
            fecha_manual=(request.POST.get('fecha_registro') or '').strip()

            try:
                fecha_final=construir_fecha_registro(
                    fecha_manual or None,
                    hora_manual or None
                )

                hora_turno=timezone.localtime(fecha_final).time().replace(tzinfo=None)
                turno_det=detectar_turno(hora_turno)

                maquina=get_object_or_404(Maquina,id_maquina=request.POST.get('id_maquina'))
                operador=get_object_or_404(Operador,id_operador=request.POST.get('id_operador'))
                defecto=get_object_or_404(DefectoScrap,id_defecto_scrap=request.POST.get('id_defecto_scrap'))
                laminacion=get_object_or_404(TipoLaminacion,id_tipo_laminacion=request.POST.get('id_tipo_laminacion'))
                clasificacion=get_object_or_404(ClasificacionScrap,id_clasificacion=request.POST.get('id_clasificacion'))
                supervisor=get_object_or_404(Supervisor,id_supervisor=request.POST.get('id_supervisor'))
                cliente=get_object_or_404(Cliente,id_cliente=request.POST.get('id_cliente'))
                tipo_acero=get_object_or_404(TipoAcero,id_tipo_acero=request.POST.get('id_tipo_acero'))
                estatus=get_object_or_404(EstatusScrap,id_estatus_scrap=request.POST.get('id_estatus_scrap'))

                nuevo_registro=Scrap.objects.create(
                    maquina=maquina,
                    operador=operador,
                    turno=turno_det,
                    defecto=defecto,
                    tipo_laminacion=laminacion,
                    clasificacion=clasificacion,
                    supervisor=supervisor,
                    cliente=cliente,
                    tipo_acero=tipo_acero,
                    estatus=estatus,
                    numero_parte=(request.POST.get('numero_parte') or '').strip(),
                    lote=(request.POST.get('lote') or '').strip(),
                    peso=decimal_post(request,'peso'),
                    cantidad_retrabajado=decimal_post(request,'cantidad_retrabajado'),
                    cantidad_ng=decimal_post(request,'cantidad_ng'),
                    usuario_registro=request.user,
                    fecha_registro=fecha_final
                )

                messages.success(request,'Registro generado exitosamente.')

                try:
                    scrap_ticket_notification(nuevo_registro)
                except Exception as e:
                    logger.exception('Error enviando alerta de Scrap: %s',e)

            except Exception as e:
                messages.error(request,f'Error al guardar: {e}')

            return redirect('scrap_section',section='nuevo')

        registros_qs=Scrap.objects.select_related(
            'maquina','operador','turno','defecto','tipo_laminacion',
            'clasificacion','supervisor','cliente','tipo_acero',
            'estatus','usuario_registro'
        ).order_by('-id')

        from django.core.paginator import Paginator
        paginator=Paginator(registros_qs,10)
        page_obj=paginator.get_page(request.GET.get('page'))

        return render(request,'scrap/generar_registro.html',{
            'registros':page_obj.object_list,
            'pagination':page_obj,
            'page_obj':page_obj,
            'maquinas':Maquina.objects.all().order_by('nombre'),
            'operadores':Operador.objects.all().order_by('nombre'),
            'turnos':Turno.objects.all().order_by('nombre_turno'),
            'defectos':DefectoScrap.objects.all().order_by('defecto'),
            'clasificaciones':ClasificacionScrap.objects.all().order_by('clasificacion'),
            'supervisores':Supervisor.objects.all().order_by('nombre'),
            'clientes':Cliente.objects.all().order_by('nombre'),
            'estatus_list':EstatusScrap.objects.all().order_by('descripcion_status'),
            'tipos_acero':TipoAcero.objects.all().order_by('especificacion'),
            'tipos_laminacion':TipoLaminacion.objects.all().order_by('especificacion')
        })

    # ========================================================
    # CATÁLOGOS
    # ========================================================

    mapping={
        'maquinas':(Maquina,'scrap/maquinas.html','nombre','id_maquina'),
        'operadores':(Operador,'scrap/operadores.html','nombre','id_operador'),
        'turnos':(Turno,'scrap/turnos.html','nombre_turno','id_turno'),
        'defectos':(DefectoScrap,'scrap/scrap_defectos.html','defecto','id_defecto_scrap'),
        'clasificaciones':(ClasificacionScrap,'scrap/clasificaciones.html','clasificacion','id_clasificacion'),
        'supervisores':(Supervisor,'scrap/supervisores.html','nombre','id_supervisor'),
        'clientes':(Cliente,'scrap/clientes_scrap.html','nombre','id_cliente'),
        'tipos_acero':(TipoAcero,'scrap/tipos_acero.html','especificacion','id_tipo_acero'),
        'tipos_laminacion':(TipoLaminacion,'scrap/tipos_laminacion.html','especificacion','id_tipo_laminacion'),
        'estatus':(EstatusScrap,'scrap/estatus.html','descripcion_status','id_estatus_scrap')
    }

    if section in mapping:
        model,template,field,pk_name=mapping[section]
        items=model.objects.all().order_by(field)

        edit_item=None
        if edit_id:
            try:
                edit_item=model.objects.filter(**{pk_name:edit_id}).first()
            except (ValueError,TypeError):
                edit_item=None

        return render(request,template,{
            'items':items,
            'edit_item':edit_item
        })

    return redirect('scrap_section',section='nuevo')


# ============================================================
# CRUD DE CATÁLOGOS
# ============================================================

@login_required
@requiere_gestion_scrap
@require_POST
def scrap_actions(request,section,action_type,item_id=None):
    model_mapping={
        'maquinas':(Maquina,'nombre','id_maquina'),
        'operadores':(Operador,'nombre','id_operador'),
        'defectos':(DefectoScrap,'defecto','id_defecto_scrap'),
        'clasificaciones':(ClasificacionScrap,'clasificacion','id_clasificacion'),
        'supervisores':(Supervisor,'nombre','id_supervisor'),
        'tipos_acero':(TipoAcero,'especificacion','id_tipo_acero'),
        'estatus':(EstatusScrap,'descripcion_status','id_estatus_scrap'),
        'clientes':(Cliente,'nombre','id_cliente'),
        'tipos_laminacion':(TipoLaminacion,'especificacion','id_tipo_laminacion')
    }

    # ========================================================
    # TURNOS
    # ========================================================

    if section=='turnos':
        try:
            if action_type=='crear':
                nombre=(request.POST.get('nombre_turno') or '').strip()
                hora_inicio=request.POST.get('hora_inicio')
                hora_fin=request.POST.get('hora_fin')

                if not nombre or not hora_inicio or not hora_fin:
                    messages.error(request,'Completa todos los campos.')
                    return redirect('scrap_section',section='turnos')

                if Turno.objects.filter(nombre_turno__iexact=nombre).exists():
                    messages.error(request,'Este turno ya existe.')
                    return redirect('scrap_section',section='turnos')

                Turno.objects.create(
                    nombre_turno=nombre,
                    hora_inicio=datetime.strptime(hora_inicio,'%H:%M').time(),
                    hora_fin=datetime.strptime(hora_fin,'%H:%M').time()
                )
                messages.success(request,'Turno guardado con éxito.')

            elif action_type=='editar' and item_id:
                obj=get_object_or_404(Turno,id_turno=item_id)
                nombre=(request.POST.get('nombre_turno') or '').strip()

                if Turno.objects.filter(nombre_turno__iexact=nombre).exclude(id_turno=item_id).exists():
                    messages.error(request,'Ya existe otro turno con ese nombre.')
                    return redirect('scrap_section',section='turnos')

                obj.nombre_turno=nombre
                obj.hora_inicio=datetime.strptime(request.POST.get('hora_inicio'),'%H:%M').time()
                obj.hora_fin=datetime.strptime(request.POST.get('hora_fin'),'%H:%M').time()
                obj.save()

                messages.success(request,'Turno actualizado con éxito.')

            elif action_type=='eliminar' and item_id:
                obj=get_object_or_404(Turno,id_turno=item_id)
                obj.delete()
                messages.success(request,'Turno eliminado correctamente.')

        except ProtectedError:
            messages.error(request,'No se puede eliminar porque este turno está siendo utilizado.')
        except ValueError:
            messages.error(request,'Formato de hora inválido.')
        except Exception as e:
            messages.error(request,f'Error: {e}')

        return redirect('scrap_section',section='turnos')

    # ========================================================
    # DEMÁS CATÁLOGOS
    # ========================================================

    if section not in model_mapping:
        messages.error(request,'Sección no válida.')
        return redirect('scrap')

    model,field_name,pk_name=model_mapping[section]

    try:
        if action_type in ['crear','editar']:
            value=(request.POST.get(field_name) or '').strip()

            if not value:
                messages.error(request,'El campo requerido no puede estar vacío.')
                return redirect('scrap_section',section=section)

            if action_type=='crear':
                if model.objects.filter(**{f'{field_name}__iexact':value}).exists():
                    messages.error(request,'Este registro ya existe en el sistema.')
                else:
                    datos={field_name:value}

                    if section=='maquinas':
                        datos['descripcion']=(request.POST.get('descripcion') or '').strip() or None

                    model.objects.create(**datos)
                    messages.success(request,'Registro creado con éxito.')

            elif action_type=='editar' and item_id:
                obj=get_object_or_404(model,**{pk_name:item_id})

                filtro={f'{field_name}__iexact':value}
                duplicado=model.objects.filter(**filtro).exclude(**{pk_name:item_id}).exists()

                if duplicado:
                    messages.error(request,'Ya existe otro registro con ese mismo nombre.')
                else:
                    setattr(obj,field_name,value)

                    if section=='maquinas':
                        obj.descripcion=(request.POST.get('descripcion') or '').strip() or None

                    obj.save()
                    messages.success(request,'Registro actualizado con éxito.')

        elif action_type=='eliminar' and item_id:
            obj=get_object_or_404(model,**{pk_name:item_id})
            obj.delete()
            messages.success(request,'Registro eliminado correctamente.')

        else:
            messages.error(request,'Acción no válida.')

    except ProtectedError:
        messages.error(request,'No se puede eliminar este registro porque está siendo utilizado.')
    except IntegrityError:
        messages.error(request,'No se pudo realizar la operación porque el registro está relacionado con otros datos.')
    except Exception as e:
        messages.error(request,f'Error: {e}')

    return redirect('scrap_section',section=section)


# ============================================================
# EDITAR REGISTRO DE SCRAP
# ============================================================

@login_required
@requiere_gestion_scrap
@require_POST
def scrap_editar(request,item_id):
    registro=get_object_or_404(Scrap,id=item_id)

    try:
        registro.maquina=get_object_or_404(Maquina,id_maquina=request.POST.get('id_maquina'))
        registro.operador=get_object_or_404(Operador,id_operador=request.POST.get('id_operador'))
        registro.supervisor=get_object_or_404(Supervisor,id_supervisor=request.POST.get('id_supervisor'))
        registro.defecto=get_object_or_404(DefectoScrap,id_defecto_scrap=request.POST.get('id_defecto_scrap'))
        registro.clasificacion=get_object_or_404(ClasificacionScrap,id_clasificacion=request.POST.get('id_clasificacion'))
        registro.cliente=get_object_or_404(Cliente,id_cliente=request.POST.get('id_cliente'))
        registro.estatus=get_object_or_404(EstatusScrap,id_estatus_scrap=request.POST.get('id_estatus_scrap'))
        registro.tipo_acero=get_object_or_404(TipoAcero,id_tipo_acero=request.POST.get('id_tipo_acero'))
        registro.tipo_laminacion=get_object_or_404(TipoLaminacion,id_tipo_laminacion=request.POST.get('id_tipo_laminacion'))

        registro.numero_parte=(request.POST.get('numero_parte') or '').strip()
        registro.lote=(request.POST.get('lote') or '').strip()
        registro.peso=decimal_post(request,'peso')
        registro.cantidad_retrabajado=decimal_post(request,'cantidad_retrabajado')
        registro.cantidad_ng=decimal_post(request,'cantidad_ng')

        hora_manual=(request.POST.get('hora_registro') or '').strip()
        fecha_manual=(request.POST.get('fecha_registro') or '').strip()

        if hora_manual or fecha_manual:
            fecha_final=construir_fecha_registro(
                fecha_manual or None,
                hora_manual or None,
                registro.fecha_registro
            )

            registro.fecha_registro=fecha_final
            hora_turno=timezone.localtime(fecha_final).time().replace(tzinfo=None)
            registro.turno=detectar_turno(hora_turno)

        registro.save()
        messages.success(request,'Registro actualizado correctamente.')

        try:
            scrap_ticket_notification(registro)
        except Exception as e:
            logger.exception('Error enviando alerta de Scrap: %s',e)

    except Exception as e:
        messages.error(request,f'Error al actualizar: {e}')

    return redirect('scrap_section',section='nuevo')


# ============================================================
# ELIMINAR REGISTRO DE SCRAP
# ============================================================

@login_required
@requiere_gestion_scrap
@require_POST
def scrap_eliminar(request,item_id):
    registro=get_object_or_404(Scrap,id=item_id)

    try:
        registro.delete()
        messages.success(request,'Registro eliminado correctamente.')
    except ProtectedError:
        messages.error(request,'No se puede eliminar este registro porque está relacionado con otros datos.')
    except Exception as e:
        messages.error(request,f'Error al eliminar: {e}')

    return redirect('scrap_section',section='nuevo')


# ============================================================
# HISTORIAL POR USUARIO
# ============================================================

@login_required
@requiere_gestion_scrap
def historial_usuario(request,user_id):
    registros=Scrap.objects.filter(
        usuario_registro_id=user_id
    ).select_related(
        'maquina','operador','turno','defecto','cliente',
        'tipo_acero','tipo_laminacion','estatus'
    ).order_by('-fecha_registro')

    return render(request,'scrap/historial.html',{
        'registros':registros
    })


# ============================================================
# OBTENER TURNO MEDIANTE AJAX
# ============================================================

@login_required
@requiere_gestion_scrap
def get_turno(request):
    hora_str=request.GET.get('hora')

    if not hora_str:
        return JsonResponse({'error':'Hora no proporcionada'},status=400)

    try:
        hora_obj=datetime.strptime(hora_str,'%H:%M').time()
        turno=detectar_turno(hora_obj)

        if turno:
            return JsonResponse({
                'id_turno':turno.id_turno,
                'nombre':turno.nombre_turno
            })

        return JsonResponse({
            'id_turno':None,
            'nombre':'Sin turno asignado'
        })

    except Exception as e:
        return JsonResponse({'error':str(e)},status=500)


# ============================================================
# FILTROS DE REPORTES
# ============================================================

def obtener_filtros_scrap(request):
    return {
        'fecha_inicio':request.GET.get('fecha_inicio',''),
        'fecha_fin':request.GET.get('fecha_fin',''),
        'id_maquina':request.GET.get('id_maquina',''),
        'id_operador':request.GET.get('id_operador',''),
        'id_cliente':request.GET.get('id_cliente',''),
        'id_estatus_scrap':request.GET.get('id_estatus_scrap',''),
        'id_defecto_scrap':request.GET.get('id_defecto_scrap',''),
        'id_turno':request.GET.get('id_turno',''),
        'id_supervisor':request.GET.get('id_supervisor',''),
        'id_clasificacion':request.GET.get('id_clasificacion',''),
        'id_tipo_acero':request.GET.get('id_tipo_acero',''),
        'id_tipo_laminacion':request.GET.get('id_tipo_laminacion','')
    }


def aplicar_filtros_scrap(query,filtros):
    if filtros['fecha_inicio']:
        inicio=datetime.strptime(filtros['fecha_inicio'],'%Y-%m-%d')
        inicio=timezone.make_aware(inicio,timezone.get_current_timezone())
        query=query.filter(fecha_registro__gte=inicio)

    if filtros['fecha_fin']:
        fin=datetime.strptime(filtros['fecha_fin'],'%Y-%m-%d').replace(hour=23,minute=59,second=59)
        fin=timezone.make_aware(fin,timezone.get_current_timezone())
        query=query.filter(fecha_registro__lte=fin)

    mapping={
        'id_maquina':'maquina_id',
        'id_operador':'operador_id',
        'id_cliente':'cliente_id',
        'id_estatus_scrap':'estatus_id',
        'id_defecto_scrap':'defecto_id',
        'id_turno':'turno_id',
        'id_supervisor':'supervisor_id',
        'id_clasificacion':'clasificacion_id',
        'id_tipo_acero':'tipo_acero_id',
        'id_tipo_laminacion':'tipo_laminacion_id'
    }

    for filtro,campo in mapping.items():
        if filtros[filtro]:
            query=query.filter(**{campo:filtros[filtro]})

    return query


# ============================================================
# REPORTES
# ============================================================

@login_required
@requiere_gestion_scrap
def scrap_reportes(request):
    filtros=obtener_filtros_scrap(request)

    query=Scrap.objects.select_related(
        'maquina','operador','turno','defecto','clasificacion',
        'supervisor','cliente','tipo_acero','estatus',
        'usuario_registro','tipo_laminacion'
    )

    try:
        query=aplicar_filtros_scrap(query,filtros)
    except (ValueError,TypeError):
        messages.error(request,'Uno de los filtros contiene un valor inválido.')

    registros=query.order_by('-fecha_registro')

    total_peso=sum((r.peso or Decimal('0')) for r in registros)
    total_ng=sum((r.cantidad_ng or Decimal('0')) for r in registros)
    total_retrabajo=sum((r.cantidad_retrabajado or Decimal('0')) for r in registros)

    kpis={
        'total_registros':registros.count(),
        'peso_total':total_peso,
        'total_ng':total_ng,
        'total_retrabajo':total_retrabajo
    }

    return render(request,'scrap/reportes_scrap.html',{
        'filtros':filtros,
        'registros':registros,
        'kpis':kpis,
        'maquinas':Maquina.objects.all().order_by('nombre'),
        'operadores':Operador.objects.all().order_by('nombre'),
        'clientes':Cliente.objects.all().order_by('nombre'),
        'estatus_list':EstatusScrap.objects.all().order_by('descripcion_status'),
        'defectos':DefectoScrap.objects.all().order_by('defecto'),
        'turnos':Turno.objects.all().order_by('nombre_turno'),
        'supervisores':Supervisor.objects.all().order_by('nombre'),
        'clasificaciones':ClasificacionScrap.objects.all().order_by('clasificacion'),
        'tipos_acero':TipoAcero.objects.all().order_by('especificacion'),
        'tipos_laminacion':TipoLaminacion.objects.all().order_by('especificacion')
    })


# ============================================================
# GRÁFICAS PARA PDF
# ============================================================

SCHEMES={
    'green':('#bbf7d0','#16a34a','#14532d'),
    'amber':('#fef9c3','#d97706','#78350f'),
    'red':('#fee2e2','#dc2626','#7f1d1d'),
    'blue':('#dbeafe','#2563eb','#1e3a8a'),
    'purple':('#f3e8ff','#a855f7','#581c87'),
    'teal':('#ccfbf1','#14b8a6','#134e4a'),
    'orange':('#ffedd5','#f97316','#7c2d12'),
    'slate':('#f1f5f9','#64748b','#0f172a'),
    'lime':('#d9f99d','#84cc16','#365314')
}


def _save(fig):
    buf=BytesIO()
    fig.savefig(buf,format='png',bbox_inches='tight',dpi=150,facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf


def bar(data,title,scheme='green',w_mm=120,h_mm=70,unit='kg',n=8):
    data=[(str(label),float(valor)) for label,valor in data if float(valor)>0][:n]

    if not data:
        return None

    labels,values=zip(*data)
    total=sum(values) or 1
    max_v=max(values)
    light,mid,dark=SCHEMES[scheme]

    fig,ax=plt.subplots(
        figsize=(w_mm/25.4,max(h_mm/25.4,len(labels)*.6+1)),
        dpi=150
    )

    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    for i in range(len(labels)):
        ax.axhspan(
            i-.48,i+.48,
            color='#f8fafc' if i%2==0 else 'white',
            zorder=0
        )

    ax.barh(
        range(len(labels)),
        [max_v]*len(labels),
        height=.52,
        color=light,
        alpha=.4,
        zorder=1
    )

    bars=ax.barh(
        range(len(labels)),
        values,
        height=.52,
        color=mid,
        alpha=.88,
        zorder=2
    )

    bars[0].set_facecolor(dark)
    bars[0].set_alpha(1)

    for i,b in enumerate(bars):
        ax.plot(
            [0,0],
            [b.get_y(),b.get_y()+b.get_height()],
            color=dark if i==0 else mid,
            linewidth=2.5,
            solid_capstyle='round',
            zorder=3
        )

    for i,(b,val) in enumerate(zip(bars,values)):
        ax.text(
            b.get_width()+max_v*.015,
            b.get_y()+b.get_height()/2,
            f'{val:,.1f} {unit} ({val/total*100:.0f}%)',
            va='center',
            ha='left',
            fontsize=6,
            color=dark if i==0 else '#374151',
            fontweight='bold' if i==0 else 'normal'
        )

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(
        [f'#{i+1} {label}' for i,label in enumerate(labels)],
        fontsize=6.2,
        color='#0f172a'
    )

    ax.invert_yaxis()
    ax.set_xlim(0,max_v*1.55)
    ax.xaxis.set_visible(False)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_color('#e2e8f0')

    ax.tick_params(axis='y',length=0,pad=3)

    for p in [.25,.5,.75,1]:
        ax.axvline(max_v*p,color='#e2e8f0',lw=.5,zorder=0)

    ax.set_title(
        title,
        fontsize=7.5,
        fontweight='bold',
        color='#0f172a',
        loc='left',
        pad=6
    )

    plt.tight_layout(pad=.5)
    return _save(fig)


def line(data_dia,w_mm=257,h_mm=58):
    if not data_dia:
        return None

    fechas=[d['fecha'] for d in data_dia]
    pesos=[d['peso'] for d in data_dia]
    ngs=[d['ng'] for d in data_dia]
    xs=np.arange(len(fechas))

    fig,ax1=plt.subplots(figsize=(w_mm/25.4,h_mm/25.4),dpi=150)
    fig.patch.set_facecolor('white')
    ax1.set_facecolor('white')
    ax2=ax1.twinx()

    ax1.fill_between(xs,pesos,alpha=.1,color='#d97706')
    ax2.fill_between(xs,ngs,alpha=.07,color='#dc2626')

    l1,=ax1.plot(
        xs,pesos,
        color='#d97706',
        lw=2,
        marker='o',
        ms=3.5,
        markerfacecolor='white',
        markeredgewidth=1.5,
        markeredgecolor='#d97706',
        label='Peso (kg)',
        zorder=4
    )

    l2,=ax2.plot(
        xs,ngs,
        color='#dc2626',
        lw=2,
        marker='s',
        ms=3.5,
        markerfacecolor='white',
        markeredgewidth=1.5,
        markeredgecolor='#dc2626',
        label='Peso NG',
        zorder=4
    )

    ax1.set_xticks(xs)
    ax1.set_xticklabels(
        fechas,
        fontsize=5.8,
        color='#64748b',
        rotation=30 if len(fechas)>10 else 0,
        ha='right'
    )

    ax1.set_ylabel('Peso (kg)',fontsize=6,color='#d97706')
    ax2.set_ylabel('Peso NG',fontsize=6,color='#dc2626')

    ax1.tick_params(axis='y',labelsize=5.5,colors='#94a3b8')
    ax2.tick_params(axis='y',labelsize=5.5,colors='#94a3b8')

    ax1.yaxis.grid(True,color='#e2e8f0',lw=.4,zorder=0)
    ax1.set_axisbelow(True)

    for ax in [ax1,ax2]:
        ax.spines['top'].set_visible(False)

    ax1.spines['right'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax1.spines['left'].set_color('#e2e8f0')
    ax1.spines['bottom'].set_color('#e2e8f0')

    fig.legend(
        [l1,l2],
        ['Peso (kg)','Peso NG'],
        loc='upper right',
        fontsize=6,
        frameon=True,
        fancybox=False,
        edgecolor='#e2e8f0',
        bbox_to_anchor=(.99,.97)
    )

    ax1.set_title(
        'Tendencia diaria',
        fontsize=7.5,
        fontweight='bold',
        color='#0f172a',
        loc='left',
        pad=6
    )

    plt.tight_layout(pad=.5)
    return _save(fig)


def _img(buf,w,h):
    return Image(buf,width=w*mm,height=h*mm) if buf else Spacer(w*mm,h*mm)


def _sec(txt,style):
    return [
        Spacer(1,3*mm),
        Paragraph(txt.upper(),style),
        HRFlowable(
            width='100%',
            thickness=.4,
            color=colors.HexColor('#e2e8f0'),
            spaceAfter=2
        )
    ]


# ============================================================
# PDF
# ============================================================

@login_required
@requiere_gestion_scrap
def scrap_reporte_pdf(request):
    filtros=obtener_filtros_scrap(request)

    query=Scrap.objects.select_related(
        'maquina','operador','turno','defecto','clasificacion',
        'supervisor','cliente','tipo_acero','estatus','tipo_laminacion'
    )

    try:
        query=aplicar_filtros_scrap(query,filtros)
    except (ValueError,TypeError):
        messages.error(request,'Los filtros proporcionados no son válidos.')
        return redirect('scrap_reportes')

    registros=list(query.order_by('fecha_registro'))

    total_peso=sum(float(r.peso or 0) for r in registros)
    total_ng=sum(float(r.cantidad_ng or 0) for r in registros)
    total_ret=sum(float(r.cantidad_retrabajado or 0) for r in registros)
    n_regs=len(registros)

    def agg(kfn,vfn=lambda r:float(r.peso or 0)):
        resultado={}

        for r in registros:
            clave=kfn(r)
            if clave:
                resultado[clave]=resultado.get(clave,0.0)+vfn(r)

        return sorted(
            resultado.items(),
            key=lambda x:x[1],
            reverse=True
        )

    ng=lambda r:float(r.cantidad_ng or 0)

    data_def=agg(lambda r:r.defecto.defecto if r.defecto else None)
    data_maq=agg(lambda r:r.maquina.nombre if r.maquina else None)
    data_op=agg(lambda r:r.operador.nombre if r.operador else None,ng)
    data_est=agg(lambda r:r.estatus.descripcion_status if r.estatus else None,ng)
    data_tur=agg(lambda r:r.turno.nombre_turno if r.turno else None)
    data_cli=agg(lambda r:r.cliente.nombre if r.cliente else None)
    data_sup=agg(lambda r:r.supervisor.nombre if r.supervisor else None)
    data_ace=agg(lambda r:r.tipo_acero.especificacion if r.tipo_acero else None)
    data_lam=agg(lambda r:r.tipo_laminacion.especificacion if r.tipo_laminacion else None)
    data_cla=agg(lambda r:r.clasificacion.clasificacion if r.clasificacion else None)

    dia_map={}

    for r in registros:
        if not r.fecha_registro:
            continue

        fecha_local=timezone.localtime(r.fecha_registro)
        clave=fecha_local.strftime('%Y-%m-%d')
        etiqueta=fecha_local.strftime('%d/%m')

        if clave not in dia_map:
            dia_map[clave]={
                'fecha':etiqueta,
                'peso':0.0,
                'ng':0.0
            }

        dia_map[clave]['peso']=round(
            dia_map[clave]['peso']+float(r.peso or 0),
            2
        )

        dia_map[clave]['ng']+=float(r.cantidad_ng or 0)

    data_dia=[valor for _,valor in sorted(dia_map.items())]

    fecha_gen=timezone.localtime().strftime('%d/%m/%Y %H:%M')

    styles=getSampleStyleSheet()

    s_t=ParagraphStyle(
        'titulo',
        parent=styles['Title'],
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=1,
        leading=22
    )

    s_s=ParagraphStyle(
        'subtitulo',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=5
    )

    s_h=ParagraphStyle(
        'seccion',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#64748b'),
        fontName='Helvetica-Bold',
        spaceAfter=2
    )

    PAGE=landscape(A4)
    M=12*mm
    W=PAGE[0]-2*M
    WM=W/mm

    buf_pdf=BytesIO()

    doc=SimpleDocTemplate(
        buf_pdf,
        pagesize=PAGE,
        leftMargin=M,
        rightMargin=M,
        topMargin=M,
        bottomMargin=13*mm
    )

    story=[
        Paragraph('Reporte de Scrap',s_t),
        Paragraph(f'Generado: {fecha_gen}',s_s),
        HRFlowable(
            width='100%',
            thickness=1.2,
            color=colors.HexColor('#16a34a'),
            spaceAfter=6
        )
    ]

    kd=[
        ['REGISTROS','PESO (kg)','PESO NG','RETRABAJO','PROM / REG'],
        [
            str(n_regs),
            f'{total_peso:,.1f}',
            f'{total_ng:,.1f}',
            f'{total_ret:,.1f}',
            f'{total_peso/n_regs:,.1f}' if n_regs else '—'
        ]
    ]

    kt=Table(kd,colWidths=[WM/5*mm]*5)

    kt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#64748b')),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0),6.5),
        ('ALIGN',(0,0),(-1,0),'CENTER'),
        ('TOPPADDING',(0,0),(-1,0),4),
        ('BOTTOMPADDING',(0,0),(-1,0),4),
        ('FONTNAME',(0,1),(-1,1),'Helvetica-Bold'),
        ('FONTSIZE',(0,1),(-1,1),17),
        ('ALIGN',(0,1),(-1,1),'CENTER'),
        ('TOPPADDING',(0,1),(-1,1),7),
        ('BOTTOMPADDING',(0,1),(-1,1),7),
        ('TEXTCOLOR',(1,1),(1,1),colors.HexColor('#d97706')),
        ('TEXTCOLOR',(2,1),(2,1),colors.HexColor('#dc2626')),
        ('TEXTCOLOR',(3,1),(3,1),colors.HexColor('#2563eb')),
        ('TEXTCOLOR',(4,1),(4,1),colors.HexColor('#64748b')),
        ('BOX',(0,0),(-1,-1),.5,colors.HexColor('#e2e8f0')),
        ('INNERGRID',(0,0),(-1,-1),.3,colors.HexColor('#e2e8f0'))
    ]))

    story.append(kt)

    H_FULL=150

    graficas=[
        ('Tendencia diaria',lambda:line(data_dia,w_mm=WM,h_mm=120)),
        ('Top Defectos',lambda:bar(data_def,'Top Defectos — Peso (kg)','green',WM,H_FULL)),
        ('Top Máquinas',lambda:bar(data_maq,'Top Máquinas — Peso (kg)','amber',WM,H_FULL)),
        ('Top Operadores',lambda:bar(data_op,'Top Operadores — Peso NG','red',WM,H_FULL,'kg')),
        ('NG por Estatus',lambda:bar(data_est,'NG por Estatus','purple',WM,H_FULL,'kg',6)),
        ('Por Turno',lambda:bar(data_tur,'Por Turno','teal',WM,H_FULL,'kg',4)),
        ('Por Cliente',lambda:bar(data_cli,'Por Cliente','blue',WM,H_FULL)),
        ('Por Supervisor',lambda:bar(data_sup,'Por Supervisor','slate',WM,H_FULL)),
        ('Por Tipo de Acero',lambda:bar(data_ace,'Por Tipo de Acero','orange',WM,H_FULL)),
        ('Por Laminación',lambda:bar(data_lam,'Por Laminación','lime',WM,H_FULL,'kg',4)),
        ('Por Clasificación',lambda:bar(data_cla,'Por Clasificación','red',WM,H_FULL,'kg',4))
    ]

    for titulo,generador in graficas:
        buf_chart=generador()

        if buf_chart is None:
            continue

        story.append(PageBreak())
        story.extend(_sec(titulo,s_h))
        story.append(_img(buf_chart,WM,H_FULL))

    def footer(canvas,doc):
        canvas.saveState()

        pw=doc.pagesize[0]

        canvas.setStrokeColor(colors.HexColor('#e2e8f0'))
        canvas.setLineWidth(.4)
        canvas.line(M,11*mm,pw-M,11*mm)

        canvas.setFont('Helvetica',6.5)
        canvas.setFillColor(colors.HexColor('#64748b'))

        canvas.drawString(M,8*mm,'Reporte de Scrap')
        canvas.drawRightString(
            pw-M,
            8*mm,
            f'Pág. {doc.page} · {fecha_gen}'
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer
    )

    buf_pdf.seek(0)

    nombre_archivo=f'reporte_scrap_{timezone.localtime().strftime("%Y%m%d_%H%M")}.pdf'

    response=HttpResponse(
        buf_pdf.getvalue(),
        content_type='application/pdf'
    )

    response['Content-Disposition']=f'attachment; filename="{nombre_archivo}"'

    return response