from django.db import models

from apps.clientes.models import Cliente
from apps.scrap.models import TipoAcero
from apps.liberaciones.models import (
    TipoLaminacion,
    Maquina
)

PROCESOS_PRODUCCION = (
    ('R', 'Rotor'),
    ('E', 'Estator'),
    ('EI', 'EI'),
    ('DG', 'Dg core'),
    ('CTL', 'CTLS'),
)


class Espesor(models.Model):
    id_espesor = models.AutoField(primary_key=True)

    espesor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        unique=True
    )

    class Meta:
        db_table = 'espesores'

    def __str__(self):
        return str(self.espesor)


class NumeroParteCliente(models.Model):
    id_num_pcli = models.AutoField(primary_key=True)

    descripcion = models.CharField(
        max_length=150
    )

    class Meta:
        db_table = 'numero_parte_cliente'

    def __str__(self):
        return self.descripcion


class StatusTar(models.Model):
    id_status = models.AutoField(primary_key=True)

    descripcion = models.CharField(
        max_length=150
    )

    class Meta:
        db_table = 'status_tar'

    def __str__(self):
        return self.descripcion


class ProcesoTarjeta(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'procesos_tarjeta'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def permite_estatus(self, status_id):
        return self.estatus_proceso.filter(status_id=status_id).exists()


class ProcesoTarjetaEstatus(models.Model):
    proceso = models.ForeignKey(
        ProcesoTarjeta,
        on_delete=models.CASCADE,
        related_name='estatus_proceso',
    )
    status = models.ForeignKey(
        StatusTar,
        on_delete=models.PROTECT,
        related_name='procesos_tarjeta',
    )
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'procesos_tarjeta_estatus'
        ordering = ['orden', 'status__descripcion']
        constraints = [
            models.UniqueConstraint(
                fields=['proceso', 'status'],
                name='uq_proceso_tarjeta_estatus',
            ),
            models.UniqueConstraint(
                fields=['proceso', 'orden'],
                name='uq_proceso_tarjeta_orden',
            ),
        ]

    def __str__(self):
        return f'{self.proceso} · {self.status}'


class Produccion(models.Model):
    id_produccion = models.AutoField(primary_key=True)

    subvariante_de = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subvariantes'
    )

    numero_orden_trabajo = models.CharField(
        max_length=20
    )

    proceso = models.CharField(
        max_length=3,
        choices=PROCESOS_PRODUCCION,
        blank=True,
        default=''
    )

    piezas_por_alambre = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    lote = models.CharField(
        max_length=100
    )

    numero_orden_compra = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        db_column='id_cliente',
        related_name='producciones'
    )

    material = models.ForeignKey(
        TipoAcero,
        on_delete=models.PROTECT,
        db_column='id_material',
        related_name='producciones'
    )

    espesor = models.ForeignKey(
        Espesor,
        on_delete=models.PROTECT,
        db_column='id_espesor',
        related_name='producciones'
    )



    laminacion = models.ForeignKey(
        TipoLaminacion,
        on_delete=models.PROTECT,
        db_column='id_laminacion',
        related_name='producciones'
    )

    numero_parte_cliente = models.ForeignKey(
        NumeroParteCliente,
        on_delete=models.PROTECT,
        db_column='id_num_pcli',
        related_name='producciones'
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'produccion'

    def __str__(self):
        return f'{self.numero_orden_trabajo} - {self.lote}'


class ConfiguracionPiezasAlambre(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    numero_parte_cliente = models.ForeignKey(
        NumeroParteCliente,
        on_delete=models.PROTECT
    )
    laminacion = models.ForeignKey(
        TipoLaminacion,
        on_delete=models.PROTECT
    )
    proceso = models.CharField(
        max_length=3,
        choices=PROCESOS_PRODUCCION
    )
    piezas_por_alambre = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cliente',
                    'numero_parte_cliente',
                    'laminacion',
                    'proceso',
                ],
                name='uq_config_piezas_cliente_parte_laminacion_proceso',
            )
        ]

    def __str__(self):
        return (
            f'{self.cliente} / {self.numero_parte_cliente} / '
            f'{self.laminacion} / {self.proceso}'
        )


class TarjetaViajera(models.Model):
    id_tarjeta = models.AutoField(
        primary_key=True
    )

    produccion = models.ForeignKey(
        Produccion,
        on_delete=models.PROTECT,
        db_column='id_produccion',
        related_name='tarjetas_viajeras'
    )

    numero_tarjeta = models.IntegerField()

    sufijo = models.CharField(
        max_length=1,
        null=True,
        blank=True
    )

    status = models.ForeignKey(
        StatusTar,
        on_delete=models.PROTECT,
        db_column='id_status',
        related_name='tarjetas_viajeras'
    )

    proceso_tarjeta = models.ForeignKey(
        ProcesoTarjeta,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column='id_proceso_tarjeta',
        related_name='tarjetas_viajeras',
    )

    numero_alambres = models.IntegerField(
        null=True,
        blank=True
    )

    piezas_por_alambre = models.IntegerField(
        null=True,
        blank=True
    )

    peso_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    peso_lbs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    tara = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'tarjetas_viajeras'
        permissions = [
            ('print_tarjetaviajera', 'Puede imprimir tarjetas viajeras'),
            ('update_status_tarjetaviajera', 'Puede actualizar el estatus de tarjetas'),
            ('update_measurements_tarjetaviajera', 'Puede actualizar medidas de tarjetas'),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'numero_tarjeta',
                    'sufijo'
                ],
                name='uq_numero_tarjeta_sufijo'
            )
        ]

    @property
    def folio_completo(self):
        if self.sufijo:
            return f'{self.numero_tarjeta}-{self.sufijo}'
        return str(self.numero_tarjeta)

    def __str__(self):
        return self.folio_completo


class ReasignacionTarjeta(models.Model):
    tarjeta = models.ForeignKey(
        TarjetaViajera,
        on_delete=models.CASCADE,
        related_name='reasignaciones'
    )

    produccion_origen = models.ForeignKey(
        Produccion,
        on_delete=models.PROTECT,
        related_name='+'
    )

    produccion_destino = models.ForeignKey(
        Produccion,
        on_delete=models.PROTECT,
        related_name='+'
    )

    motivo = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)
