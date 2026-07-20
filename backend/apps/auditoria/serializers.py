from rest_framework import serializers

from .models import Bitacora


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

