from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.auth.models import Permission
from django.db import models


class Rol(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=25, unique=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='roles',
        verbose_name='permisos',
    )

    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.nombre


class UsuarioManager(UserManager):
    
    def create_superuser(
        self,
        username,
        email=None,
        password=None,
        **extra_fields
    ):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        extra_fields.setdefault('rol_id', 1)

        return self._create_user(
            username,
            email,
            password,
            **extra_fields
        )


class Usuario(AbstractUser):
    nombre = models.CharField(max_length=40)
    email = models.EmailField(unique=True)

    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        db_column='rol_id'
    )

    area = models.ForeignKey(
        'areas.Area',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_area'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    class Meta:
        db_table = 'usuarios'
