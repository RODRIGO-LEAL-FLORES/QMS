from django.db import migrations


def asignar(apps, rol, permission_model, app_label, codename):
    Permission = apps.get_model('auth', 'Permission')
    permission = Permission.objects.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).first()
    if permission:
        rol.permissions.add(permission)


def migrar_permisos_especiales(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Usuario = apps.get_model('usuarios', 'Usuario')

    for rol in Rol.objects.all():
        usuarios = Usuario.objects.filter(rol_id=rol.pk)

        if usuarios.filter(puede_gestionar_reportes=True).exists():
            asignar(apps, rol, 'Reclamacion', 'reclamaciones', 'view_reportes')
            asignar(apps, rol, 'ReclamacionInterna', 'reclamaciones_internas', 'view_reportes')

        if rol.pk == 1:
            asignar(apps, rol, 'FormatoReclamacionInterna', 'reclamaciones_internas', 'delete_formatoreclamacioninterna')

        if rol.pk in (1, 2):
            asignar(apps, rol, 'Scrap', 'scrap', 'export_scrap')

        if usuarios.filter(area__nombre__iexact='producción').exists() or usuarios.filter(area__nombre__iexact='produccion').exists():
            asignar(apps, rol, 'Scrap', 'scrap', 'view_produccion_scrap')
            asignar(apps, rol, 'Scrap', 'scrap', 'change_produccion_scrap')

        if rol.pk in (1, 2, 3):
            asignar(apps, rol, 'TarjetaViajera', 'tarj_viajeras', 'print_tarjetaviajera')

        if rol.pk == 4:
            asignar(apps, rol, 'TarjetaViajera', 'tarj_viajeras', 'update_status_tarjetaviajera')

        if rol.pk == 3:
            asignar(apps, rol, 'TarjetaViajera', 'tarj_viajeras', 'update_measurements_tarjetaviajera')


class Migration(migrations.Migration):
    dependencies = [
        ('reclamaciones', '0002_alter_reclamacion_options'),
        ('reclamaciones_internas', '0009_alter_reclamacioninterna_options'),
        ('scrap', '0002_alter_scrap_options'),
        ('tarj_viajeras', '0005_alter_tarjetaviajera_options'),
        ('usuarios', '0009_migrar_permisos_de_roles'),
    ]

    operations = [
        migrations.RunPython(migrar_permisos_especiales, migrations.RunPython.noop),
    ]
