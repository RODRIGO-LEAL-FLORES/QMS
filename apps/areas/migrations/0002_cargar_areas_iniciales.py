from django.db import migrations


def crear_areas(apps, schema_editor):
    Area = apps.get_model('areas', 'Area')

    areas = [
        (1, 'Calidad'),
        (2, 'Produccion'),
        (3, 'Ingenieria'),
        (5, 'SH'),
        (7, 'Planeacion'),
        (8, 'Horno'),
        (9, 'Nuevos desarrollos'),
        (10, 'Mantenimiento'),
        (11, 'Estampado'),
        (12, "CTL's"),
        (13, 'Cadena de suministro'),
        (14, 'Ventas'),
        (15, 'Alta direccion'),
        (16, 'Tecnologias de la informacion'),
        (17, 'Recursos Humanos'),
        (18, 'Dev'),
        (19, 'Taller de troqueles'),
        (20, 'Compras indirectas'),
    ]

    for area_id, nombre in areas:
        Area.objects.update_or_create(
            id_area=area_id,
            defaults={'nombre': nombre}
        )


def eliminar_areas(apps, schema_editor):
    Area = apps.get_model('areas', 'Area')

    Area.objects.filter(
        id_area__in=[
            1, 2, 3, 5, 7, 8, 9, 10,
            11, 12, 13, 14, 15, 16,
            17, 18, 19, 20
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('areas', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            crear_areas,
            eliminar_areas
        ),
    ]