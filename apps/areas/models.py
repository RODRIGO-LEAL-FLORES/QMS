

from django.db import models


class Area(models.Model):
    id_area = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'areas'

    def __str__(self):
        return self.nombre