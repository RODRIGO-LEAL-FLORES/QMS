from django.db.models import Q


def tiene_permiso(user, permiso):
    """Comprueba exclusivamente permisos estándar asignados al rol."""
    if not getattr(user, 'is_authenticated', True):
        return False

    has_perm = getattr(user, 'has_perm', None)
    if callable(has_perm):
        return has_perm(permiso)

    return False


def usuarios_con_permiso(queryset, permiso):
    """Filtra usuarios activos por permiso estándar del rol (o superusuario)."""
    app_label, codename = permiso.split('.', 1)
    return queryset.filter(
        Q(is_superuser=True)
        | Q(
            rol__permissions__content_type__app_label=app_label,
            rol__permissions__codename=codename,
        )
    ).distinct()
