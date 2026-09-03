from datetime import date

from django.conf import settings
from django.db import models


# ============================================================
# PRIORIDAD
# ============================================================

class Prioridad(models.Model):
    id_prioridad = models.AutoField(primary_key=True)
    # Conservamos los mismos datos que antes tenía Color_Ticket
    Prioridad = models.CharField(max_length=20,unique=True)
    descripcion = models.CharField(max_length=1000,null=True,blank=True)
    dias_resolucion = models.IntegerField(default=0)
    
    class Meta:db_table = 'prioridades'
    def __str__(self):
        return self.color


# ============================================================
# ESTATUS DE RECLAMACIÓN INTERNA
# ============================================================

class EstatusReclamacionInterna(models.Model):
    id_estatus = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100,unique=True)
    class Meta:db_table = 'estatus_reclamaciones_internas'
    def __str__(self):return self.descripcion


# ============================================================
# RECLAMACIÓN INTERNA
# ============================================================

class ReclamacionInterna(models.Model):

    id_folio = models.AutoField(primary_key=True)

    # --------------------------------------------------------
    # Prioridad
    # --------------------------------------------------------

    prioridad = models.ForeignKey(
        Prioridad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_prioridad',
        related_name='reclamaciones_internas'
    )

    # --------------------------------------------------------
    # Usuario creador
    # --------------------------------------------------------

    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_usuario_creador',
        related_name='reclamaciones_internas_creadas'
    )

    # --------------------------------------------------------
    # Emisor
    # --------------------------------------------------------

    emisor = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    # --------------------------------------------------------
    # Área responsable
    # --------------------------------------------------------

    area_responsable = models.ForeignKey(
        'areas.Area',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_area_responsable',
        related_name='reclamaciones_internas'
    )

    # --------------------------------------------------------
    # Fechas
    # --------------------------------------------------------

    fecha_emision = models.DateField()

    fecha_compromiso = models.DateField(
        null=True,
        blank=True
    )

    fecha_cierre = models.DateField(
        null=True,
        blank=True
    )

    # --------------------------------------------------------
    # Estatus
    # --------------------------------------------------------

    estatus = models.ForeignKey(
        EstatusReclamacionInterna,
        on_delete=models.PROTECT,
        db_column='id_estatus',
        related_name='reclamaciones_internas'
    )

    # --------------------------------------------------------
    # Seguimiento
    # --------------------------------------------------------

    dias_retraso = models.IntegerField(
        default=0
    )

    evidencia_resolucion = models.TextField(
        null=True,
        blank=True
    )

    problematica = models.TextField(
        null=True,
        blank=True
    )

    accion_correctiva = models.TextField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'reclamaciones_internas'

    # --------------------------------------------------------
    # Retraso calculado en vivo
    # --------------------------------------------------------

    @property
    def dias_retraso_calculado(self):

        if not self.fecha_compromiso:
            return 0

        # Si ya cerró, congelamos el cálculo con fecha_cierre
        fecha_referencia = self.fecha_cierre or date.today()

        retraso = (
            fecha_referencia - self.fecha_compromiso
        ).days

        return retraso if retraso > 0 else 0

    def __str__(self):
        return f'Reclamación interna #{self.id_folio}'


# ============================================================
# EVIDENCIAS
# ============================================================

class EvidenciaReclamacionInterna(models.Model):

    id = models.AutoField(primary_key=True)

    reclamacion = models.ForeignKey(
        ReclamacionInterna,
        on_delete=models.CASCADE,
        db_column='id_reclamacion_interna',
        related_name='evidencias'
    )

    archivo = models.FileField(
        upload_to='reclamaciones_internas/evidencias/'
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'reclamaciones_internas_evidencias'

    def __str__(self):
        return self.archivo.name