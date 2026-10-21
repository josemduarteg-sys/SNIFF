from rest_framework import serializers

from .models import Bitacora, Notificacion


class BitacoraSerializer(serializers.ModelSerializer):
    # Etapa 4 (M7): en eventos del sistema usuario es NULL; sin default, DRF
    # omitiría el campo en lugar de devolverlo vacío.
    usuario_username = serializers.CharField(
        source='usuario.username',
        read_only=True,
        default=None,
    )
    origen = serializers.CharField(read_only=True)
    autor = serializers.CharField(read_only=True)

    class Meta:
        model = Bitacora
        fields = [
            'id',
            'usuario',
            'usuario_username',
            'origen',
            'autor',
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

