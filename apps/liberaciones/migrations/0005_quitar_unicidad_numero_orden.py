from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('liberaciones', '0004_liberacion_numero_orden'),
    ]

    operations = [
        migrations.AlterField(
            model_name='liberacion',
            name='numero_orden',
            field=models.CharField(max_length=50),
        ),
    ]