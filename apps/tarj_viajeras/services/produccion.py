"""Normalización y validaciones de datos de producción."""

from django.db import models, transaction

from ..models import (
    ConfiguracionPiezasAlambre,
    Espesor,
    NumeroParteCliente,
    Produccion,
    PROCESOS_PRODUCCION,
)
from apps.clientes.models import Cliente
from apps.liberaciones.models import TipoLaminacion
from apps.scrap.models import TipoAcero


# =========================================================
# PRODUCCIÓN: NORMALIZACIÓN Y VALIDACIÓN
# =========================================================

def numero_orden_sin_prefijo(numero_orden, proceso):
    prefijo = f'{proceso}:'
    if proceso and numero_orden.startswith(prefijo):
        return numero_orden[len(prefijo):]
    for codigo, _ in PROCESOS_PRODUCCION:
        prefijo_existente = f'{codigo}:'
        if numero_orden.startswith(prefijo_existente):
            return numero_orden[len(prefijo_existente):]
    return numero_orden


def datos_produccion(post_data):
    # Acepta Request en llamadas heredadas y POST en las vistas actuales.
    post_data = getattr(post_data, 'POST', post_data)
    proceso = post_data.get('proceso', '').strip()
    numero_orden = post_data.get('numero_orden_trabajo', '').strip()
    if proceso in dict(PROCESOS_PRODUCCION):
        numero_orden = numero_orden_sin_prefijo(numero_orden, proceso)

    return {
        'numero_orden': f'{proceso}:{numero_orden}' if numero_orden else '',
        'numero_orden_base': numero_orden,
        'proceso': proceso,
        'lote': post_data.get('lote', '').strip(),
        'numero_orden_compra': post_data.get('numero_orden_compra', '').strip(),
        'cliente_id': post_data.get('id_cliente'),
        'material_id': post_data.get('id_material'),
        'espesor_id': post_data.get('id_espesor'),
        'laminacion_id': post_data.get('id_laminacion'),
        'numero_parte_id': post_data.get('id_num_pcli'),
    }


def produccion_completa(datos):
    return all([
        datos['numero_orden_base'].isdigit(),
        len(datos['numero_orden']) <= 20,
        datos['proceso'] in dict(PROCESOS_PRODUCCION),
        datos['lote'],
        datos['cliente_id'], datos['material_id'],
        datos['espesor_id'], datos['laminacion_id'], datos['numero_parte_id']
    ])


def configuracion_de_produccion(datos):
    ids_relaciones = (
        datos['cliente_id'],
        datos['numero_parte_id'],
        datos['laminacion_id'],
    )
    if (
        datos['proceso'] not in dict(PROCESOS_PRODUCCION)
        or not all(str(valor).isdigit() for valor in ids_relaciones)
    ):
        return None
    return ConfiguracionPiezasAlambre.objects.filter(
        cliente_id=datos['cliente_id'],
        numero_parte_cliente_id=datos['numero_parte_id'],
        laminacion_id=datos['laminacion_id'],
        proceso=datos['proceso'],
    ).first()


class ProduccionInvalida(Exception):
    """Error de negocio con mensaje seguro para mostrar al usuario."""


def _validar_datos_produccion(datos, item_id=None):
    if not datos['numero_orden_base'].isdigit() or len(datos['numero_orden']) > 20:
        raise ProduccionInvalida(
            'El número de OT debe contener solo números y no exceder el tamaño permitido para el prefijo del proceso.'
        )
    if not produccion_completa(datos):
        raise ProduccionInvalida('Completa todos los campos obligatorios.')
    configuracion = configuracion_de_produccion(datos)
    if configuracion is None:
        raise ProduccionInvalida(
            'No existe una configuración de piezas por alambre para el cliente, número de parte, laminación y proceso seleccionados.'
        )
    existentes = Produccion.objects.filter(
        numero_orden_trabajo=datos['numero_orden'],
        lote=datos['lote'],
    )
    if item_id is not None:
        existentes = existentes.exclude(id_produccion=item_id)
    if existentes.exists():
        raise ProduccionInvalida('Ya existe otra producción con esa orden de trabajo y lote.')
    return configuracion


def _relaciones_produccion(datos):
    return {
        'cliente': Cliente.objects.get(id_cliente=datos['cliente_id']),
        'material': TipoAcero.objects.get(id_tipo_acero=datos['material_id']),
        'espesor': Espesor.objects.get(id_espesor=datos['espesor_id']),
        'laminacion': TipoLaminacion.objects.get(id_tipo_laminacion=datos['laminacion_id']),
        'numero_parte_cliente': NumeroParteCliente.objects.get(id_num_pcli=datos['numero_parte_id']),
    }


@transaction.atomic
def crear_produccion(datos):
    configuracion = _validar_datos_produccion(datos)
    return Produccion.objects.create(
        numero_orden_trabajo=datos['numero_orden'],
        proceso=datos['proceso'],
        piezas_por_alambre=configuracion.piezas_por_alambre,
        lote=datos['lote'],
        numero_orden_compra=datos['numero_orden_compra'] or None,
        **_relaciones_produccion(datos),
    )


@transaction.atomic
def actualizar_produccion(item, datos):
    configuracion = _validar_datos_produccion(datos, item.id_produccion)
    for campo, valor in _relaciones_produccion(datos).items():
        setattr(item, campo, valor)
    item.numero_orden_trabajo = datos['numero_orden']
    item.proceso = datos['proceso']
    item.piezas_por_alambre = configuracion.piezas_por_alambre
    item.lote = datos['lote']
    item.numero_orden_compra = datos['numero_orden_compra'] or None
    item.save()
    return item


@transaction.atomic
def crear_subvariante(base, cliente_id, parte_id, laminacion_id):
    configuracion = ConfiguracionPiezasAlambre.objects.filter(
        cliente_id=cliente_id,
        numero_parte_cliente_id=parte_id,
        laminacion_id=laminacion_id,
        proceso=base.proceso,
    ).first()
    if not configuracion:
        raise ProduccionInvalida('No existe configuración de PXA para esta combinación.')
    if Produccion.objects.filter(
        (models.Q(pk=base.pk) | models.Q(subvariante_de=base)),
        cliente_id=cliente_id,
        numero_parte_cliente_id=parte_id,
        laminacion_id=laminacion_id,
    ).exists():
        raise ProduccionInvalida('Esta variante ya existe para la producción.')
    return Produccion.objects.create(
        subvariante_de=base,
        numero_orden_trabajo=base.numero_orden_trabajo,
        lote=base.lote,
        proceso=base.proceso,
        numero_orden_compra=base.numero_orden_compra,
        material=base.material,
        espesor=base.espesor,
        cliente_id=cliente_id,
        numero_parte_cliente_id=parte_id,
        laminacion_id=laminacion_id,
        piezas_por_alambre=configuracion.piezas_por_alambre,
    )
