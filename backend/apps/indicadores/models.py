from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.estrategia.models import Objetivo

class Frecuencia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'frecuencia'
        verbose_name = 'Frecuencia'
        verbose_name_plural = 'Frecuencias'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class TipoCalculo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'tipo_calculo'
        verbose_name = 'Tipo de cálculo'
        verbose_name_plural = 'Tipos de cálculo'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class FuenteDato(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'fuente_dato'
        verbose_name = 'Fuente de dato'
        verbose_name_plural = 'Fuentes de datos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class IndicadorKPI(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('autorizado', 'Autorizado'),
        ('inactivo', 'Inactivo'),
        ('anulado', 'Anulado'),
    ]

    objetivo = models.ForeignKey(
        Objetivo,
        on_delete=models.PROTECT,
        related_name='indicadores'
    )
    frecuencia = models.ForeignKey(
        Frecuencia,
        on_delete=models.PROTECT,
        related_name='indicadores'
    )
    tipo_calculo = models.ForeignKey(
        TipoCalculo,
        on_delete=models.PROTECT,
        related_name='indicadores'
    )
    fuente_dato = models.ForeignKey(
        FuenteDato,
        on_delete=models.PROTECT,
        related_name='indicadores'
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    unidad_medida = models.CharField(max_length=50)

    valor_meta = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        help_text='Meta total esperada para el KPI durante su vigencia.'
    )
    fecha_inicio = models.DateField(
        blank=True,
        null=True,
        help_text='Fecha de inicio de vigencia del KPI.'
    )
    fecha_fin = models.DateField(
        blank=True,
        null=True,
        help_text='Fecha final esperada para cumplir el KPI.'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador'
    )

    fecha_autorizacion = models.DateTimeField(blank=True, null=True)
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='kpis_autorizados',
        blank=True,
        null=True
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='indicadores_creados',
        blank=True,
        null=True
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'indicador_kpi'
        verbose_name = 'Indicador KPI'
        verbose_name_plural = 'Indicadores KPI'
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['objetivo', 'nombre'],
                name='unique_indicador_por_objetivo'
            )
        ]

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                'La fecha de finalización no puede ser anterior a la fecha de inicio.'
            )

    def puede_modificarse(self):
        return self.estado == 'borrador'

    def __str__(self):
        return self.nombre


class MetaKPI(models.Model):
    ESTADO_CHOICES = [
        ('vigente', 'Vigente'),
        ('historial', 'Historial'),
        ('inactiva', 'Inactiva'),
    ]

    indicador = models.ForeignKey(
        IndicadorKPI,
        on_delete=models.PROTECT,
        related_name='metas'
    )
    valor_meta = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(0)]
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='vigente'
    )

    class Meta:
        db_table = 'meta_kpi'
        verbose_name = 'Meta KPI'
        verbose_name_plural = 'Metas KPI'
        ordering = ['-fecha_inicio']

    def clean(self):
        if self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                'La fecha de finalización no puede ser anterior a la fecha de inicio.'
            )

    def __str__(self):
        return f'{self.indicador.nombre} - {self.valor_meta}'


class ResponsableKPI(models.Model):
    indicador = models.ForeignKey(
        IndicadorKPI,
        on_delete=models.PROTECT,
        related_name='responsables'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='kpis_responsables'
    )
    fecha_asignacion = models.DateField(auto_now_add=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'responsable_kpi'
        verbose_name = 'Responsable KPI'
        verbose_name_plural = 'Responsables KPI'
        constraints = [
            models.UniqueConstraint(
                fields=['indicador', 'usuario'],
                name='unique_responsable_por_indicador'
            )
        ]

    def __str__(self):
        return f'{self.usuario} - {self.indicador}'


class EstadoCumplimiento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=30)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'estado_cumplimiento'
        verbose_name = 'Estado de cumplimiento'
        verbose_name_plural = 'Estados de cumplimiento'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class RangoKPI(models.Model):
    indicador = models.ForeignKey(
        IndicadorKPI,
        on_delete=models.PROTECT,
        related_name='rangos'
    )
    estado_cumplimiento = models.ForeignKey(
        EstadoCumplimiento,
        on_delete=models.PROTECT,
        related_name='rangos'
    )
    valor_minimo = models.DecimalField(max_digits=14, decimal_places=4)
    valor_maximo = models.DecimalField(max_digits=14, decimal_places=4)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'rango_kpi'
        verbose_name = 'Rango KPI'
        verbose_name_plural = 'Rangos KPI'
        ordering = ['indicador', 'valor_minimo']

    def clean(self):
        if self.valor_maximo < self.valor_minimo:
            raise ValidationError(
                'El valor máximo no puede ser menor que el valor mínimo.'
            )

    def __str__(self):
        return f'{self.indicador.nombre}: {self.valor_minimo} - {self.valor_maximo}'


