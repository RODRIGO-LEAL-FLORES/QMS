from django.db import models

from apps.clientes.models import Cliente
from apps.scrap.models import TipoAcero
from apps.liberaciones.models import (
    TipoLaminacion,
    Maquina
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


class Produccion(models.Model):
    id_produccion = models.AutoField(primary_key=True)

    numero_orden_trabajo = models.CharField(
        max_length=20
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