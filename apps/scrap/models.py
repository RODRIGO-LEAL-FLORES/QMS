from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.liberaciones import models as liberaciones_models 





class Operador(models.Model):
    id_operador = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=60, unique=True)

    class Meta:
        db_table = 'operadores'

    def __str__(self):
        return self.nombre


class Turno(models.Model):
    id_turno = models.AutoField(primary_key=True)
    nombre_turno = models.CharField(max_length=25, unique=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        db_table = 'turnos'

    def __str__(self):
        return self.nombre_turno


class DefectoScrap(models.Model):
    id_defecto_scrap = models.AutoField(primary_key=True)
    defecto = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'defectos_scrap'

    def __str__(self):
        return self.defecto


class ClasificacionScrap(models.Model):
    id_clasificacion = models.AutoField(primary_key=True)
    clasificacion = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'clasificaciones_scrap'

    def __str__(self):
        return self.clasificacion


class Supervisor(models.Model):
    id_supervisor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=60, unique=True)

    class Meta:
        db_table = 'supervisores'

    def __str__(self):
        return self.nombre


class TipoAcero(models.Model):
    id_tipo_acero = models.AutoField(primary_key=True)
    especificacion = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'tipos_acero'

    def __str__(self):
        return self.especificacion




class EstatusScrap(models.Model):
    id_estatus_scrap = models.AutoField(primary_key=True)
    descripcion_status = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'estatus_scrap'

    def __str__(self):
        return self.descripcion_status


class Scrap(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_registro = models.DateTimeField(default=timezone.now)

    maquina = models.ForeignKey(
        'maquinas.Maquina',
        on_delete=models.PROTECT,
        db_column='id_maquina',
        related_name='registros_scrap'
    )

    operador = models.ForeignKey(
        Operador,
        on_delete=models.PROTECT,
        db_column='id_operador',
        related_name='registros_scrap'
    )

    turno = models.ForeignKey(
        Turno,
        on_delete=models.PROTECT,
        db_column='id_turno',
        related_name='registros_scrap'
    )

    defecto = models.ForeignKey(
        DefectoScrap,
        on_delete=models.PROTECT,
        db_column='id_defecto_scrap',
        related_name='registros_scrap'
    )

    clasificacion = models.ForeignKey(
        ClasificacionScrap,
        on_delete=models.PROTECT,
        db_column='id_clasificacion',
        related_name='registros_scrap'
    )

    supervisor = models.ForeignKey(
        Supervisor,
        on_delete=models.PROTECT,
        db_column='id_supervisor',
        related_name='registros_scrap'
    )

    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        db_column='id_cliente',
        related_name='registros_scrap'
    )

    tipo_acero = models.ForeignKey(
        TipoAcero,
        on_delete=models.PROTECT,
        db_column='id_tipo_acero',
        related_name='registros_scrap'
    )

    estatus = models.ForeignKey(
        EstatusScrap,
        on_delete=models.PROTECT,
        db_column='id_estatus_scrap',
        related_name='registros_scrap'
    )

    usuario_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='usuario_registro_id',
        related_name='registros_scrap'
    )

 
    tipo_laminacion = models.ForeignKey(
        'laminacion.TipoLaminacion',
        on_delete=models.PROTECT,
        db_column='id_tipo_laminacion',
        related_name='registros_scrap'
    )

    numero_parte = models.CharField(max_length=50)
    lote = models.CharField(max_length=50)
    peso = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_retrabajado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cantidad_ng = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'scrap'

    def __str__(self):
        return f'Scrap #{self.id} - Lote {self.lote}'