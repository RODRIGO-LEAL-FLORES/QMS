from django.conf import settings
from django.db import models


class EstatusLiberacion(models.Model):
    id_estatus = models.AutoField(primary_key=True)
    descripcion_status = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'estatus_liberaciones'

    def __str__(self):
        return self.descripcion_status


class TipoLaminacion(models.Model):
    id_tipo_laminacion = models.AutoField(primary_key=True)
    especificacion = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'tipos_laminacion'

    def __str__(self):
        return self.especificacion


class Maquina(models.Model):
    id_maquina = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'maquinas'

    def __str__(self):
        return self.nombre


class Liberacion(models.Model):
    id = models.AutoField(primary_key=True)
    motivo = models.CharField(max_length=300)
    fecha_liberacion = models.DateField()
    hora_liberacion = models.TimeField()
    numero_orden = models.CharField(max_length=50, null=True, blank=True)

    estatus = models.ForeignKey(
        EstatusLiberacion,
        on_delete=models.PROTECT,
        db_column='id_status',
        related_name='liberaciones'
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_usuario',
        related_name='liberaciones'
    )

    cliente=models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        db_column='id_cliente',
        related_name='liberaciones',
        null=True,
        blank=True
    )

    tipo_laminacion=models.ForeignKey(
        TipoLaminacion,
        on_delete=models.PROTECT,
        db_column='id_tipo_laminacion',
        related_name='liberaciones',
        null=True,
        blank=True
)

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.PROTECT,
        db_column='id_maquina',
        related_name='liberaciones'
    )

    class Meta:
        db_table = 'liberaciones'

    def __str__(self):
        return f'Liberación #{self.id}'