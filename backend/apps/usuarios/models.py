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
    debe_cambiar_password = models.BooleanField(default=False)

    email = models.EmailField(blank=True)

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.username


class SolicitudRestablecimientoPassword(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('atendida', 'Atendida'),
    ]

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='solicitudes_restablecimiento',
    )
    identificador_ingresado = models.CharField(max_length=150)
    motivo = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    fecha_atencion = models.DateTimeField(null=True, blank=True)
    revisado_por = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='solicitudes_revisadas',
    )
    atendido_por = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='solicitudes_atendidas',
    )
    observacion_admin = models.TextField(blank=True)

    class Meta:
        db_table = 'solicitud_restablecimiento_password'
        verbose_name = 'Solicitud de restablecimiento de contraseña'
        verbose_name_plural = 'Solicitudes de restablecimiento de contraseña'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'{self.usuario} - {self.estado}'
