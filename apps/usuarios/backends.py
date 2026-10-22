class RolPermissionsBackend:
    """Expone en user.has_perm() los permisos asignados al Rol."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        return None

    def _role_permissions(self, user_obj):
        """Devuelve los permisos del rol en el formato usado por Django."""
        if not user_obj.is_active or user_obj.is_superuser or not user_obj.rol_id:
            return set()

        return {
            f'{permission.content_type.app_label}.{permission.codename}'
            for permission in user_obj.rol.permissions.select_related('content_type')
        }

    def get_user_permissions(self, user_obj, obj=None):
        return self._role_permissions(user_obj)

    def get_group_permissions(self, user_obj, obj=None):
        return set()

    def get_all_permissions(self, user_obj, obj=None):
        if user_obj.is_superuser:
            from django.contrib.auth.models import Permission

            return {
                f'{permission.content_type.app_label}.{permission.codename}'
                for permission in Permission.objects.select_related('content_type')
            }

        return self._role_permissions(user_obj)

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False

        if user_obj.is_superuser:
            return True

        return perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        if not user_obj.is_active:
            return False

        if user_obj.is_superuser:
            return True

        if not user_obj.rol_id:
            return False

        return user_obj.rol.permissions.filter(
            content_type__app_label=app_label,
        ).exists()
