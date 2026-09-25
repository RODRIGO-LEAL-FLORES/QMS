from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class Operador(models.Model):
    id_operador=models.AutoField(primary_key=True)
    numero_operador=models.CharField(max_length=10,null=True,blank=True)
    nombre=models.CharField(max_length=60,unique=True)

    class Meta:
        db_table='operadores'

    def __str__(self):
        return f'{self.numero_operador or "S/N"} - {self.nombre}'
    


class Turno(models.Model):
    id_turno=models.AutoField(primary_key=True)
    nombre_turno=models.CharField(max_length=25,unique=True)
    hora_inicio=models.TimeField()
    hora_fin=models.TimeField()

    class Meta:
        db_table='turnos'

    def __str__(self):
        return self.nombre_turno


class DefectoScrap(models.Model):
    id_defecto_scrap=models.AutoField(primary_key=True)
    defecto=models.CharField(max_length=100,unique=True)

    class Meta:
        db_table='defectos_scrap'

    def __str__(self):
        return self.defecto


class ClasificacionScrap(models.Model):
    id_clasificacion=models.AutoField(primary_key=True)
    clasificacion=models.CharField(max_length=50,unique=True)

    class Meta:
        db_table='clasificaciones_scrap'

    def __str__(self):
        return self.clasificacion


class Supervisor(models.Model):
    id_supervisor=models.AutoField(primary_key=True)
    nombre=models.CharField(max_length=60,unique=True)

    class Meta:
        db_table='supervisores'

    def __str__(self):
        return self.nombre


class TipoAcero(models.Model):
    id_tipo_acero=models.AutoField(primary_key=True)
    especificacion=models.CharField(max_length=50,unique=True)

    class Meta:
        db_table='tipos_acero'

    def __str__(self):
        return self.especificacion


class TipoPieza(models.Model):
    id_tipo_pieza=models.AutoField(primary_key=True)
    tipo_pieza=models.CharField(max_length=50,unique=True)
    costo_unitario=models.DecimalField(max_digits=10,decimal_places=2,default=0)

    class Meta:
        db_table='tipos_pieza'

    def __str__(self):
        return self.tipo_pieza


class Scrap(models.Model):
    id=models.AutoField(primary_key=True)
    fecha_registro=models.DateTimeField(default=timezone.now)
    maquina=models.ForeignKey(
        'liberaciones.Maquina',
        on_delete=models.PROTECT,
        db_column='id_maquina',
        related_name='registros_scrap'
    )
    operador=models.ForeignKey(
        Operador,
        on_delete=models.PROTECT,
        db_column='id_operador',
        related_name='registros_scrap'
    )
    turno=models.ForeignKey(
        Turno,
        on_delete=models.PROTECT,
        db_column='id_turno',
        related_name='registros_scrap'
    )
    defecto=models.ForeignKey(
        DefectoScrap,
        on_delete=models.PROTECT,
        db_column='id_defecto_scrap',
        related_name='registros_scrap'
    )
    clasificacion=models.ForeignKey(
        ClasificacionScrap,
        on_delete=models.PROTECT,
        db_column='id_clasificacion',
        related_name='registros_scrap'
    )
    supervisor=models.ForeignKey(
        Supervisor,
        on_delete=models.PROTECT,
        db_column='id_supervisor',
        related_name='registros_scrap'
    )
    cliente=models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        db_column='id_cliente',
        related_name='registros_scrap'
    )
    tipo_acero=models.ForeignKey(
        TipoAcero,
        on_delete=models.PROTECT,
        db_column='id_tipo_acero',
        related_name='registros_scrap'
    )
    usuario_registro=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='usuario_registro_id',
        related_name='registros_scrap'
    )
    tipo_laminacion=models.ForeignKey(
        'liberaciones.TipoLaminacion',
        on_delete=models.PROTECT,
        db_column='id_tipo_laminacion',
        related_name='registros_scrap'
    )
    tipo_pieza=models.ForeignKey(
        TipoPieza,
        on_delete=models.PROTECT,
        db_column='id_tipo_pieza',
        related_name='registros_scrap'
    )

    numero_de_orden=models.CharField(max_length=50)
    lote=models.CharField(max_length=50)
    contenedor=models.CharField(max_length=50,null=True,blank=True)
    numero_de_control=models.CharField(max_length=50,null=True,blank=True)
    

    control_salida_pnc_kg=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    pnc_agranel_kg=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    pnc_kg=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    kg_producidos=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    class Meta:
        db_table='scrap'

    def clean(self):
        control=self.control_salida_pnc_kg or Decimal('0')
        agranel=self.pnc_agranel_kg or Decimal('0')
        producidos=self.kg_producidos or Decimal('0')

        if control<0 or agranel<0 or producidos<0:
            raise ValidationError('Los valores en KG no pueden ser negativos.')

        clasificacion=(
            self.clasificacion.clasificacion.strip().lower()
            if self.clasificacion_id
            else ''
        )

        if clasificacion=='targeta roja':
            if agranel>0:
                raise ValidationError({
                    'pnc_agranel_kg':'Para Targeta roja no debe capturarse PNC a granel.'
                })

        elif clasificacion in ['bin amarillo','bin rojo']:
            if control>0:
                raise ValidationError({
                    'control_salida_pnc_kg':'Para Bin amarillo o Bin rojo no debe capturarse Control de salida PNC.'
                })

    def save(self,*args,**kwargs):
        self.control_salida_pnc_kg=self.control_salida_pnc_kg or Decimal('0')
        self.pnc_agranel_kg=self.pnc_agranel_kg or Decimal('0')
        self.kg_producidos=self.kg_producidos or Decimal('0')

        clasificacion=(
            self.clasificacion.clasificacion.strip().lower()
            if self.clasificacion_id
            else ''
        )

        if clasificacion=='targeta roja':
            self.pnc_agranel_kg=Decimal('0')

        elif clasificacion in ['bin amarillo','bin rojo']:
            self.control_salida_pnc_kg=Decimal('0')

        self.pnc_kg=(
            self.control_salida_pnc_kg+
            self.pnc_agranel_kg
        )

        self.full_clean()
        super().save(*args,**kwargs)

    def __str__(self):
        return f'Scrap #{self.id} - Lote {self.lote}'