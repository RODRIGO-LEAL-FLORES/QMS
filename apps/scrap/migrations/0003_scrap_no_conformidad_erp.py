from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('scrap', '0002_alter_scrap_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='scrap',
            name='no_conformidad_erp',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
