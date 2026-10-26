"""Reglas de negocio para procesos y estatus de Tarjetas Viajeras."""

from django.db import transaction

from ..models import ProcesoTarjeta, ProcesoTarjetaEstatus


def estatus_permitido(proceso, status_id):
    """Indica si un estatus está configurado dentro del proceso."""
    return bool(proceso and status_id and proceso.permite_estatus(status_id))


def estatus_ids_del_formulario(post_data):
    """Obtiene IDs válidos, únicos y en el orden recibido por el formulario."""
    return list(dict.fromkeys(
        int(value)
        for value in post_data.getlist('estatus_ids')
        if value.isdigit()
    ))


@transaction.atomic
def crear_proceso(nombre, descripcion, status_ids):
    proceso = ProcesoTarjeta.objects.create(
        nombre=nombre,
        descripcion=descripcion,
    )
    ProcesoTarjetaEstatus.objects.bulk_create([
        ProcesoTarjetaEstatus(
            proceso=proceso,
            status_id=status_id,
            orden=orden,
        )
        for orden, status_id in enumerate(status_ids, start=1)
    ])
    return proceso


@transaction.atomic
def actualizar_proceso(proceso, nombre, descripcion, activo, status_ids):
    proceso.nombre = nombre
    proceso.descripcion = descripcion
    proceso.activo = activo
    proceso.save(update_fields=['nombre', 'descripcion', 'activo'])

    ProcesoTarjetaEstatus.objects.filter(proceso=proceso).delete()
    ProcesoTarjetaEstatus.objects.bulk_create([
        ProcesoTarjetaEstatus(
            proceso=proceso,
            status_id=status_id,
            orden=orden,
        )
        for orden, status_id in enumerate(status_ids, start=1)
    ])
    return proceso
