from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import ArchivoImportado, ConexionDW, ConsultaDW
from .serializers import (
    ArchivoImportadoSerializer,
    ConexionDWSerializer,
    ConsultaDWSerializer,
)


class ArchivoImportadoViewSet(viewsets.ModelViewSet):
    queryset = ArchivoImportado.objects.select_related(
        'importado_por',
    ).all()
    serializer_class = ArchivoImportadoSerializer
    permission_classes = [IsAuthenticated]


class ConexionDWViewSet(viewsets.ModelViewSet):
    queryset = ConexionDW.objects.all()
    serializer_class = ConexionDWSerializer
    permission_classes = [IsAuthenticated]


class ConsultaDWViewSet(viewsets.ModelViewSet):
    queryset = ConsultaDW.objects.select_related(
        'conexion_dw',
        'indicador',
    ).all()
    serializer_class = ConsultaDWSerializer
    permission_classes = [IsAuthenticated]

