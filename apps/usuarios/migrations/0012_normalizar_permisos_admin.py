from django.db import migrations


PERMISOS_ADMIN = (
    ('liberaciones', 'view_liberacion'),
    ('liberaciones', 'change_liberacion'),
    ('reclamaciones', 'view_reclamacion'),
    ('reclamaciones', 'change_reclamacion'),
    ('reclamaciones', 'view_reportes'),
    ('reclamaciones_internas', 'view_reclamacioninterna'),
    ('reclamaciones_internas', 'change_reclamacioninterna'),
    ('reclamaciones_internas', 'view_reportes'),
    ('reclamaciones_internas', 'delete_formatoreclamacioninterna'),
    ('scrap', 'view_scrap'),
    ('scrap', 'change_scrap'),
    ('scrap', 'export_scrap'),
    ('tarj_viajeras', 'view_tarjetaviajera'),
    ('tarj_viajeras', 'change_tarjetaviajera'),
    ('tarj_viajeras', 'print_tarjetaviajera'),
    ('usuarios', 'view_usuario'),
    ('usuarios', 'change_usuario'),
)


def normalizar_admin(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Permission = apps.get_model('auth', 'Permission')

    admin_role = Rol.objects.filter(pk=1).first()
    if not admin_role:
        return

    admin_role.permissions.clear()

    for app_label, codename in PERMISOS_ADMIN:
        permission = Permission.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
        ).first()
        if permission:
            admin_role.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0011_asignar_permisos_personalizados'),
    ]

    operations = [
        migrations.RunPython(normalizar_admin, migrations.RunPython.noop),
    ]
