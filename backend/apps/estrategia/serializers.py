from django.db.models import Q
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import (
    Area,
    ObjetivoEspecifico,
    ObjetivoGeneral,
    PlanAnual,
    PlanEstrategico,
    PonderacionAnualObjetivoGeneral,
)
from .services import (
    objetivo_especifico_esta_bloqueado,
    objetivo_especifico_tiene_dependencias,
    objetivo_general_tiene_dependencias,
    plan_anual_esta_bloqueado,
    plan_anual_tiene_dependencias,
    plan_estrategico_esta_cerrado,
    puede_completar_vigencia_plan_anual,
    resumen_ponderacion_anual,
)


def _cambia_relacion(data, instance, campo):
    """True si el payload trae `campo` apuntando a un registro distinto del
    actual de `instance`. Reenviar el mismo id (lo que hace el formulario
    al editar solo el texto) no cuenta como cambio."""
    if instance is None or campo not in data:
        return False

    nuevo = data[campo]
    return getattr(nuevo, 'pk', nuevo) != getattr(instance, f'{campo}_id')


class AreaSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(
        max_length=150,
        validators=[
            UniqueValidator(
                queryset=Area.objects.all(),
                message='Ya existe un área registrada con ese nombre.'
            )
        ]
    )

    class Meta:
        model = Area
        fields = [
            'id',
            'nombre',
            'descripcion',
            'estado',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion']


class PlanEstrategicoSerializer(serializers.ModelSerializer):
    creado_por_username = serializers.CharField(
        source='creado_por.username',
        read_only=True
    )

    # Campos que quedan bloqueados según el estado del plan. Título y periodo
    # se bloquean apenas pasa a "en_uso"; en "cerrado" ya no se puede tocar
    # ningún dato principal (la descripción incluida).
    CAMPOS_BLOQUEADOS_EN_USO = {'titulo', 'fecha_inicio', 'fecha_fin'}
    CAMPOS_BLOQUEADOS_CERRADO = {'titulo', 'descripcion', 'fecha_inicio', 'fecha_fin'}

    class Meta:
        model = PlanEstrategico
        fields = [
            'id',
            'titulo',
            'descripcion',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'creado_por',
            'creado_por_username',
            'fecha_creacion',
        ]
        # El estado NUNCA se edita por un PATCH/PUT normal: solo cambia a
        # través de las transiciones explícitas (poner_en_uso / cerrar) en
        # la vista, que además son exclusivas de administrador.
        read_only_fields = ['id', 'estado', 'fecha_creacion', 'creado_por']

    def validate(self, data):
        instance = self.instance

        if instance is not None:
            if plan_estrategico_esta_cerrado(instance):
                raise serializers.ValidationError(
                    'El Plan estratégico está Cerrado y no permite modificaciones.'
                )

            if instance.esta_en_uso():
                campos_intentados = self.CAMPOS_BLOQUEADOS_EN_USO.intersection(data.keys())

                if campos_intentados:
                    raise serializers.ValidationError(
                        'El título y el periodo no pueden modificarse mientras el '
                        'Plan estratégico está En uso. Solo la descripción es editable.'
                    )

        fecha_inicio = data.get('fecha_inicio', getattr(instance, 'fecha_inicio', None))
        fecha_fin = data.get('fecha_fin', getattr(instance, 'fecha_fin', None))

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError({
                'fecha_fin': 'La fecha fin no puede ser menor que la fecha inicio.'
            })

        return data


class ObjetivoGeneralSerializer(serializers.ModelSerializer):
    plan_estrategico_titulo = serializers.CharField(
        source='plan_estrategico.titulo',
        read_only=True
    )
    # Expuesto para que el frontend pueda ocultar la acción "Editar" cuando
    # el plan está Cerrado. El bloqueo real (lo que de verdad protege el
    # dato) es la validación de abajo, no este campo — es solo para UX.
    plan_estrategico_estado = serializers.CharField(
        source='plan_estrategico.estado',
        read_only=True
    )
    creado_por_username = serializers.CharField(
        source='creado_por.username',
        read_only=True
    )
    # Etapa 1 (A1): solo para que el frontend desactive el selector de
    # Plan estratégico; el bloqueo real lo aplica validate().
    puede_cambiar_plan_estrategico = serializers.SerializerMethodField()

    class Meta:
        model = ObjetivoGeneral
        fields = [
            'id',
            'plan_estrategico',
            'plan_estrategico_titulo',
            'plan_estrategico_estado',
            'texto_objetivo',
            'puede_cambiar_plan_estrategico',
            'creado_por',
            'creado_por_username',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'creado_por']

    def get_puede_cambiar_plan_estrategico(self, obj):
        return not objetivo_general_tiene_dependencias(obj)

    def validate(self, data):
        instance = self.instance
        plan = data.get('plan_estrategico') or getattr(instance, 'plan_estrategico', None)

        if not plan:
            raise serializers.ValidationError({
                'plan_estrategico': 'Debe seleccionar un Plan estratégico.'
            })

        if instance is None:
            # Creación: solo sobre un Plan estratégico En uso.
            if not plan.esta_en_uso():
                raise serializers.ValidationError({
                    'plan_estrategico': (
                        'Solo se pueden crear objetivos generales sobre un '
                        'Plan estratégico En uso.'
                    )
                })
        else:
            # Edición: bloqueada por completo si el plan está Cerrado.
            if plan_estrategico_esta_cerrado(plan):
                raise serializers.ValidationError(
                    'El Plan estratégico está Cerrado y no permite modificar sus '
                    'objetivos generales.'
                )

            # Etapa 1 (A1): traslado a otro Plan estratégico. Prohibido si
            # ya tiene descendencia; sin ella, el destino debe cumplir la
            # misma regla que una creación (Plan estratégico En uso).
            if _cambia_relacion(data, instance, 'plan_estrategico'):
                if plan_estrategico_esta_cerrado(instance.plan_estrategico):
                    raise serializers.ValidationError(
                        'El Plan estratégico actual está Cerrado y no permite '
                        'trasladar sus objetivos generales.'
                    )

                if objetivo_general_tiene_dependencias(instance):
                    raise serializers.ValidationError({
                        'plan_estrategico': (
                            'No se puede cambiar el Plan estratégico de un objetivo '
                            'general que ya tiene objetivos específicos, KPI o '
                            'ponderaciones anuales asociados.'
                        )
                    })

                if not plan.esta_en_uso():
                    raise serializers.ValidationError({
                        'plan_estrategico': (
                            'Solo se puede trasladar un objetivo general a un '
                            'Plan estratégico En uso.'
                        )
                    })

        return data


class PlanAnualSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    plan_estrategico_titulo = serializers.CharField(
        source='plan_estrategico.titulo',
        read_only=True
    )
    # Igual que en ObjetivoGeneralSerializer: expuesto solo para que el
    # frontend pueda ocultar acciones cuando el plan padre está Cerrado.
    # El bloqueo real lo aplica la validación de abajo.
    plan_estrategico_estado = serializers.CharField(
        source='plan_estrategico.estado',
        read_only=True
    )
    creado_por_username = serializers.CharField(
        source='creado_por.username',
        read_only=True
    )

    class Meta:
        model = PlanAnual
        fields = [
            'id',
            'plan_estrategico',
            'plan_estrategico_titulo',
            'plan_estrategico_estado',
            'anio',
            'nombre',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'puede_cambiar_plan_estrategico',
            'puede_completar_vigencia',
            'creado_por',
            'creado_por_username',
            'fecha_creacion',
        ]
        # El estado NUNCA se edita por PATCH/PUT normal: solo cambia a
        # través de las transiciones explícitas (poner_en_uso / cerrar).
        read_only_fields = ['id', 'estado', 'fecha_creacion', 'creado_por']
        # DRF genera automáticamente un UniqueTogetherValidator a partir de
        # la UniqueConstraint del modelo (plan_estrategico, anio). Ese
        # validador corre ANTES que validate() de abajo y devuelve un
        # mensaje técnico en non_field_errors ("Los campos ... deben formar
        # un conjunto único."). Se desactiva acá para que el único chequeo
        # de duplicado sea el de validate(), con mensaje en español natural.
        # La constraint en el modelo (y en la base de datos) sigue intacta:
        # esto solo evita que DRF la revalide con su mensaje genérico.
        validators = []

    # Etapa 1 (M9): solo UX; el bloqueo real lo aplica validate().
    puede_cambiar_plan_estrategico = serializers.SerializerMethodField()

    def get_nombre(self, obj):
        return obj.nombre

    def get_puede_cambiar_plan_estrategico(self, obj):
        return obj.esta_en_borrador() and not plan_anual_tiene_dependencias(obj)

    # Etapa 1 (M9): solo UX; la regla real la aplica
    # CompletarVigenciaPlanAnualSerializer.
    puede_completar_vigencia = serializers.SerializerMethodField()

    def get_puede_completar_vigencia(self, obj):
        return puede_completar_vigencia_plan_anual(obj)

    def validate(self, data):
        instance = self.instance
        plan_estrategico = data.get('plan_estrategico') or getattr(instance, 'plan_estrategico', None)
        anio = data.get('anio', getattr(instance, 'anio', None))

        if not plan_estrategico:
            raise serializers.ValidationError({
                'plan_estrategico': 'Seleccioná un plan estratégico.'
            })

        if instance is None:
            # Creación: solo sobre un Plan estratégico En uso (esto también
            # descarta Borrador y Cerrado con un único chequeo).
            if not plan_estrategico.esta_en_uso():
                raise serializers.ValidationError({
                    'plan_estrategico': (
                        'Solo se pueden crear planes anuales sobre un Plan '
                        'estratégico En uso.'
                    )
                })
        else:
            if plan_anual_esta_bloqueado(instance):
                raise serializers.ValidationError(
                    'El Plan anual está Cerrado (o su Plan estratégico lo está) y '
                    'no permite modificaciones.'
                )

            campos_bloqueados_en_uso = {'plan_estrategico', 'anio', 'fecha_inicio', 'fecha_fin'}

            if instance.esta_en_uso() and campos_bloqueados_en_uso.intersection(data.keys()):
                raise serializers.ValidationError(
                    'El plan estratégico, el año y las fechas de vigencia no pueden '
                    'modificarse mientras el Plan anual está En uso.'
                )

            # Etapa 1 (M9, integridad): en Borrador ya puede tener
            # ponderaciones anuales; trasladarlo dejaría esas filas
            # mezclando objetivos generales de otra estrategia.
            if (
                _cambia_relacion(data, instance, 'plan_estrategico')
                and plan_anual_tiene_dependencias(instance)
            ):
                raise serializers.ValidationError({
                    'plan_estrategico': (
                        'No se puede cambiar el Plan estratégico de un plan anual '
                        'que ya tiene objetivos específicos o ponderaciones anuales '
                        'asociados.'
                    )
                })

        if anio is None:
            raise serializers.ValidationError({'anio': 'Ingresá el año del plan anual.'})

        if plan_estrategico.fecha_inicio and anio < plan_estrategico.fecha_inicio.year:
            raise serializers.ValidationError({
                'anio': 'El año debe estar dentro de la vigencia del Plan estratégico.'
            })

        if plan_estrategico.fecha_fin and anio > plan_estrategico.fecha_fin.year:
            raise serializers.ValidationError({
                'anio': 'El año debe estar dentro de la vigencia del Plan estratégico.'
            })

        duplicados = PlanAnual.objects.filter(plan_estrategico=plan_estrategico, anio=anio)

        if instance is not None:
            duplicados = duplicados.exclude(pk=instance.pk)

        if duplicados.exists():
            raise serializers.ValidationError({
                'anio': 'Ya existe un plan anual para ese año.'
            })

        # Fechas de vigencia (corrección Hernán, bloque 1). Obligatorias
        # SOLO para registros nuevos — los existentes pueden quedar sin
        # fecha (ver nota en el modelo) hasta que se completen a mano.
        fecha_inicio = data.get('fecha_inicio', getattr(instance, 'fecha_inicio', None))
        fecha_fin = data.get('fecha_fin', getattr(instance, 'fecha_fin', None))

        if instance is None:
            if not fecha_inicio:
                raise serializers.ValidationError({
                    'fecha_inicio': 'Ingresá la fecha de inicio del plan anual.'
                })

            if not fecha_fin:
                raise serializers.ValidationError({
                    'fecha_fin': 'Ingresá la fecha de finalización del plan anual.'
                })

        validar_rango_fechas_plan_anual(plan_estrategico, fecha_inicio, fecha_fin)

        # Coherencia fecha <-> año: solo se exige en registros nuevos (en
        # edición, ni anio ni las fechas pueden tocarse por separado salvo
        # que el plan siga en Borrador, en cuyo caso ambos se revalidan
        # igual con los valores finales ya combinados arriba).
        if instance is None or 'anio' in data or 'fecha_inicio' in data or 'fecha_fin' in data:
            validar_fechas_en_anio_plan_anual(anio, fecha_inicio, fecha_fin)

        return data


def validar_rango_fechas_plan_anual(plan_estrategico, fecha_inicio, fecha_fin):
    """Reglas de vigencia del Plan anual (Bloque 1), compartidas entre la
    edición normal (PlanAnualSerializer) y el completado único de fechas de
    planes antiguos (CompletarVigenciaPlanAnualSerializer)."""
    if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
        raise serializers.ValidationError({
            'fecha_fin': 'La fecha de finalización no puede ser anterior a la fecha de inicio.'
        })

    if fecha_inicio and plan_estrategico.fecha_inicio and fecha_inicio < plan_estrategico.fecha_inicio:
        raise serializers.ValidationError({
            'fecha_inicio': 'La fecha de inicio debe estar dentro de la vigencia del Plan estratégico.'
        })

    if fecha_fin and plan_estrategico.fecha_fin and fecha_fin > plan_estrategico.fecha_fin:
        raise serializers.ValidationError({
            'fecha_fin': 'La fecha de finalización debe estar dentro de la vigencia del Plan estratégico.'
        })


def validar_fechas_en_anio_plan_anual(anio, fecha_inicio, fecha_fin):
    if fecha_inicio and fecha_inicio.year != anio:
        raise serializers.ValidationError({
            'fecha_inicio': 'La fecha de inicio debe pertenecer al año seleccionado.'
        })

    if fecha_fin and fecha_fin.year != anio:
        raise serializers.ValidationError({
            'fecha_fin': 'La fecha de finalización debe pertenecer al año seleccionado.'
        })


class CompletarVigenciaPlanAnualSerializer(serializers.Serializer):
    """Etapa 1 (auditoría M9, autorizado el 20/10/2026): completa POR ÚNICA
    VEZ las fechas de vigencia de un Plan anual En uso creado antes del
    Bloque 1 (ambas fechas NULL). Una vez guardadas, la regla normal de
    PlanAnualSerializer (fechas bloqueadas En uso) vuelve a aplicar, así
    que no existe un segundo completado.

    Las fechas las ingresa una persona: nunca se asignan automáticamente."""

    fecha_inicio = serializers.DateField(
        error_messages={'required': 'Ingresá la fecha de inicio del plan anual.'},
    )
    fecha_fin = serializers.DateField(
        error_messages={'required': 'Ingresá la fecha de finalización del plan anual.'},
    )

    def validate(self, data):
        plan_anual = self.instance

        if not puede_completar_vigencia_plan_anual(plan_anual):
            raise serializers.ValidationError(
                'Solo se pueden completar las fechas de un Plan anual En uso, con '
                'su Plan estratégico abierto y sin fechas de vigencia registradas.'
            )

        fecha_inicio = data['fecha_inicio']
        fecha_fin = data['fecha_fin']

        validar_rango_fechas_plan_anual(plan_anual.plan_estrategico, fecha_inicio, fecha_fin)
        validar_fechas_en_anio_plan_anual(plan_anual.anio, fecha_inicio, fecha_fin)

        # Los periodos de un KPI se cuentan por mes desde el mes de
        # fecha_inicio hasta el mes de fecha_fin (ver
        # IndicadorKPI.fecha_inicio_vigencia y
        # services.obtener_info_siguiente_periodo); una medición cuyo
        # periodo empiece fuera de ese rango quedaría excluida.
        from datetime import date

        from apps.indicadores.models import Medicion

        primer_mes = date(fecha_inicio.year, fecha_inicio.month, 1)
        ultimo_mes = date(fecha_fin.year, fecha_fin.month, 1)

        excluidas = Medicion.objects.filter(
            indicador__objetivo_especifico__plan_anual=plan_anual,
        ).filter(
            Q(periodo__fecha_inicio__lt=primer_mes) | Q(periodo__fecha_inicio__gt=ultimo_mes)
        )

        if excluidas.exists():
            raise serializers.ValidationError(
                'Las fechas dejan fuera de la vigencia periodos que ya tienen '
                f'mediciones registradas ({excluidas.count()}). Ajustá la vigencia '
                'para que los incluya.'
            )

        return data

    def update(self, instance, validated_data):
        instance.fecha_inicio = validated_data['fecha_inicio']
        instance.fecha_fin = validated_data['fecha_fin']
        instance.save(update_fields=['fecha_inicio', 'fecha_fin'])
        return instance


class ObjetivoEspecificoSerializer(serializers.ModelSerializer):
    plan_anual_nombre = serializers.SerializerMethodField()
    plan_anual_estado = serializers.CharField(
        source='plan_anual.estado',
        read_only=True
    )
    plan_estrategico_titulo = serializers.CharField(
        source='plan_anual.plan_estrategico.titulo',
        read_only=True
    )
    # Igual criterio que arriba: expuesto para que el frontend oculte
    # acciones; el bloqueo real lo aplica la validación de abajo.
    plan_estrategico_estado = serializers.CharField(
        source='plan_anual.plan_estrategico.estado',
        read_only=True
    )
    objetivo_general_texto = serializers.CharField(
        source='objetivo_general.texto_objetivo',
        read_only=True
    )
    creado_por_username = serializers.CharField(
        source='creado_por.username',
        read_only=True
    )

    class Meta:
        model = ObjetivoEspecifico
        fields = [
            'id',
            'plan_anual',
            'plan_anual_nombre',
            'plan_anual_estado',
            'plan_estrategico_titulo',
            'plan_estrategico_estado',
            'objetivo_general',
            'objetivo_general_texto',
            'texto_objetivo',
            'es_generado_automaticamente',
            'puede_cambiar_relaciones',
            'creado_por',
            'creado_por_username',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'creado_por', 'es_generado_automaticamente']

    # Etapa 1 (A2): solo UX; el bloqueo real lo aplica validate().
    puede_cambiar_relaciones = serializers.SerializerMethodField()

    def get_plan_anual_nombre(self, obj):
        return obj.plan_anual.nombre if obj.plan_anual_id else None

    def get_puede_cambiar_relaciones(self, obj):
        return (
            not obj.es_generado_automaticamente
            and not objetivo_especifico_tiene_dependencias(obj)
        )

    def validate(self, data):
        instance = self.instance
        plan_anual = data.get('plan_anual') or getattr(instance, 'plan_anual', None)
        objetivo_general = data.get('objetivo_general') or getattr(instance, 'objetivo_general', None)

        if not plan_anual:
            raise serializers.ValidationError({
                'plan_anual': 'Seleccioná un plan anual.'
            })

        if not objetivo_general:
            raise serializers.ValidationError({
                'objetivo_general': 'Seleccioná un objetivo general.'
            })

        if objetivo_general.plan_estrategico_id != plan_anual.plan_estrategico_id:
            raise serializers.ValidationError({
                'objetivo_general': (
                    'El objetivo general debe pertenecer al mismo Plan estratégico '
                    'que el Plan anual seleccionado.'
                )
            })

        if instance is None:
            # Creación: solo dentro de un Plan anual En uso, y su Plan
            # estratégico padre no puede estar Cerrado (plan_anual_esta_bloqueado
            # ya contempla ambos casos).
            if not plan_anual.esta_en_uso() or plan_anual_esta_bloqueado(plan_anual):
                raise serializers.ValidationError({
                    'plan_anual': (
                        'Solo se pueden crear objetivos específicos dentro de un '
                        'Plan anual En uso.'
                    )
                })
        else:
            if objetivo_especifico_esta_bloqueado(instance):
                raise serializers.ValidationError(
                    'El objetivo específico está bloqueado y no permite modificaciones.'
                )

            # Etapa 1 (A2): los objetivos implícitos de KPI directo ya
            # quedan fuera del queryset del ViewSet; esto es el resguardo
            # por si el serializer se reutiliza en otro lugar.
            if instance.es_generado_automaticamente:
                raise serializers.ValidationError(
                    'Este objetivo específico es interno del sistema (KPI directo) '
                    'y no puede modificarse.'
                )

            cambia_plan_anual = _cambia_relacion(data, instance, 'plan_anual')
            cambia_objetivo_general = _cambia_relacion(data, instance, 'objetivo_general')

            if cambia_plan_anual or cambia_objetivo_general:
                if objetivo_especifico_tiene_dependencias(instance):
                    raise serializers.ValidationError({
                        'plan_anual' if cambia_plan_anual else 'objetivo_general': (
                            'No se puede cambiar el plan anual ni el objetivo general '
                            'de un objetivo específico que ya tiene KPI asociados.'
                        )
                    })

                # Sin KPI, el traslado debe cumplir la misma regla que una
                # creación: destino En uso y no bloqueado.
                if not plan_anual.esta_en_uso() or plan_anual_esta_bloqueado(plan_anual):
                    raise serializers.ValidationError({
                        'plan_anual': (
                            'Solo se puede trasladar un objetivo específico a un '
                            'Plan anual En uso.'
                        )
                    })

        return data


class PonderacionAnualObjetivoGeneralSerializer(serializers.ModelSerializer):
    """Bloque 3, segunda parte: solo registra el porcentaje configurado
    (reglas 1/2/3 de Hernán). No calcula ningún cumplimiento — ver nota de
    clase en el modelo."""

    objetivo_general_texto = serializers.CharField(
        source='objetivo_general.texto_objetivo', read_only=True
    )
    plan_anual_nombre = serializers.CharField(
        source='plan_anual.nombre', read_only=True
    )
    plan_anual_anio = serializers.IntegerField(
        source='plan_anual.anio', read_only=True
    )
    creado_por_username = serializers.CharField(
        source='creado_por.username', read_only=True
    )
    # Expuestos para que el frontend muestre "total distribuido" /
    # "pendiente" sin tener que traer y sumar él mismo el resto de filas
    # del mismo objetivo general (Fase 3). Se calculan INCLUYENDO esta
    # fila (a diferencia de resumen_ponderacion_anual(excluir_id=...), que
    # se usa en validate() para el chequeo de "no superar el 100%").
    total_asignado_objetivo_general = serializers.SerializerMethodField()
    pendiente_objetivo_general = serializers.SerializerMethodField()

    class Meta:
        model = PonderacionAnualObjetivoGeneral
        fields = [
            'id',
            'objetivo_general',
            'objetivo_general_texto',
            'plan_anual',
            'plan_anual_nombre',
            'plan_anual_anio',
            'porcentaje',
            'total_asignado_objetivo_general',
            'pendiente_objetivo_general',
            'creado_por',
            'creado_por_username',
            'fecha_creacion',
            'fecha_actualizacion',
        ]
        read_only_fields = ['id', 'creado_por', 'fecha_creacion', 'fecha_actualizacion']
        # Mismo motivo que en los demás serializers de este proyecto: se
        # desactiva el UniqueTogetherValidator automático de DRF (derivado
        # de la UniqueConstraint del modelo) para que el único mensaje de
        # duplicado sea el de validate(), en español natural.
        validators = []

    def get_total_asignado_objetivo_general(self, obj):
        resumen = resumen_ponderacion_anual(obj.objetivo_general, excluir_id=obj.pk)
        return resumen['total_asignado'] + obj.porcentaje

    def get_pendiente_objetivo_general(self, obj):
        resumen = resumen_ponderacion_anual(obj.objetivo_general, excluir_id=obj.pk)
        return resumen['pendiente'] - obj.porcentaje

    def validate(self, data):
        instance = self.instance
        objetivo_general = data.get('objetivo_general') or getattr(instance, 'objetivo_general', None)
        plan_anual = data.get('plan_anual') or getattr(instance, 'plan_anual', None)
        porcentaje = data.get('porcentaje', getattr(instance, 'porcentaje', None))

        if not objetivo_general:
            raise serializers.ValidationError({
                'objetivo_general': 'Seleccioná un objetivo general.'
            })

        if not plan_anual:
            raise serializers.ValidationError({
                'plan_anual': 'Seleccioná un plan anual.'
            })

        # Etapa 1 (integridad): una ponderación existente solo corrige su
        # porcentaje; trasladarla a otro objetivo/año es crear otra fila.
        if _cambia_relacion(data, instance, 'objetivo_general') or _cambia_relacion(
            data, instance, 'plan_anual'
        ):
            raise serializers.ValidationError(
                'Una ponderación existente no puede trasladarse a otro objetivo '
                'general ni a otro plan anual. Solo puede corregirse su porcentaje.'
            )

        if objetivo_general.plan_estrategico_id != plan_anual.plan_estrategico_id:
            raise serializers.ValidationError({
                'plan_anual': (
                    'El plan anual debe pertenecer al mismo Plan estratégico que '
                    'el objetivo general seleccionado.'
                )
            })

        if plan_anual_esta_bloqueado(plan_anual):
            raise serializers.ValidationError(
                'El Plan anual está Cerrado (o su Plan estratégico lo está) y no '
                'permite modificar sus ponderaciones.'
            )

        duplicados = PonderacionAnualObjetivoGeneral.objects.filter(
            objetivo_general=objetivo_general, plan_anual=plan_anual,
        )

        if instance is not None:
            duplicados = duplicados.exclude(pk=instance.pk)

        if duplicados.exists():
            raise serializers.ValidationError(
                'Ya existe una ponderación para este objetivo general en ese año. '
                'Editá la fila existente en lugar de crear una nueva.'
            )

        if porcentaje is None:
            raise serializers.ValidationError({
                'porcentaje': 'Ingresá el porcentaje de ponderación.'
            })

        resumen = resumen_ponderacion_anual(
            objetivo_general, excluir_id=instance.pk if instance else None,
        )

        if resumen['total_asignado'] + porcentaje > 100:
            raise serializers.ValidationError({
                'porcentaje': (
                    'La ponderación excede el 100% del objetivo general: ya hay '
                    f'{resumen["total_asignado"]}% asignado en otros años, máximo '
                    f'disponible {resumen["pendiente"]}%.'
                )
            })

        return data
