from django.db import migrations, models


def asignar_numeros_orden(apps, schema_editor):
    Liberacion = apps.get_model('liberaciones', 'Liberacion')

    for liberacion in Liberacion.objects.order_by('id'):
        liberacion.numero_orden = f'LEGACY-{liberacion.id}'
        liberacion.save(update_fields=['numero_orden'])


class Migration(migrations.Migration):

    dependencies = [
        ('liberaciones', '0003_cargar_maquinas'),
    ]

    operations = [
        migrations.AddField(
            model_name='liberacion',
            name='numero_orden',
            field=models.CharField(max_length=50, null=True, unique=True),
        ),
        migrations.RunPython(asignar_numeros_orden, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='liberacion',
            name='numero_orden',
            field=models.CharField(max_length=50, unique=True),
        ),
    ]