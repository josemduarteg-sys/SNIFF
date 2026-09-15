from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import Area, Estrategia, Objetivo


class AreaSerializer(serializers.ModelSerializer):
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


class EstrategiaSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    creado_por_username = serializers.CharField(
        source='creado_por.username',
        read_only=True
    )

    class Meta:
        model = Estrategia
        fields = [
            'id',
            'area',
            'area_nombre',
            'creado_por',
            'creado_por_username',
            'nombre',
            'descripcion',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'creado_por']
        validators = [
            UniqueTogetherValidator(
                queryset=Estrategia.objects.all(),
                fields=['area', 'nombre'],
                message='Ya existe una estrategia con ese nombre dentro del área seleccionada.',
            )
        ]

    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio') or getattr(self.instance, 'fecha_inicio', None)
        fecha_fin = data.get('fecha_fin') or getattr(self.instance, 'fecha_fin', None)

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError({
                'fecha_fin': 'La fecha fin no puede ser menor que la fecha inicio.'
            })

        return data


class ObjetivoSerializer(serializers.ModelSerializer):
    estrategia_nombre = serializers.CharField(
        source='estrategia.nombre',
        read_only=True
    )
    creado_por_username = serializers.CharField(
        source='creado_por.username',
        read_only=True
    )

    class Meta:
        model = Objetivo
        fields = [
            'id',
            'estrategia',
            'estrategia_nombre',
            'creado_por',
            'creado_por_username',
            'nombre',
            'descripcion',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'creado_por']
        validators = [
            UniqueTogetherValidator(
                queryset=Objetivo.objects.all(),
                fields=['estrategia', 'nombre'],
                message='Ya existe un objetivo con ese nombre dentro de la estrategia seleccionada.',
            )
        ]

    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio') or getattr(self.instance, 'fecha_inicio', None)
        fecha_fin = data.get('fecha_fin') or getattr(self.instance, 'fecha_fin', None)

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError({
                'fecha_fin': 'La fecha fin no puede ser menor que la fecha inicio.'
            })

        return data

