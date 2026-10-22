from django.db import migrations


PERMISOS = (
    ('reclamaciones', 'view_reportes'),
    ('reclamaciones_internas', 'view_reportes'),
    ('reclamaciones_internas', 'delete_formatoreclamacioninterna'),
    ('scrap', 'export_scrap'),
    ('scrap', 'view_produccion_scrap'),
    ('scrap', 'change_produccion_scrap'),
    ('tarj_viajeras', 'print_tarjetaviajera'),
    ('tarj_viajeras', 'update_status_tarjetaviajera'),
    ('tarj_viajeras', 'update_measurements_tarjetaviajera'),
)


def asignar_permisos(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Usuario = apps.get_model('usuarios', 'Usuario')
    Permission = apps.get_model('auth', 'Permission')

    def permiso(app_label, codename):
        return Permission.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
        ).first()

    for rol in Rol.objects.all():
        usuarios = Usuario.objects.filter(rol_id=rol.pk)

        if usuarios.filter(puede_gestionar_reportes=True).exists():
            for app_label in ('reclamaciones', 'reclamaciones_internas'):
                p = permiso(app_label, 'view_reportes')
                if p:
                    rol.permissions.add(p)

        if rol.pk == 1:
            p = permiso('reclamaciones_internas', 'delete_formatoreclamacioninterna')
            if p:
                rol.permissions.add(p)

        if rol.pk in (1, 2):
            p = permiso('scrap', 'export_scrap')
            if p:
                rol.permissions.add(p)

        if usuarios.filter(area__nombre__iexact='producción').exists() or usuarios.filter(area__nombre__iexact='produccion').exists():
            for codename in ('view_produccion_scrap', 'change_produccion_scrap'):
                p = permiso('scrap', codename)
                if p:
                    rol.permissions.add(p)

        if rol.pk in (1, 2, 3):
            p = permiso('tarj_viajeras', 'print_tarjetaviajera')
            if p:
                rol.permissions.add(p)

        if rol.pk == 4:
            p = permiso('tarj_viajeras', 'update_status_tarjetaviajera')
            if p:
                rol.permissions.add(p)

        if rol.pk == 3:
            p = permiso('tarj_viajeras', 'update_measurements_tarjetaviajera')
            if p:
                rol.permissions.add(p)


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0010_permisos_especiales_de_roles'),
    ]

    operations = [
        migrations.RunPython(asignar_permisos, migrations.RunPython.noop),
    ]
