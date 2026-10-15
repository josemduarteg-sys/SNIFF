from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Area, ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from .services import (
    objetivo_especifico_esta_bloqueado,
    plan_anual_esta_bloqueado,
    plan_estrategico_esta_cerrado,
)


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

    class Meta:
        model = ObjetivoGeneral
        fields = [
            'id',
            'plan_estrategico',
            'plan_estrategico_titulo',
            'plan_estrategico_estado',
            'texto_objetivo',
            'creado_por',
            'creado_por_username',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'creado_por']

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

    def get_nombre(self, obj):
        return obj.nombre

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

        # Coherencia fecha <-> año: solo se exige en registros nuevos (en
        # edición, ni anio ni las fechas pueden tocarse por separado salvo
        # que el plan siga en Borrador, en cuyo caso ambos se revalidan
        # igual con los valores finales ya combinados arriba).
        if instance is None or 'anio' in data or 'fecha_inicio' in data or 'fecha_fin' in data:
            if fecha_inicio and fecha_inicio.year != anio:
                raise serializers.ValidationError({
                    'fecha_inicio': 'La fecha de inicio debe pertenecer al año seleccionado.'
                })

            if fecha_fin and fecha_fin.year != anio:
                raise serializers.ValidationError({
                    'fecha_fin': 'La fecha de finalización debe pertenecer al año seleccionado.'
                })

        return data


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
            'creado_por',
            'creado_por_username',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'creado_por']

    def get_plan_anual_nombre(self, obj):
        return obj.plan_anual.nombre if obj.plan_anual_id else None

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

        return data
