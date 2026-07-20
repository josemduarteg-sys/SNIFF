from rest_framework import serializers

from .models import (
    Frecuencia,
    TipoCalculo,
    FuenteDato,
    IndicadorKPI,
    MetaKPI,
    ResponsableKPI,
    EstadoCumplimiento,
    RangoKPI,
    PeriodoMedicion,
    Medicion,
    Alerta,
)


class FrecuenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frecuencia
        fields = [
            'id',
            'nombre',
            'descripcion',
            'estado',
        ]
        read_only_fields = ['id']


class TipoCalculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCalculo
        fields = [
            'id',
            'nombre',
            'descripcion',
            'estado',
        ]
        read_only_fields = ['id']


class FuenteDatoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuenteDato
        fields = [
            'id',
            'nombre',
            'descripcion',
            'estado',
        ]
        read_only_fields = ['id']


class IndicadorKPISerializer(serializers.ModelSerializer):
    objetivo_nombre = serializers.CharField(
        source='objetivo.nombre',
        read_only=True
    )
    frecuencia_nombre = serializers.CharField(
        source='frecuencia.nombre',
        read_only=True
    )
    tipo_calculo_nombre = serializers.CharField(
        source='tipo_calculo.nombre',
        read_only=True
    )
    fuente_dato_nombre = serializers.CharField(
        source='fuente_dato.nombre',
        read_only=True
    )

    class Meta:
        model = IndicadorKPI
        fields = [
            'id',
            'objetivo',
            'objetivo_nombre',
            'frecuencia',
            'frecuencia_nombre',
            'tipo_calculo',
            'tipo_calculo_nombre',
            'fuente_dato',
            'fuente_dato_nombre',
            'nombre',
            'descripcion',
            'unidad_medida',
            'estado',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion']


class MetaKPISerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )

    class Meta:
        model = MetaKPI
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'valor_meta',
            'fecha_inicio',
            'fecha_fin',
            'estado',
        ]
        read_only_fields = ['id']


class ResponsableKPISerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )
    usuario_username = serializers.CharField(
        source='usuario.username',
        read_only=True
    )

    class Meta:
        model = ResponsableKPI
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'usuario',
            'usuario_username',
            'fecha_asignacion',
            'estado',
        ]
        read_only_fields = ['id', 'fecha_asignacion']


class EstadoCumplimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoCumplimiento
        fields = [
            'id',
            'nombre',
            'descripcion',
            'color',
            'estado',
        ]
        read_only_fields = ['id']


class RangoKPISerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )
    estado_cumplimiento_nombre = serializers.CharField(
        source='estado_cumplimiento.nombre',
        read_only=True
    )

    class Meta:
        model = RangoKPI
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'estado_cumplimiento',
            'estado_cumplimiento_nombre',
            'valor_minimo',
            'valor_maximo',
            'estado',
        ]
        read_only_fields = ['id']


class PeriodoMedicionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoMedicion
        fields = [
            'id',
            'tipo_periodo',
            'fecha_inicio',
            'fecha_fin',
            'anio',
            'mes',
            'semana',
            'dia',
            'descripcion',
        ]
        read_only_fields = ['id']


class MedicionSerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )
    estado_cumplimiento = serializers.PrimaryKeyRelatedField(read_only=True)
    estado_cumplimiento_nombre = serializers.CharField(
        source='estado_cumplimiento.nombre',
        read_only=True
    )
    registrado_por_username = serializers.CharField(
        source='registrado_por.username',
        read_only=True
    )
    porcentaje_cumplimiento = serializers.SerializerMethodField()

    class Meta:
        model = Medicion
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'meta',
            'estado_cumplimiento',
            'estado_cumplimiento_nombre',
            'periodo',
            'registrado_por',
            'registrado_por_username',
            'archivo_importado',
            'consulta_dw',
            'fecha_medicion',
            'valor_resultado',
            'porcentaje_cumplimiento',
            'observacion',
            'fecha_registro',
        ]
        read_only_fields = [
            'id',
            'estado_cumplimiento',
            'fecha_registro',
            'porcentaje_cumplimiento',
        ]

    def get_porcentaje_cumplimiento(self, obj):
        return round(obj.calcular_cumplimiento(), 2)

    def validate(self, attrs):
        indicador = attrs.get('indicador') or getattr(self.instance, 'indicador', None)
        meta = attrs.get('meta') or getattr(self.instance, 'meta', None)

        if indicador and meta and meta.indicador_id != indicador.id:
            raise serializers.ValidationError(
                'La meta seleccionada no pertenece al indicador indicado.'
            )

        return attrs

    def create(self, validated_data):
        from .services import obtener_estado_para_medicion

        indicador = validated_data.get('indicador')
        meta = validated_data.get('meta')
        valor_resultado = validated_data.get('valor_resultado')

        estado = obtener_estado_para_medicion(
            indicador=indicador,
            meta=meta,
            valor_resultado=valor_resultado,
        )

        if estado is None:
            raise serializers.ValidationError(
                'No se encontró un estado de cumplimiento válido para esta medición.'
            )

        validated_data['estado_cumplimiento'] = estado

        return super().create(validated_data)

    def update(self, instance, validated_data):
        from .services import obtener_estado_para_medicion

        indicador = validated_data.get('indicador', instance.indicador)
        meta = validated_data.get('meta', instance.meta)
        valor_resultado = validated_data.get(
            'valor_resultado',
            instance.valor_resultado
        )

        estado = obtener_estado_para_medicion(
            indicador=indicador,
            meta=meta,
            valor_resultado=valor_resultado,
        )

        if estado is None:
            raise serializers.ValidationError(
                'No se encontró un estado de cumplimiento válido para esta medición.'
            )

        validated_data['estado_cumplimiento'] = estado

        return super().update(instance, validated_data)


class AlertaSerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )
    revisado_por_username = serializers.CharField(
        source='revisado_por.username',
        read_only=True
    )

    class Meta:
        model = Alerta
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'medicion',
            'tipo_alerta',
            'mensaje',
            'estado_alerta',
            'fecha_generacion',
            'fecha_revision',
            'revisado_por',
            'revisado_por_username',
        ]
        read_only_fields = ['id', 'fecha_generacion']

