from django.db import migrations


MAQUINAS = [
    (1, 'MINSTER 30', 'prensa'),
    (2, 'PULSAR C', 'producción'),
    (5, 'MINSTER 100 A', 'producción'),
    (7, 'MINSTER 100 B', 'producción'),
    (13, 'P-150 A', 'prensa'),
    (10, 'P-150 B', 'prensa'),
    (11, 'P-150 C', 'prensa'),
    (9, 'P-125 A', 'prensa'),
    (8, 'P-125 B', 'prensa'),
    (14, 'P-200-A', 'prensa'),
    (12, 'P-200-B', 'prensa'),
    (6, 'P-300-A', 'prensa'),
    (4, 'CTL A', 'CTL'),
    (3, 'CTL B', 'CTL'),
    (15, 'CTL C', 'CTL'),
    (16, 'DGCORE A', 'DGCORE'),
    (17, 'DGCORE B', 'DGCORE'),
    (18, 'DGCORE C', 'DGCORE'),
]


def cargar_maquinas(apps, schema_editor):
    Maquina = apps.get_model('liberaciones', 'Maquina')

    for id_maquina, nombre, descripcion in MAQUINAS:
        if not Maquina.objects.filter(id_maquina=id_maquina).exists():
            Maquina.objects.create(
                id_maquina=id_maquina,
                nombre=nombre,
                descripcion=descripcion
            )

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence('maquinas', 'id_maquina'), "
            "COALESCE((SELECT MAX(id_maquina) FROM maquinas), 1), TRUE)"
        )


def revertir_maquinas(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('liberaciones', '0002_alter_liberacion_cliente_and_more'),
    ]

    operations = [
        migrations.RunPython(cargar_maquinas, revertir_maquinas),
    ]
