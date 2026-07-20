from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Rol, Usuario
from .serializers import (
    RolSerializer,
    UsuarioSerializer,
    UsuarioCrearSerializer,
)


class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [IsAuthenticated]


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.select_related('rol').all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UsuarioCrearSerializer
        return UsuarioSerializer
    
