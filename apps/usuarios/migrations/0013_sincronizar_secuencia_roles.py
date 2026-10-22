from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0012_normalizar_permisos_admin'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "SELECT setval("
                "pg_get_serial_sequence('roles', 'id'), "
                "COALESCE((SELECT MAX(id) FROM roles), 1), true)"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
