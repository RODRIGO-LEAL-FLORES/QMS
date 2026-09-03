from datetime import date, timedelta

from .models import EstatusReclamacion


# =========================================================================
# CÁLCULO DE DÍAS HÁBILES
# =========================================================================

def sumar_dias_habiles(fecha_inicio: date, dias_habiles: int) -> date:
    """
    Suma N días hábiles (lunes a viernes) a una fecha.

    No considera días festivos; únicamente excluye sábados y domingos.
    """

    if fecha_inicio is None:
        return None

    fecha = fecha_inicio
    dias_sumados = 0

    while dias_sumados < dias_habiles:
        fecha += timedelta(days=1)

        # weekday():
        # 0 = lunes
        # 1 = martes
        # 2 = miércoles
        # 3 = jueves
        # 4 = viernes
        # 5 = sábado
        # 6 = domingo
        if fecha.weekday() < 5:
            dias_sumados += 1

    return fecha


# =========================================================================
# DEFINICIÓN DEL PIPELINE
# =========================================================================
#
# Cada etapa contiene:
#
#   orden:
#       Posición dentro del pipeline.
#
#   nombre:
#       Nombre del estatus que debe existir en EstatusReclamacion.
#
#   campo_fecha:
#       Campo de Reclamacion que indica que la etapa fue completada.
#
#   calcular_limite:
#       Función utilizada para calcular la fecha límite de la etapa.
#
# IMPORTANTE:
# El estatus NO se selecciona manualmente.
# Se determina automáticamente dependiendo de qué fechas están capturadas.
#
# =========================================================================

ETAPAS = [
    {
        "orden": 1,
        "nombre": "Confirmación",
        "campo_fecha": "fecha_confirmacion",
        "calcular_limite": lambda reporte: reporte + timedelta(days=1),
    },
    {
        "orden": 2,
        "nombre": "Contención (D0-D3)",
        "campo_fecha": "fecha_contencion",
        "calcular_limite": lambda reporte: sumar_dias_habiles(
            reporte,
            2
        ),
    },
    {
        "orden": 3,
        "nombre": "CR y AC (D4-D7)",
        "campo_fecha": "fecha_CR_AC",
        "calcular_limite": lambda reporte: sumar_dias_habiles(
            reporte,
            10
        ),
    },
    {
        "orden": 4,
        "nombre": "Cierre (D8)",
        "campo_fecha": "fecha_cierre",
        "calcular_limite": lambda reporte: sumar_dias_habiles(
            reporte,
            20
        ),
    },
    {
        "orden": 5,
        "nombre": "Cerrado",
        "campo_fecha": None,
        "calcular_limite": lambda reporte: None,
    },
]


# =========================================================================
# CÁLCULO DEL ESTATUS ACTUAL
# =========================================================================

def calcular_orden_actual(reclamacion) -> int:
    """
    Determina en qué etapa se encuentra actualmente una reclamación.

    Recorre las etapas en orden y devuelve la primera cuya fecha todavía
    no ha sido capturada.

    Ejemplo:

        fecha_confirmacion = capturada
        fecha_contencion = capturada
        fecha_CR_AC = None

    Resultado:

        orden = 3
        estatus = "CR y AC (D4-D7)"

    Si todas las fechas fueron capturadas, la reclamación pasa a "Cerrado".
    """

    for etapa in ETAPAS:

        campo = etapa["campo_fecha"]

        # "Cerrado" no tiene campo de fecha propio
        if campo is None:
            continue

        if getattr(reclamacion, campo, None) is None:
            return etapa["orden"]

    # Todas las etapas fueron completadas
    return ETAPAS[-1]["orden"]


# =========================================================================
# OBTENER ESTATUS DESDE LA BASE DE DATOS
# =========================================================================

