from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django import forms
from django.contrib.auth.models import Permission

from .models import Rol, Usuario


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    class form(forms.ModelForm):
        permissions = forms.ModelMultipleChoiceField(
            queryset=Permission.objects.select_related('content_type').filter(
                content_type__app_label__in={
                    'areas',
                    'clientes',
                    'reclamaciones',
                    'reclamaciones_internas',
                    'scrap',
                    'tarj_viajeras',
                    'liberaciones',
                    'usuarios',
                }
            ).order_by('content_type__app_label', 'content_type__model', 'codename'),
            widget=forms.CheckboxSelectMultiple,
            required=False,
            label='Permisos del rol',
            help_text=(
                'Selecciona las acciones que este rol podrá realizar. '
                'Consultar permite entrar al módulo; las demás acciones son independientes.'
            ),
        )

        class Meta:
            model = Rol
            fields = ('nombre', 'permissions')

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            groups = {}
            for permission in self.fields['permissions'].queryset:
                module = permission.content_type.app_label.replace('_', ' ').title()
                groups.setdefault(module, []).append(
                    (permission.pk, self._permission_label(permission))
                )

            self.fields['permissions'].choices = list(groups.items())

        @staticmethod
        def _permission_label(permission):
            app = permission.content_type.app_label
            model = permission.content_type.model
            action = permission.codename

            modules = {
                'reclamaciones': 'Reclamaciones',
                'reclamaciones_internas': 'Reclamaciones internas',
                'tarj_viajeras': 'Tarjetas viajeras',
                'liberaciones': 'Liberaciones',
                'scrap': 'Scrap',
                'usuarios': 'Usuarios',
                'areas': 'Áreas',
            }
            submodules = {
                'area': 'Area',
                'categoria': 'Categoria',
                'defecto': 'Defecto',
                'estatusreclamacion': 'Estatus',
                'ocurrencia': 'Ocurrencia',
                'reclamacion': 'Reclamacion',
                'estatusreclamacioninterna': 'Estatus',
                'evidenciareclamacioninterna': 'Evidencias',
                'formatoreclamacioninterna': 'Formato oficial',
                'prioridad': 'Prioridad',
                'clasificacionscrap': 'Clasificaciones',
                'defectoscrap': 'Defectos',
                'operador': 'Operadores',
                'scrap': 'Registros de scrap',
                'supervisor': 'Supervisores',
                'tipoacero': 'Tipos de acero',
                'tipopieza': 'Tipos de pieza',
                'turno': 'Turnos',
                'configuracionpiezasalambre': 'Configuracion de piezas',
                'espesor': 'Espesores',
                'numeropartecliente': 'Numeros de parte',
                'produccion': 'Produccion',
                'reasignaciontarjeta': 'Reasignacion de tarjetas',
                'statustar': 'Estatus de tarjetas',
                'tarjetaviajera': 'Tarjeta viajera',
                'rol': 'Roles',
                'usuario': 'Usuarios',
                'estatusliberacion': 'Estatus',
                'liberacion': 'Liberacion',
                'maquina': 'Maquinas',
                'tipolaminacion': 'Tipos de laminacion',
                'tira_liberacion': 'Tiras de liberacion',
            }
            actions = {
                'add': 'Agregar',
                'change': 'Editar',
                'delete': 'Eliminar',
                'view': 'Consultar',
                'view_reportes': 'Consultar reportes',
                'export_scrap': 'Exportar registros',
                'print_tarjetaviajera': 'Imprimir tarjetas',
                'update_status_tarjetaviajera': 'Actualizar estatus',
                'update_measurements_tarjetaviajera': 'Actualizar medidas',
                'view_produccion_scrap': 'Consultar producción',
                'change_produccion_scrap': 'Cambiar producción',
                'delete_formatoreclamacioninterna': 'Eliminar formatos',
            }
            action_label = actions.get(action)
            if action.startswith('change_'):
                action_label = action_label.replace('Cambiar', 'Editar') if action_label else 'Editar'
            if action_label is None:
                prefixes = (
                    ('add_', 'Agregar'),
                    ('change_', 'Cambiar'),
                    ('delete_', 'Eliminar'),
                    ('view_', 'Consultar'),
                )
                action_label = next(
                    (label for prefix, label in prefixes if action.startswith(prefix)),
                    permission.name.replace('Can ', '').capitalize(),
                )
                
            submodule_label = submodules.get(model, model.replace('_', ' ').title())
            return f"{modules.get(app, app.replace('_', ' ').title())} · {submodule_label} · {action_label}"

            return f"{modules.get(app, app.replace('_', ' ').title())} · {action_label}"

    list_display = ('id', 'nombre', 'cantidad_permisos')
    search_fields = ('nombre',)

    @admin.display(description='Permisos')
    def cantidad_permisos(self, obj):
        return obj.permissions.count()

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'nombre', 'rol', 'area',
        'is_active', 'is_staff', 'is_superuser',
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'rol', 'area')
    search_fields = ('username', 'email', 'nombre')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (
            'Información personal',
            {'fields': ('email', 'first_name', 'last_name')},
        ),
        (
            'Acceso al sistema',
            {'fields': ('is_active', 'is_staff', 'is_superuser')},
        ),
        (
            'Información de QMS',
            {
                'fields': (
                    'nombre', 'rol', 'area',
                )
            },
        ),
        ('Fechas importantes', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            'Información de QMS',
            {'fields': ('nombre', 'email', 'rol', 'area')},
        ),
    )
