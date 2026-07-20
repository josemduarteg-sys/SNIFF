from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Area, Estrategia, Objetivo
from .serializers import (
    AreaSerializer,
    EstrategiaSerializer,
    ObjetivoSerializer,
)


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated]


class EstrategiaViewSet(viewsets.ModelViewSet):
    queryset = Estrategia.objects.select_related(
        'area',
        'creado_por',
    ).all()
    serializer_class = EstrategiaSerializer
    permission_classes = [IsAuthenticated]


class ObjetivoViewSet(viewsets.ModelViewSet):
    queryset = Objetivo.objects.select_related(
        'estrategia',
        'creado_por',
    ).all()
    serializer_class = ObjetivoSerializer
    permission_classes = [IsAuthenticated]

