from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reclamaciones_internas', '0004_reclamacioninterna_document_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reclamacioninterna',
            name='codigo_documento',
        ),
        migrations.RemoveField(
            model_name='reclamacioninterna',
            name='fecha_alta',
        ),
        migrations.RemoveField(
            model_name='reclamacioninterna',
            name='id_documento',
        ),
        migrations.RemoveField(
            model_name='reclamacioninterna',
            name='solicitante',
        ),
    ]