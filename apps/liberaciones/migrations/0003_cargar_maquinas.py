from django.db import migrations


MAQUINAS = [
    ('M-30', 'producción'),
    ('Pulsar C', 'producción'),
    ('100-A', 'producción'),
    ('100-B', 'producción'),
    ('150-A', 'producción'),
    ('150-B', 'producción'),
    ('150-C', 'producción'),
    ('125-A', 'producción'),
    ('125-B', 'producción'),
    ('200-A', 'producción'),
    ('200-B', 'producción'),
    ('300-A', 'producción'),
    ('CTL-A', 'producción'),
    ('CTL-B', 'producción'),
    ('CTL-C', 'producción'),
    ('DGCORE A', 'producción'),
    ('DGCORE B', 'producción'),
    ('DGCORE C', 'producción'),
    ('DGCORE D', 'producción'),
    ('SCRAP', None),
]


def cargar_maquinas(apps, schema_editor):
    Maquina = apps.get_model('liberaciones', 'Maquina')

    for nombre, descripcion in MAQUINAS:
        if not Maquina.objects.filter(nombre=nombre).exists():
            Maquina.objects.create(nombre=nombre, descripcion=descripcion)


def revertir_maquinas(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('liberaciones', '0002_alter_liberacion_cliente_and_more'),
    ]

    operations = [
        migrations.RunPython(cargar_maquinas, revertir_maquinas),
    ]
