from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Bitacora
from .serializers import BitacoraSerializer


class BitacoraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bitacora.objects.select_related(
        'usuario',
    ).all().order_by('-fecha_hora')
    serializer_class = BitacoraSerializer
    permission_classes = [IsAuthenticated]

    