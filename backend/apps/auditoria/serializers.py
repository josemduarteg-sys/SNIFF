from rest_framework import serializers

from .models import Bitacora, Notificacion


class BitacoraSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(
        source='usuario.username',
        read_only=True
    )

    class Meta:
        model = Bitacora
        fields = [
            'id',
            'usuario',
            'usuario_username',
            'accion',
            'modulo',
            'descripcion',
            'fecha_hora',
            'ip_usuario',
        ]
        read_only_fields = [
            'id',
            'fecha_hora',
        ]


class NotificacionSerializer(serializers.ModelSerializer):
    usuario_destino_username = serializers.CharField(
        source='usuario_destino.username',
        read_only=True
    )

    class Meta:
        model = Notificacion
        fields = [
            'id',
            'usuario_destino',
            'usuario_destino_username',
            'tipo',
            'titulo',
            'mensaje',
            'leida',
            'enlace',
            'fecha_creacion',
        ]
        read_only_fields = [
            'id',
            'usuario_destino',
            'fecha_creacion',
        ]

