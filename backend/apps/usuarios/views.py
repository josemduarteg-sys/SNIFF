from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Rol, Usuario
from .permissions import EsAdministradorSistema
from .serializers import (
    CambiarPasswordSerializer,
    RolSerializer,
    UsuarioActualSerializer,
    UsuarioSerializer,
)


class RolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Rol.objects.filter(estado=True).order_by('nombre')
    serializer_class = RolSerializer
    permission_classes = [IsAuthenticated]


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.select_related('rol').order_by('id')
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated, EsAdministradorSistema]

    def destroy(self, request, *args, **kwargs):
        usuario = self.get_object()

        if usuario.id == request.user.id:
            return Response(
                {'detail': 'No podés inactivar tu propio usuario desde esta opción.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario.estado = False
        usuario.is_active = False
        usuario.save(update_fields=['estado', 'is_active'])

        return Response(
            {'detail': 'Usuario inactivado correctamente.'},
            status=status.HTTP_200_OK,
        )


class UsuarioActualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UsuarioActualSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UsuarioActualSerializer(
            request.user,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class CambiarPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CambiarPasswordSerializer(
            data=request.data,
            context={'request': request},
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'detail': 'Contraseña actualizada correctamente.'},
            status=status.HTTP_200_OK,
        )