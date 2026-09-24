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


class PlanEstrategico(models.Model):
    """Cabecera general de toda la planificación. Ya no depende de Área.

    Flujo de estados (un solo sentido, sin retorno):
        borrador -> en_uso -> cerrado
    'cerrado' es terminal: no existe reactivar ni volver a un estado previo.
    """

    ESTADO_BORRADOR = 'borrador'
    ESTADO_EN_USO = 'en_uso'
    ESTADO_CERRADO = 'cerrado'

    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, 'Borrador'),
        (ESTADO_EN_USO, 'En uso'),
        (ESTADO_CERRADO, 'Cerrado'),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_BORRADOR,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='planes_estrategicos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'plan_estrategico'
        verbose_name = 'Plan estratégico'
        verbose_name_plural = 'Planes estratégicos'
        ordering = ['-fecha_creacion']

    def clean(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                raise ValidationError(
                    'La fecha de finalización no puede ser anterior a la fecha de inicio.'
                )

    def esta_en_borrador(self):
        return self.estado == self.ESTADO_BORRADOR

    def esta_en_uso(self):
        return self.estado == self.ESTADO_EN_USO

    def esta_cerrado(self):
        return self.estado == self.ESTADO_CERRADO

    def __str__(self):
        return self.titulo


class ObjetivoGeneral(models.Model):
    """Objetivo macro de largo plazo del Plan estratégico. El texto del
    objetivo es autosuficiente: no tiene nombre ni descripción separados,
    ni fechas propias (su vigencia es la del Plan estratégico completo).

    No tiene un campo `estado` propio: su disponibilidad para edición la
    gobierna por completo el estado del Plan estratégico al que pertenece
    (editable mientras el plan no esté Cerrado; solo puede crearse mientras
    el plan está En uso). Ver apps/estrategia/services.py.
    """

    plan_estrategico = models.ForeignKey(
        PlanEstrategico,
        on_delete=models.PROTECT,
        related_name='objetivos_generales'
    )
    texto_objetivo = models.TextField()
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='objetivos_generales_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'objetivo_general'
        verbose_name = 'Objetivo general'
        verbose_name_plural = 'Objetivos generales'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.texto_objetivo[:80]
