"""Normalización y validación de datos recibidos por formularios."""

from ..models import NumeroParteCliente, PROCESOS_PRODUCCION
from apps.clientes.models import Cliente
from apps.liberaciones.models import TipoLaminacion


# =========================================================
# TARJETAS: NORMALIZACIÓN DE FORMULARIO
# =========================================================

def datos_tarjeta(post_data):
    return {
        'numero_tarjeta': post_data.get('numero_tarjeta', '').strip(),
        'sufijo': post_data.get('sufijo', '').strip().upper(),
        'status_id': post_data.get('id_status'),
        'proceso_tarjeta_id': post_data.get('proceso_tarjeta'),
        'numero_alambres': post_data.get('numero_alambres'),
        'piezas_por_alambre': post_data.get('piezas_por_alambre'),
        'peso_kg': post_data.get('peso_kg'),
        'peso_lbs': post_data.get('peso_lbs'),
        'tara': post_data.get('tara', '').strip(),
    }


# =========================================================
# CONFIGURACIÓN DE PIEZAS: NORMALIZACIÓN Y VALIDACIÓN
# =========================================================

def datos_configuracion_piezas(post_data):
    return {
        'cliente_id': post_data.get('cliente'),
        'numero_parte_id': post_data.get('numero_parte_cliente'),
        'laminacion_id': post_data.get('laminacion'),
        'proceso': post_data.get('proceso', '').strip(),
        'piezas_por_alambre': post_data.get('piezas_por_alambre', '').strip(),
    }


def validar_datos_configuracion_piezas(datos):
    if not all((
        datos['cliente_id'],
        datos['numero_parte_id'],
        datos['laminacion_id'],
        datos['proceso'],
        datos['piezas_por_alambre'],
    )):
        return None

    ids_relaciones = (
        datos['cliente_id'],
        datos['numero_parte_id'],
        datos['laminacion_id'],
    )
    if (
        datos['proceso'] not in dict(PROCESOS_PRODUCCION)
        or not all(str(valor).isdigit() for valor in ids_relaciones)
        or not Cliente.objects.filter(pk=datos['cliente_id']).exists()
        or not NumeroParteCliente.objects.filter(
            pk=datos['numero_parte_id']
        ).exists()
        or not TipoLaminacion.objects.filter(
            pk=datos['laminacion_id']
        ).exists()
    ):
        return None

    try:
        piezas = int(datos['piezas_por_alambre'])
    except (TypeError, ValueError):
        return None

    return piezas if piezas >= 0 else None
