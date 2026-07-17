from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Area(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'area'
        verbose_name = 'Área'
        verbose_name_plural = 'Áreas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Estrategia(models.Model):
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('en_revision', 'En revisión'),
        ('finalizada', 'Finalizada'),
        ('inactiva', 'Inactiva'),
    ]

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name='estrategias'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='estrategias_creadas'
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activa'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'estrategia'
        verbose_name = 'Estrategia'
        verbose_name_plural = 'Estrategias'
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(
                fields=['area', 'nombre'],
                name='unique_estrategia_por_area'
            )
        ]

    def clean(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                raise ValidationError(
                    'La fecha de finalización no puede ser anterior a la fecha de inicio.'
                )

    def __str__(self):
        return self.nombre


class Objetivo(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('en_revision', 'En revisión'),
        ('finalizado', 'Finalizado'),
        ('inactivo', 'Inactivo'),
    ]

    estrategia = models.ForeignKey(
        Estrategia,
        on_delete=models.PROTECT,
        related_name='objetivos'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='objetivos_creados'
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'objetivo'
        verbose_name = 'Objetivo'
        verbose_name_plural = 'Objetivos'
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(
                fields=['estrategia', 'nombre'],
                name='unique_objetivo_por_estrategia'
            )
        ]

    def clean(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                raise ValidationError(
                    'La fecha de finalización no puede ser anterior a la fecha de inicio.'
                )

    def __str__(self):
        return self.nombre
    
     