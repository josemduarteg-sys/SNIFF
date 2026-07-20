from rest_framework import serializers

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
        read_only_fields = ['id', 'fecha_creacion']


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
        read_only_fields = ['id', 'fecha_creacion']

