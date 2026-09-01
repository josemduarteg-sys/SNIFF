from rest_framework import viewsets

from apps.usuarios.permissions import PermisoCatalogoSoloAdmin, PermisoPlaneacion
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
    permission_classes = [PermisoPlaneacion]

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)


class ObjetivoViewSet(viewsets.ModelViewSet):
    queryset = Objetivo.objects.select_related(
        'estrategia',
        'creado_por',
    ).all()
    serializer_class = ObjetivoSerializer
    permission_classes = [PermisoPlaneacion]

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

