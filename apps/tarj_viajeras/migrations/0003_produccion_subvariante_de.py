from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tarj_viajeras', '0002_reasignaciontarjeta'),
    ]

    operations = [
        migrations.AddField(
            model_name='produccion',
            name='subvariante_de',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='subvariantes',
                to='tarj_viajeras.produccion',
            ),
        ),
    ]
