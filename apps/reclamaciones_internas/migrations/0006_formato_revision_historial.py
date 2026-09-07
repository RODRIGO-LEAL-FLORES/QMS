from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reclamaciones_internas', '0005_remove_reclamacion_document_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='formatoreclamacioninterna',
            old_name='version',
            new_name='revision',
        ),
        migrations.AlterField(
            model_name='formatoreclamacioninterna',
            name='codigo',
            field=models.CharField(max_length=50),
        ),
    ]