def obtener_estatus_por_orden(orden: int):
    """
    Busca el EstatusReclamacion correspondiente al número de orden.

    Django ORM reemplaza:

        EstatusReclamacion.query.filter_by(...)

    que utilizabas anteriormente con SQLAlchemy.
    """

    return EstatusReclamacion.objects.filter(
        orden=orden
    ).first()


# =========================================================================
# ACTUALIZAR ESTATUS AUTOMÁTICAMENTE
# =========================================================================

def actualizar_estatus_automatico(reclamacion):
    """
    Calcula automáticamente el estatus actual de una reclamación.

    Debe ejecutarse antes de guardar cuando cambien las fechas del pipeline.

    Ejemplo:

        reclamacion.fecha_contencion = date.today()

        actualizar_estatus_automatico(reclamacion)

        reclamacion.save()
    """

    orden_actual = calcular_orden_actual(reclamacion)

    estatus = obtener_estatus_por_orden(
        orden_actual
    )

    if estatus:
        reclamacion.estatus = estatus

    return reclamacion


# =========================================================================
# CHECKLIST / TIMELINE DE LA RECLAMACIÓN
# =========================================================================

def calcular_checklist(reclamacion):
    """
    Genera la información necesaria para mostrar el pipeline de una
    reclamación en la interfaz.

    Cada elemento contiene:

        {
            "orden": 2,
            "nombre": "Contención (D0-D3)",
            "completado": True,
            "es_actual": False,
            "fecha_limite": date,
            "fecha_real": date,
            "estado_tiempo": "en_tiempo"
        }

    Posibles valores de estado_tiempo:

        en_tiempo
            La etapa ya fue completada dentro del límite.

        completado_tarde
            La etapa fue completada después del límite.

        atrasado
            La etapa todavía NO fue completada y ya venció.

        pendiente
            Es la etapa actual y todavía está dentro del tiempo permitido.

        sin_iniciar
            Es una etapa futura.
    """

    hoy = date.today()

    fecha_reporte = reclamacion.fecha_reporte

    orden_actual = calcular_orden_actual(
        reclamacion
    )

    checklist = []

    for etapa in ETAPAS:

        campo = etapa["campo_fecha"]

        # ---------------------------------------------------------
        # Fecha real
        # ---------------------------------------------------------

        fecha_real = (
            getattr(reclamacion, campo, None)
            if campo
            else None
        )

        # ---------------------------------------------------------
        # Fecha límite
        # ---------------------------------------------------------

        fecha_limite = (
            etapa["calcular_limite"](fecha_reporte)
            if fecha_reporte
            else None
        )

        # ---------------------------------------------------------
        # ¿La etapa ya fue completada?
        # ---------------------------------------------------------

        if campo is None:
            completado = (
                orden_actual == etapa["orden"]
            )
        else:
            completado = fecha_real is not None

        # ---------------------------------------------------------
        # ¿Es la etapa actual?
        # ---------------------------------------------------------

        es_actual = (
            etapa["orden"] == orden_actual
        )

        # ---------------------------------------------------------
        # Estado de tiempo
        # ---------------------------------------------------------

        if campo is None:

            # Etapa final "Cerrado"
            if orden_actual == etapa["orden"]:
                estado_tiempo = "en_tiempo"
            else:
                estado_tiempo = "sin_iniciar"

        elif fecha_real is not None:

            # La etapa ya fue realizada
            if (
                fecha_limite is None
                or fecha_real <= fecha_limite
            ):
                estado_tiempo = "en_tiempo"

            else:
                estado_tiempo = "completado_tarde"

        elif (
            fecha_limite is not None
            and hoy > fecha_limite
        ):

            # La etapa sigue pendiente y ya venció
            estado_tiempo = "atrasado"

        elif es_actual:

            # Etapa actual todavía dentro del tiempo
            estado_tiempo = "pendiente"

        else:

            # Etapa futura
            estado_tiempo = "sin_iniciar"

        checklist.append(
            {
                "orden": etapa["orden"],
                "nombre": etapa["nombre"],
                "completado": completado,
                "es_actual": es_actual,
                "fecha_limite": fecha_limite,
                "fecha_real": fecha_real,
                "estado_tiempo": estado_tiempo,
            }
        )

    return checklist