class PeriodoMedicion(models.Model):
    TIPO_PERIODO_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
        ('anual', 'Anual'),
    ]

    tipo_periodo = models.CharField(max_length=20, choices=TIPO_PERIODO_CHOICES)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    anio = models.PositiveIntegerField()
    mes = models.PositiveIntegerField(blank=True, null=True)
    semana = models.PositiveIntegerField(blank=True, null=True)
    dia = models.PositiveIntegerField(blank=True, null=True)
    descripcion = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        db_table = 'periodo_medicion'
        verbose_name = 'Periodo de medición'
        verbose_name_plural = 'Periodos de medición'
        ordering = ['-fecha_inicio']
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_periodo', 'fecha_inicio', 'fecha_fin'],
                name='unique_periodo_medicion'
            )
        ]

    def clean(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                'La fecha de finalización no puede ser anterior a la fecha de inicio.'
            )

    def __str__(self):
        return f'{self.tipo_periodo} - {self.fecha_inicio} a {self.fecha_fin}'


class Medicion(models.Model):
    indicador = models.ForeignKey(
        IndicadorKPI,
        on_delete=models.PROTECT,
        related_name='mediciones'
    )
    meta = models.ForeignKey(
        MetaKPI,
        on_delete=models.PROTECT,
        related_name='mediciones'
    )
    estado_cumplimiento = models.ForeignKey(
        EstadoCumplimiento,
        on_delete=models.PROTECT,
        related_name='mediciones'
    )
    periodo = models.ForeignKey(
        PeriodoMedicion,
        on_delete=models.PROTECT,
        related_name='mediciones'
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='mediciones_registradas'
    )
    archivo_importado = models.ForeignKey(
        'integraciones.ArchivoImportado',
        on_delete=models.PROTECT,
        related_name='mediciones',
        blank=True,
        null=True
    )
    consulta_dw = models.ForeignKey(
        'integraciones.ConsultaDW',
        on_delete=models.PROTECT,
        related_name='mediciones',
        blank=True,
        null=True
    )
    fecha_medicion = models.DateField()
    valor_resultado = models.DecimalField(max_digits=14, decimal_places=4)
    observacion = models.TextField(blank=True, null=True)
    evidencia = models.TextField(
        blank=True,
        null=True,
        help_text='Evidencias, respaldo o detalle de lo realizado durante la medición.'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'medicion'
        verbose_name = 'Medición'
        verbose_name_plural = 'Mediciones'
        ordering = ['-fecha_medicion']
        constraints = [
            models.UniqueConstraint(
                fields=['indicador', 'periodo'],
                name='unique_medicion_por_indicador_periodo'
            )
        ]

    def clean(self):
        if self.meta.indicador_id != self.indicador_id:
            raise ValidationError(
                'La meta seleccionada no pertenece al indicador KPI.'
            )

    def calcular_cumplimiento(self):
        if self.meta.valor_meta == 0:
            return 0

        return (self.valor_resultado / self.meta.valor_meta) * 100

    def __str__(self):
        return f'{self.indicador.nombre} - {self.fecha_medicion}'


class Alerta(models.Model):
    ESTADO_ALERTA_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('revisada', 'Revisada'),
        ('descartada', 'Descartada'),
    ]

    indicador = models.ForeignKey(
        IndicadorKPI,
        on_delete=models.PROTECT,
        related_name='alertas'
    )
    medicion = models.ForeignKey(
        Medicion,
        on_delete=models.PROTECT,
        related_name='alertas',
        blank=True,
        null=True
    )
    tipo_alerta = models.CharField(max_length=100)
    mensaje = models.TextField()
    estado_alerta = models.CharField(
        max_length=20,
        choices=ESTADO_ALERTA_CHOICES,
        default='pendiente'
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(blank=True, null=True)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='alertas_revisadas',
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'alerta'
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f'{self.tipo_alerta} - {self.indicador.nombre}'
    
