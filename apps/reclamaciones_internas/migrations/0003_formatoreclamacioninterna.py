import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reclamaciones_internas', '0002_cargar_estatus_iniciales'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FormatoReclamacionInterna',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150)),
                ('codigo', models.CharField(max_length=50, unique=True)),
                ('version', models.CharField(max_length=20)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('archivo', models.FileField(upload_to='reclamaciones_internas/formatos/')),
                ('fecha_vigencia', models.DateField()),
                ('actualizado_at', models.DateTimeField(auto_now=True)),
                ('actualizado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='formatos_reclamaciones_internas_actualizados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'formatos_reclamaciones_internas',
                'ordering': ['-fecha_vigencia', '-actualizado_at'],
            },
        ),
    ]