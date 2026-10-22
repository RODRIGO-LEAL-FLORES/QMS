from django.db import migrations


def completar_acceso_tarjetas(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Permission = apps.get_model('auth', 'Permission')

    permiso_ver = Permission.objects.filter(
        content_type__app_label='tarj_viajeras',
        codename='view_tarjetaviajera',
    ).first()

    if not permiso_ver:
        return

    permisos_tarjetas = Permission.objects.filter(
        content_type__app_label='tarj_viajeras',
        codename__in=(
            'change_tarjetaviajera',
            'print_tarjetaviajera',
            'update_status_tarjetaviajera',
            'update_measurements_tarjetaviajera',
        ),
    )

    for rol in Rol.objects.filter(permissions__in=permisos_tarjetas).distinct():
        rol.permissions.add(permiso_ver)


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0013_sincronizar_secuencia_roles'),
    ]

    operations = [
        migrations.RunPython(completar_acceso_tarjetas, migrations.RunPython.noop),
    ]
