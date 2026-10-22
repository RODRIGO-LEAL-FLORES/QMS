"""Reglas reutilizables del catálogo y captura de estatus de tarjetas."""

import re
import unicodedata

from ..models import StatusTar


# =========================================================
# ESTATUS: NORMALIZACIÓN Y VALIDACIÓN DEL CATÁLOGO
# =========================================================

def normalizar_descripcion_estatus(descripcion):
    return (descripcion or '').strip()


def descripcion_estatus_duplicada(descripcion, excluir_id=None):
    estatus = StatusTar.objects.filter(descripcion__iexact=descripcion)
    if excluir_id is not None:
        estatus = estatus.exclude(id_status=excluir_id)
    return estatus.exists()


def codigo_barras_estatus(id_status):
    return f'9{id_status:05d}'


# =========================================================
# ESTATUS: INTERPRETACIÓN DE CÓDIGOS DEL ESCÁNER
# =========================================================

def separar_codigo_tarjeta(codigo):
    codigo = unicodedata.normalize('NFKC', codigo or '')
    codigo = ''.join(
        caracter for caracter in codigo
        if caracter.isprintable() and caracter != '\ufffd'
    )
    codigo = codigo.strip().replace('Ã‘', ':').replace('Ã±', ':')
    codigo = codigo.replace('Ñ', ':').replace('ñ', ':')
    codigo = codigo.replace('Ç', ':').replace('ç', ':')
    codigo = codigo.replace('\ufffd', ':')
    if codigo.startswith(']C1'):
        codigo = codigo[3:]

    codigo_partido = re.fullmatch(r'(.*?)(\d+)(?:-([A-Za-z]))?', codigo)
    if not codigo_partido:
        return None

    orden = re.sub(r'[^A-Za-z0-9]+$', '', codigo_partido.group(1)) or None
    sufijo = codigo_partido.group(3)
    return (
        orden,
        int(codigo_partido.group(2)),
        sufijo.upper() if sufijo else None,
    )


def id_estatus_desde_codigo(codigo):
    codigo = (codigo or '').strip()
    if len(codigo) != 6 or not codigo.isdigit() or not codigo.startswith('9'):
        return None
    return int(codigo[1:])
