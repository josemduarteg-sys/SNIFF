from django.conf import settings
from django.db import models


class Bitacora(models.Model):
    ACCION_CHOICES = [
        ('crear', 'Crear'),
        ('actualizar', 'Actualizar'),
        ('eliminar', 'Eliminar'),
        ('consultar', 'Consultar'),
        ('importar_csv', 'Importar CSV'),
        ('consulta_dw', 'Consulta Data Warehouse'),
        ('inicio_sesion', 'Inicio de sesión'),
        ('cierre_sesion', 'Cierre de sesión'),
        ('error', 'Error'),
    ]

    # Etapa 4 (auditoría M7): NULL solo en eventos ejecutados por el propio
    # sistema (tareas automáticas), registrados con
    # services.registrar_bitacora_sistema(). Las acciones de usuarios
    # siempre llevan usuario (registrar_bitacora lo exige).
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='registros_bitacora',
        null=True,
        blank=True,
        help_text='Vacío únicamente en eventos ejecutados automáticamente por el sistema.',
    )
    accion = models.CharField(
        max_length=50,
        choices=ACCION_CHOICES
    )
    modulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    fecha_hora = models.DateTimeField(auto_now_add=True)
    ip_usuario = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'bitacora'
        verbose_name = 'Bitácora'
        verbose_name_plural = 'Bitácoras'
        ordering = ['-fecha_hora']

    ORIGEN_USUARIO = 'usuario'
    ORIGEN_SISTEMA = 'sistema'
    NOMBRE_SISTEMA = 'Sistema'

    @property
    def origen(self):
        return self.ORIGEN_SISTEMA if self.usuario_id is None else self.ORIGEN_USUARIO

    @property
    def autor(self):
        return self.NOMBRE_SISTEMA if self.usuario_id is None else self.usuario.username

    def __str__(self):
        return f'{self.autor} - {self.accion} - {self.modulo}'


class Notificacion(models.Model):
    usuario_destino = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    tipo = models.CharField(max_length=80)
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    enlace = models.CharField(max_length=255, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificacion'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.usuario_destino} - {self.titulo}'