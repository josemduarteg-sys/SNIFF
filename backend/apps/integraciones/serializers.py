from rest_framework import serializers

from .models import ArchivoImportado, ConexionDW, ConsultaDW


class ArchivoImportadoSerializer(serializers.ModelSerializer):
    importado_por_username = serializers.CharField(
        source='importado_por.username',
        read_only=True
    )

    class Meta:
        model = ArchivoImportado
        fields = [
            'id',
            'nombre_archivo',
            'tipo_archivo',
            'ruta_archivo',
            'fecha_importacion',
            'estado_importacion',
            'registros_procesados',
            'registros_con_error',
            'importado_por',
            'importado_por_username',
            'observacion',
        ]
        read_only_fields = ['id', 'fecha_importacion']


class ConexionDWSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConexionDW
        fields = [
            'id',
            'nombre',
            'descripcion',
            'servidor',
            'base_datos',
            'esquema',
            'estado',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion']


class ConsultaDWSerializer(serializers.ModelSerializer):
    conexion_dw_nombre = serializers.CharField(
        source='conexion_dw.nombre',
        read_only=True
    )
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )

    class Meta:
        model = ConsultaDW
        fields = [
            'id',
            'conexion_dw',
            'conexion_dw_nombre',
            'indicador',
            'indicador_nombre',
            'nombre',
            'descripcion',
            'consulta_referencia',
            'frecuencia_ejecucion',
            'estado',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion']

