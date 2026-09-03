from django.db import models


# ============================================================
# CATEGORÍA
# ============================================================

class Categoria(models.Model):
    id_categorias = models.AutoField(primary_key=True)

    categoria = models.CharField(
        max_length=100,
        unique=True
    )

    class Meta:
        db_table = 'categorias'

    def __str__(self):
        return self.categoria


# ============================================================
# DEFECTO
# ============================================================

class Defecto(models.Model):
    id_defecto = models.AutoField(primary_key=True)

    descripcion = models.CharField(
        max_length=100
    )

    class Meta:
        db_table = 'defectos'

    def __str__(self):
        return self.descripcion


# ============================================================
# OCURRENCIA
# ============================================================

class Ocurrencia(models.Model):
    id_ocurrencia = models.AutoField(primary_key=True)

    ocurrencia = models.CharField(
        max_length=100,
        unique=True
    )

    class Meta:
        db_table = 'ocurrencias'

    def __str__(self):
        return self.ocurrencia


# ============================================================
# ESTATUS DE RECLAMACIÓN
# ============================================================

class EstatusReclamacion(models.Model):
    id_estatus = models.AutoField(primary_key=True)

    descripcion_status = models.CharField(
        max_length=100,
        unique=True
    )

    orden = models.IntegerField(
        unique=True,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'estatus_reclamaciones'

    def __str__(self):
        return self.descripcion_status


# ============================================================
# RECLAMACIÓN
# ============================================================

class Reclamacion(models.Model):

    id = models.AutoField(primary_key=True)

    # --------------------------------------------------------
    # Información principal
    # --------------------------------------------------------

    id_reporte_cliente = models.CharField(
        max_length=50,
        unique=True
    )

    issue = models.CharField(
        max_length=500
    )

    # --------------------------------------------------------
    # Relaciones
    # --------------------------------------------------------

    defecto = models.ForeignKey(
        Defecto,
        on_delete=models.PROTECT,
        db_column='id_defecto',
        related_name='reclamaciones'
    )

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        db_column='id_categoria',
        related_name='reclamaciones'
    )

    ocurrencia = models.ForeignKey(
        Ocurrencia,
        on_delete=models.PROTECT,
        db_column='id_ocurrencia',
        related_name='reclamaciones'
    )

    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_cliente',
        related_name='reclamaciones'
    )

    estatus = models.ForeignKey(
        EstatusReclamacion,
        on_delete=models.PROTECT,
        db_column='id_estatus',
        related_name='reclamaciones'
    )

    # Una reclamación puede involucrar una o varias áreas
    areas_involucradas = models.ManyToManyField(
        'areas.Area',
        related_name='reclamaciones',
        blank=True
    )

    # --------------------------------------------------------
    # Información del material
    # --------------------------------------------------------

    numero_parte = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    lote = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    numero_contenedor = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    cantidad_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # --------------------------------------------------------
    # Evidencia del defecto
    # --------------------------------------------------------

    imagen_defecto = models.ImageField(
        upload_to='reclamaciones/defectos/',
        null=True,
        blank=True
    )

    # --------------------------------------------------------
    # Análisis
    # --------------------------------------------------------

    causa_raiz = models.TextField(
        null=True,
        blank=True
    )

    # --------------------------------------------------------
    # Fechas
    # --------------------------------------------------------

    fecha_reporte = models.DateField()

    fecha_confirmacion = models.DateField(
        null=True,
        blank=True
    )

    fecha_contencion = models.DateField(
        null=True,
        blank=True
    )

    fecha_CR_AC = models.DateField(
        null=True,
        blank=True
    )

    fecha_cierre = models.DateField(
        null=True,
        blank=True
    )

    # --------------------------------------------------------
    # Seguimiento
    # --------------------------------------------------------

    dias_retrazo_al_reclamo = models.IntegerField(
        default=0
    )

    periodo = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # --------------------------------------------------------
    # Archivo de cierre
    # --------------------------------------------------------

    archivo_cierre_pdf = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'reclamaciones'

    def __str__(self):
        return self.id_reporte_cliente