from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_usuario_puede_imprimir_targetas_viajeras'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usuario',
            name='puede_imprimir_targetas_viajeras',
        ),
    ]
