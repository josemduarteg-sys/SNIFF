from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.usuarios.permissions import (
    PermisoCatalogoSoloAdmin,
    PermisoEstrategiaObjetivo,
    es_administrador,
)
from .models import Area, Estrategia, Objetivo
from .serializers import (
    AreaSerializer,
    EstrategiaSerializer,
    ObjetivoSerializer,
)


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]


class EstrategiaViewSet(viewsets.ModelViewSet):
    queryset = Estrategia.objects.select_related(
        'area',
        'creado_por',
    ).all()
    serializer_class = EstrategiaSerializer
    permission_classes = [PermisoEstrategiaObjetivo]

    def perform_create(self, serializer):
        from apps.auditoria.services import notificar_usuarios_gestion

        estado_inicial = 'activa' if es_administrador(self.request.user) else 'en_revision'
        estrategia = serializer.save(creado_por=self.request.user, estado=estado_inicial)

        notificar_usuarios_gestion(
            tipo='estrategia_creada',
            titulo='Nueva estrategia registrada',
            mensaje=f'{self.request.user.username} registró la estrategia "{estrategia.nombre}".',
            enlace=f'/estrategias?resaltar={estrategia.id}',
            excluir_usuario=self.request.user,
        )

    def perform_update(self, serializer):
        if not es_administrador(self.request.user):
            serializer.validated_data.pop('estado', None)

        serializer.save()

    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        estrategia = self.get_object()
        estrategia.estado = 'activa'
        estrategia.save(update_fields=['estado'])

        serializer = self.get_serializer(estrategia)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        estrategia = self.get_object()
        estrategia.estado = 'finalizada'
        estrategia.save(update_fields=['estado'])

        serializer = self.get_serializer(estrategia)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def inactivar(self, request, pk=None):
        estrategia = self.get_object()
        estrategia.estado = 'inactiva'
        estrategia.save(update_fields=['estado'])

        serializer = self.get_serializer(estrategia)
        return Response(serializer.data)


class ObjetivoViewSet(viewsets.ModelViewSet):
    queryset = Objetivo.objects.select_related(
        'estrategia',
        'creado_por',
    ).all()
    serializer_class = ObjetivoSerializer
    permission_classes = [PermisoEstrategiaObjetivo]

    def perform_create(self, serializer):
        from apps.auditoria.services import notificar_usuarios_gestion

        estado_inicial = 'activo' if es_administrador(self.request.user) else 'en_revision'
        objetivo = serializer.save(creado_por=self.request.user, estado=estado_inicial)

        notificar_usuarios_gestion(
            tipo='objetivo_creado',
            titulo='Nuevo objetivo registrado',
            mensaje=f'{self.request.user.username} registró el objetivo "{objetivo.nombre}".',
            enlace=f'/objetivos?resaltar={objetivo.id}',
            excluir_usuario=self.request.user,
        )

    def perform_update(self, serializer):
        if not es_administrador(self.request.user):
            serializer.validated_data.pop('estado', None)

        serializer.save()

    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        objetivo = self.get_object()
        objetivo.estado = 'activo'
        objetivo.save(update_fields=['estado'])

        serializer = self.get_serializer(objetivo)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        objetivo = self.get_object()
        objetivo.estado = 'finalizado'
        objetivo.save(update_fields=['estado'])

        serializer = self.get_serializer(objetivo)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def inactivar(self, request, pk=None):
        objetivo = self.get_object()
        objetivo.estado = 'inactivo'
        objetivo.save(update_fields=['estado'])

        serializer = self.get_serializer(objetivo)
        return Response(serializer.data)
