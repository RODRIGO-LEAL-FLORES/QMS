from django.db import migrations


PERMISOS_POR_CAMPO = {
    'puede_gestionar_reclamaciones': (
        ('reclamaciones', 'reclamacion', ('view', 'change')),
    ),
    'puede_gestionar_reclamaciones_internas': (
        ('reclamaciones_internas', 'reclamacioninterna', ('view', 'change')),
    ),
    'puede_gestionar_scrap': (
        ('scrap', 'scrap', ('view', 'change')),
    ),
    'puede_gestionar_liberaciones': (
        ('liberaciones', 'liberacion', ('view', 'change')),
    ),
    'puede_gestionar_targetas_viajeras': (
        ('tarj_viajeras', 'tarjetaviajera', ('view', 'change')),
    ),
    'puede_gestionar_usuarios': (
        ('usuarios', 'usuario', ('view', 'change')),
    ),
}


def migrar_permisos(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Usuario = apps.get_model('usuarios', 'Usuario')
    Permission = apps.get_model('auth', 'Permission')

    for rol in Rol.objects.all():
        usuarios = Usuario.objects.filter(rol_id=rol.pk)

        for campo, definiciones in PERMISOS_POR_CAMPO.items():
            if not usuarios.filter(**{campo: True}).exists():
                continue

            for app_label, model, acciones in definiciones:
                permisos = Permission.objects.filter(
                    content_type__app_label=app_label,
                    content_type__model=model,
                    codename__in=[f'{accion}_{model}' for accion in acciones],
                )
                rol.permissions.add(*permisos)


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('usuarios', '0008_rol_permissions'),
    ]

    operations = [
        migrations.RunPython(migrar_permisos, migrations.RunPython.noop),
    ]
