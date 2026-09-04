from django.db import migrations, models


def limpiar_numeros_legacy(apps, schema_editor):
    Liberacion = apps.get_model('liberaciones', 'Liberacion')
    Liberacion.objects.filter(numero_orden__startswith='LEGACY-').update(
        numero_orden=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ('liberaciones', '0005_quitar_unicidad_numero_orden'),
    ]

    operations = [
        migrations.AlterField(
            model_name='liberacion',
            name='numero_orden',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.RunPython(limpiar_numeros_legacy, migrations.RunPython.noop),
    ]