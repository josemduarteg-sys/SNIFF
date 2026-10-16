from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.estrategia.models import ObjetivoEspecifico

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


class ConfiguracionMediciones(models.Model):
    """Bloque 4 (periodos y plazos): plazo adicional, en días calendario,
    para registrar una medición después del cierre de su periodo (reglas
    6/7 confirmadas por Hernán — "cinco o diez días" fueron ejemplos del
    valor, no un número fijo del sistema).

    Singleton: existe exactamente una fila (pk=1), sembrada por migración
    con el valor que ya regía en código antes de esta corrección (5), para
    no cambiar el comportamiento de nadie hasta que la administración lo
    edite explícitamente. Ver obtener()."""

    dias_plazo_registro = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text=(
            'Días calendario adicionales, contados desde el cierre del '
            'periodo, durante los cuales todavía se puede registrar la '
            'medición manualmente.'
        ),
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_mediciones'
        verbose_name = 'Configuración de mediciones'
        verbose_name_plural = 'Configuración de mediciones'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        configuracion, _ = cls.objects.get_or_create(pk=1)
        return configuracion

    def __str__(self):
        return f'Plazo de registro: {self.dias_plazo_registro} día(s)'


class IndicadorKPI(models.Model):
    """Bloque 3 del rediseño: el KPI pertenece a un ObjetivoEspecifico de un
    PlanAnual concreto (Opción A — un año, un registro de KPI). Por diseño
    NO guarda `anio`, `plan_anual` ni `plan_estrategico` propios: todo eso
    se deriva de `objetivo_especifico` a través de las propiedades de abajo,
    para no duplicar información ni acoplarse rígidamente a la jerarquía
    (ver notas de cada propiedad para la compatibilidad con una eventual
    Opción B futura, no implementada)."""

    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('autorizado', 'Autorizado'),
        ('anulado', 'Anulado'),
    ]

    objetivo_especifico = models.ForeignKey(
        ObjetivoEspecifico,
        on_delete=models.PROTECT,
        related_name='indicadores'
    )
    frecuencia = models.ForeignKey(
        Frecuencia,
        on_delete=models.PROTECT,
        related_name='indicadores'
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    formula_medicion = models.TextField(
        help_text=(
            'Explicación funcional de cómo se obtiene el resultado del KPI '
            '(no se interpreta ni se ejecuta). Ejemplo: "(Ventas actuales / '
            'Meta de ventas) × 100".'
        )
    )
    unidad_medida = models.CharField(max_length=50)

    valor_meta = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(0)],
        help_text='Meta del KPI para el año de su Plan anual.'
    )

    # Bloque 3, segunda parte (ponderaciones): importancia del KPI dentro
    # del cumplimiento anual de su (plan_anual, objetivo_general) — regla
    # 5/6 confirmada por Hernán. Nula por defecto ("sin ponderar todavía",
    # nunca 0%, ver services.calcular_ponderacion_kpi_ambito) y
    # deliberadamente independiente de valor_meta/estado/promedio
    # acumulado (regla 7: no son lo mismo, no se derivan entre sí).
    ponderacion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Peso del KPI dentro del 100% de su año y objetivo general. Vacío = sin ponderar todavía.'
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
                fields=['objetivo_especifico', 'nombre'],
                name='unique_indicador_por_objetivo_especifico'
            )
        ]

    def clean(self):
        if not self.formula_medicion or not self.formula_medicion.strip():
            raise ValidationError(
                'La fórmula de medición es obligatoria.'
            )

    def puede_modificarse(self):
        return self.estado == 'borrador'

    def esta_bloqueado(self):
        """True si el KPI no puede modificarse por el estado de su Plan
        anual o de su Plan estratégico ancestro (Cerrado congela toda la
        descendencia). Reutiliza el helper centralizado de Bloque 2 en vez
        de duplicar la regla acá."""
        from apps.estrategia.services import plan_anual_esta_bloqueado

        return plan_anual_esta_bloqueado(self.plan_anual)

    @property
    def plan_anual(self):
        """PlanAnual del KPI, derivado de objetivo_especifico. No se
        almacena en este modelo para no duplicar la relación (ver nota de
        clase) ni acoplar el KPI a un esquema donde en el futuro pudiera
        pertenecer a más de un año."""
        return self.objetivo_especifico.plan_anual

    @property
    def plan_estrategico(self):
        """PlanEstrategico del KPI, derivado transitivamente vía PlanAnual."""
        return self.plan_anual.plan_estrategico

    @property
    def objetivo_general(self):
        """ObjetivoGeneral del KPI, derivado de objetivo_especifico (Bloque
        3, KPI directo). Siempre disponible, incluso para un KPI directo:
        su objetivo_especifico "implícito" también enlaza con un
        ObjetivoGeneral real."""
        return self.objetivo_especifico.objetivo_general

    @property
    def es_directo(self):
        """True cuando este KPI no está asociado a un objetivo específico
        creado por un usuario, sino al objetivo específico 'implícito' que
        el sistema reutiliza para (plan_anual, objetivo_general) — ver
        apps/estrategia/services.obtener_o_crear_objetivo_especifico_directo."""
        return self.objetivo_especifico.es_generado_automaticamente

    @property
    def anio(self):
        """Año del KPI: SIEMPRE derivado de PlanAnual.anio, nunca un campo
        propio (así una eventual Opción B futura, donde un KPI conceptual
        se reutilice entre años, no exigiría migrar un campo `anio` fijo
        en IndicadorKPI)."""
        return self.plan_anual.anio

    @property
    def fecha_inicio_vigencia(self):
        """Vigencia real del KPI para el cálculo de periodos (Bloque 4,
        regla 4 confirmada por Hernán: la fecha de cierre de un periodo se
        determina a partir de la frecuencia del KPI Y de la vigencia de su
        PLAN ANUAL). Prioriza plan_anual.fecha_inicio (Bloque 1) cuando
        existe.

        Los Planes anuales anteriores al Bloque 1 tienen fecha_inicio/
        fecha_fin NULL (no se les inventa una fecha histórica, ver nota de
        PlanAnual.fecha_inicio) — para esos, se conserva el comportamiento
        previo a esta corrección: año calendario acotado por la vigencia
        del Plan estratégico."""
        plan_anual = self.plan_anual

        if plan_anual.fecha_inicio:
            return plan_anual.fecha_inicio

        inicio_anio = date(self.anio, 1, 1)
        inicio_plan = self.plan_estrategico.fecha_inicio

        if inicio_plan and inicio_plan > inicio_anio:
            return inicio_plan

        return inicio_anio

    @property
    def fecha_fin_vigencia(self):
        """Ver fecha_inicio_vigencia."""
        plan_anual = self.plan_anual

        if plan_anual.fecha_fin:
            return plan_anual.fecha_fin

        fin_anio = date(self.anio, 12, 31)
        fin_plan = self.plan_estrategico.fecha_fin

        if fin_plan and fin_plan < fin_anio:
            return fin_plan

        return fin_anio

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
    valor_maximo = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        blank=True,
        null=True,
        help_text='Límite superior del rango. Vacío/NULL significa "sin límite superior".'
    )
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'rango_kpi'
        verbose_name = 'Rango KPI'
        verbose_name_plural = 'Rangos KPI'
        ordering = ['indicador', 'valor_minimo']

    def clean(self):
        if self.valor_maximo is not None and self.valor_maximo < self.valor_minimo:
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
        ('bimestral', 'Bimestral'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
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


ARCHIVO_EVIDENCIA_EXTENSIONES = ('.pdf', '.jpg', '.jpeg')
ARCHIVO_EVIDENCIA_CONTENT_TYPES = ('application/pdf', 'image/jpeg', 'image/jpg')
ARCHIVO_EVIDENCIA_TAMANO_MAXIMO = 10 * 1024 * 1024  # 10 MB


def validar_archivo_evidencia(archivo):
    """Validación backend de la evidencia de una Medicion (Bloque 4): no se
    confía únicamente en el `accept` del navegador. Revisa extensión, tipo
    de contenido declarado y tamaño máximo."""
    import os

    nombre = getattr(archivo, 'name', '') or ''
    extension = os.path.splitext(nombre)[1].lower()

    if extension not in ARCHIVO_EVIDENCIA_EXTENSIONES:
        raise ValidationError('Solo se permiten archivos PDF, JPG o JPEG.')

    content_type = getattr(archivo, 'content_type', None)

    if content_type and content_type.lower() not in ARCHIVO_EVIDENCIA_CONTENT_TYPES:
        raise ValidationError('Solo se permiten archivos PDF, JPG o JPEG.')

    tamano = getattr(archivo, 'size', 0) or 0

    if tamano > ARCHIVO_EVIDENCIA_TAMANO_MAXIMO:
        raise ValidationError('El archivo no puede superar los 10 MB.')


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
        related_name='mediciones_registradas',
        blank=True,
        null=True,
        help_text='Vacío únicamente cuando la medición fue creada por el cierre automático del sistema.'
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
    fecha_medicion = models.DateField(
        help_text='Fecha de cierre del periodo medido (no la fecha en que se registró).'
    )
    valor_resultado = models.DecimalField(max_digits=14, decimal_places=4)
    observacion = models.TextField(blank=True, null=True)
    evidencia = models.FileField(
        upload_to='evidencias/mediciones/%Y/%m/',
        blank=True,
        null=True,
        validators=[validar_archivo_evidencia],
        help_text='Respaldo opcional de la medición. Solo PDF, JPG o JPEG, máximo 10 MB.'
    )
    cierre_automatico = models.BooleanField(
        default=False,
        help_text='True cuando el sistema creó esta medición automáticamente en 0.00 por vencimiento de la ventana de registro.'
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
    
