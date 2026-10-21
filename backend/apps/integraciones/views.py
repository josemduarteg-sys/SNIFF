from rest_framework import viewsets

from apps.usuarios.permissions import PermisoIntegracionesSoloLectura

from .models import ArchivoImportado, ConexionDW, ConsultaDW
from .serializers import (
    ArchivoImportadoSerializer,
    ConexionDWSerializer,
    ConsultaDWSerializer,
)

# Etapa 2 (auditoría A4): módulo fuera del alcance vigente. Solo lectura y
# solo para Administrador del sistema (ver PermisoIntegracionesSoloLectura);
# no hay creación, edición ni borrado por API, ni conexiones externas.


class ArchivoImportadoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ArchivoImportado.objects.select_related(
        'importado_por',
    ).all()
    serializer_class = ArchivoImportadoSerializer
    permission_classes = [PermisoIntegracionesSoloLectura]


class ConexionDWViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ConexionDW.objects.all()
    serializer_class = ConexionDWSerializer
    permission_classes = [PermisoIntegracionesSoloLectura]


class ConsultaDWViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ConsultaDW.objects.select_related(
        'conexion_dw',
        'indicador',
    ).all()
    serializer_class = ConsultaDWSerializer
    permission_classes = [PermisoIntegracionesSoloLectura]
