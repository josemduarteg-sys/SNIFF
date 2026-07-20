from django.conf import settings
from django.db import models

from apps.indicadores.models import IndicadorKPI


class ArchivoImportado(models.Model):
    ESTADO_IMPORTACION_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesado', 'Procesado'),
        ('procesado_con_errores', 'Procesado con errores'),
        ('fallido', 'Fallido'),
    ]

    nombre_archivo = models.CharField(max_length=255)
    tipo_archivo = models.CharField(max_length=20, default='CSV')
    ruta_archivo = models.CharField(max_length=500, blank=True, null=True)
    fecha_importacion = models.DateTimeField(auto_now_add=True)
    estado_importacion = models.CharField(
        max_length=30,
        choices=ESTADO_IMPORTACION_CHOICES,
        default='pendiente'
    )
    registros_procesados = models.PositiveIntegerField(default=0)
    registros_con_error = models.PositiveIntegerField(default=0)
    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='archivos_importados'
    )
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'archivo_importado'
        verbose_name = 'Archivo importado'
        verbose_name_plural = 'Archivos importados'
        ordering = ['-fecha_importacion']

    def __str__(self):
        return self.nombre_archivo


class ConexionDW(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    servidor = models.CharField(max_length=200)
    base_datos = models.CharField(max_length=150)
    esquema = models.CharField(max_length=100, blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'conexion_dw'
        verbose_name = 'Conexión Data Warehouse'
        verbose_name_plural = 'Conexiones Data Warehouse'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ConsultaDW(models.Model):
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('inactiva', 'Inactiva'),
        ('en_revision', 'En revisión'),
    ]

    conexion_dw = models.ForeignKey(
        ConexionDW,
        on_delete=models.PROTECT,
        related_name='consultas'
    )
    indicador = models.ForeignKey(
        IndicadorKPI,
        on_delete=models.PROTECT,
        related_name='consultas_dw'
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    consulta_referencia = models.TextField()
    frecuencia_ejecucion = models.CharField(max_length=50, default='Diaria')
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activa'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'consulta_dw'
        verbose_name = 'Consulta Data Warehouse'
        verbose_name_plural = 'Consultas Data Warehouse'
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['conexion_dw', 'indicador', 'nombre'],
                name='unique_consulta_dw_por_indicador'
            )
        ]

    def __str__(self):
        return self.nombre