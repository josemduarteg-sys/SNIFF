from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Area, PlanEstrategico, ObjetivoGeneral
from .services import plan_estrategico_esta_cerrado


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
