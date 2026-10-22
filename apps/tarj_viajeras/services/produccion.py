"""Normalización y validaciones de datos de producción."""

from ..models import ConfiguracionPiezasAlambre, PROCESOS_PRODUCCION


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
