from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.usuarios.permissions import EsAdministradorSistema, es_administrador

from .models import Bitacora, Notificacion
from .serializers import BitacoraSerializer, NotificacionSerializer


class BitacoraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bitacora.objects.select_related(
        'usuario',
    ).all().order_by('-fecha_hora')
    serializer_class = BitacoraSerializer
    permission_classes = [EsAdministradorSistema]

    def get_queryset(self):
        # Etapa 4 (M7): ?origen=sistema | usuario.
        queryset = super().get_queryset()
        origen = self.request.query_params.get('origen')

        if origen == Bitacora.ORIGEN_SISTEMA:
            return queryset.filter(usuario__isnull=True)

        if origen == Bitacora.ORIGEN_USUARIO:
            return queryset.filter(usuario__isnull=False)

        return queryset


class NotificacionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Notificacion.objects.select_related('usuario_destino').all()
        usuario = self.request.user

        if es_administrador(usuario) and self.request.query_params.get('todas') == '1':
            return queryset

        return queryset.filter(usuario_destino=usuario)

    @action(detail=True, methods=['patch'], url_path='marcar-leida')
    def marcar_leida(self, request, pk=None):
        notificacion = self.get_object()
        notificacion.leida = True
        notificacion.save(update_fields=['leida'])

        serializer = self.get_serializer(notificacion)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='marcar-todas-leidas')
    def marcar_todas_leidas(self, request):
        actualizadas = Notificacion.objects.filter(
            usuario_destino=request.user,
            leida=False,
        ).update(leida=True)

        return Response({
            'detail': f'{actualizadas} notificación(es) marcada(s) como leída(s).'
        })

    