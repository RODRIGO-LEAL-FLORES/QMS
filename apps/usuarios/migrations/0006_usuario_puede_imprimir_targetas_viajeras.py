from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0005_usuario_puede_gestionar_targetas_viajeras'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='puede_imprimir_targetas_viajeras',
            field=models.BooleanField(default=False),
        ),
    ]
