from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reclamaciones_internas', '0003_formatoreclamacioninterna'),
    ]

    operations = [
        migrations.AddField(
            model_name='reclamacioninterna',
            name='codigo_documento',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='reclamacioninterna',
            name='fecha_alta',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reclamacioninterna',
            name='id_documento',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='reclamacioninterna',
            name='solicitante',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]