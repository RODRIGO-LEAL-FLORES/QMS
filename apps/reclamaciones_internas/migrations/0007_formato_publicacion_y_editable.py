from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reclamaciones_internas', '0006_formato_revision_historial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='formatoreclamacioninterna',
            old_name='fecha_vigencia',
            new_name='fecha_publicacion',
        ),
        migrations.AddField(
            model_name='formatoreclamacioninterna',
            name='archivo_editable',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='reclamaciones_internas/formatos/editables/',
            ),
        ),
    ]
