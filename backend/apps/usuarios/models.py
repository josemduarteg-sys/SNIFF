from django.db import models
from django.contrib.auth.models import AbstractUser


class Rol(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rol'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        related_name='usuarios',
        null=True,
        blank=True
    )
    correo = models.EmailField(unique=True)
    estado = models.BooleanField(default=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)

    email = models.EmailField(blank=True)

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.username
    
     