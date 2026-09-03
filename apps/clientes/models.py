from django.db import models


class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        db_table = 'clientes'

    def __str__(self):
        return self.nombre