# =========================================================================
# DÍAS DE RETRASO AL CIERRE
# =========================================================================

def calcular_dias_retraso_cierre(
    fecha_reporte: date,
    fecha_cierre: date
) -> int:
    """
    Calcula cuántos días se tardó una reclamación después de la fecha
    límite de cierre.

    El cierre tiene un límite de 20 días hábiles desde fecha_reporte.

    Devuelve 0 cuando:

        - No existe fecha_reporte.
        - La reclamación todavía no tiene fecha_cierre.
        - Se cerró dentro del tiempo permitido.

    Una vez cerrada la reclamación, este valor queda congelado.
    """

    if not fecha_reporte or not fecha_cierre:
        return 0

    limite_cierre = sumar_dias_habiles(
        fecha_reporte,
        20
    )

    if not limite_cierre:
        return 0

    diferencia = (
        fecha_cierre - limite_cierre
    ).days

    return diferencia if diferencia > 0 else 0


# =========================================================================
# DÍAS DE RETRASO ACTUALES
# =========================================================================

def calcular_dias_retraso_actual(reclamacion) -> int:
    """
    Calcula el retraso actual de una reclamación.

    Si la reclamación ya está cerrada:

        utiliza fecha_cierre y el valor queda congelado.

    Si continúa abierta:

        compara la fecha actual contra el límite de 20 días hábiles.

    Esto permite que el retraso aumente automáticamente con el paso
    del tiempo sin necesidad de modificar la reclamación.
    """

    if not reclamacion.fecha_reporte:
        return 0

    # ---------------------------------------------------------
    # Reclamación cerrada
    # ---------------------------------------------------------

    if reclamacion.fecha_cierre:

        return calcular_dias_retraso_cierre(
            reclamacion.fecha_reporte,
            reclamacion.fecha_cierre
        )

    # ---------------------------------------------------------
    # Reclamación todavía abierta
    # ---------------------------------------------------------

    limite_cierre = sumar_dias_habiles(
        reclamacion.fecha_reporte,
        20
    )

    if not limite_cierre:
        return 0

    diferencia = (
        date.today() - limite_cierre
    ).days

    return diferencia if diferencia > 0 else 0


# =========================================================================
# SINCRONIZAR RETRASO EN BASE DE DATOS
# =========================================================================

def actualizar_dias_retraso(reclamacion):
    """
    Actualiza el campo:

        dias_retrazo_al_reclamo

    con el valor calculado actualmente.

    IMPORTANTE:

    Este campo sirve principalmente para ordenar y filtrar registros
    desde la base de datos.

    Para mostrar el retraso actual en pantalla se recomienda utilizar:

        calcular_dias_retraso_actual(reclamacion)

    porque ese cálculo cambia diariamente aunque nadie edite el registro.
    """

    reclamacion.dias_retrazo_al_reclamo = (
        calcular_dias_retraso_actual(
            reclamacion
        )
    )

    return reclamacion


# =========================================================================
# PREPARAR RECLAMACIÓN ANTES DE GUARDAR
# =========================================================================

def preparar_reclamacion_para_guardar(reclamacion):
    """
    Ejecuta las operaciones automáticas necesarias antes de guardar una
    reclamación.

    Actualmente:

        1. Actualiza el estatus según las fechas.
        2. Actualiza los días de retraso.

    Uso:

        reclamacion.fecha_contencion = date.today()

        preparar_reclamacion_para_guardar(reclamacion)

        reclamacion.save()
    """

    actualizar_estatus_automatico(
        reclamacion
    )

    actualizar_dias_retraso(
        reclamacion
    )

    return reclamacion