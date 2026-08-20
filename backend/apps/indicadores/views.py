from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response    
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from .models import (
    Frecuencia,
    TipoCalculo,
    FuenteDato,
    IndicadorKPI,
    MetaKPI,
    ResponsableKPI,
    EstadoCumplimiento,
    RangoKPI,
    PeriodoMedicion,
    Medicion,
    Alerta,
)
from .serializers import (
    FrecuenciaSerializer,
    TipoCalculoSerializer,
    FuenteDatoSerializer,
    IndicadorKPISerializer,
    MetaKPISerializer,
    ResponsableKPISerializer,
    EstadoCumplimientoSerializer,
    RangoKPISerializer,
    PeriodoMedicionSerializer,
    MedicionSerializer,
    AlertaSerializer,
)


class FrecuenciaViewSet(viewsets.ModelViewSet):
    queryset = Frecuencia.objects.filter(estado=True).order_by('nombre')
    serializer_class = FrecuenciaSerializer
    permission_classes = [IsAuthenticated]


class TipoCalculoViewSet(viewsets.ModelViewSet):
    queryset = TipoCalculo.objects.filter(estado=True).order_by('nombre')
    serializer_class = TipoCalculoSerializer
    permission_classes = [IsAuthenticated]


class FuenteDatoViewSet(viewsets.ModelViewSet):
    queryset = FuenteDato.objects.filter(estado=True).order_by('nombre')
    serializer_class = FuenteDatoSerializer
    permission_classes = [IsAuthenticated]


class IndicadorKPIViewSet(viewsets.ModelViewSet):
    queryset = IndicadorKPI.objects.select_related(
        'objetivo',
        'frecuencia',
        'tipo_calculo',
        'fuente_dato',
        'autorizado_por',
    ).all()
    serializer_class = IndicadorKPISerializer

    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        indicador = self.get_object()

        if indicador.estado == 'autorizado':
            return Response(
                {'detail': 'El KPI ya se encuentra autorizado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not indicador.valor_meta:
            return Response(
                {'detail': 'No se puede autorizar un KPI sin meta configurada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not indicador.fecha_inicio or not indicador.fecha_fin:
            return Response(
                {'detail': 'No se puede autorizar un KPI sin fechas de vigencia.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        indicador.estado = 'autorizado'
        indicador.fecha_autorizacion = timezone.now()
        indicador.autorizado_por = request.user
        indicador.save(
            update_fields=[
                'estado',
                'fecha_autorizacion',
                'autorizado_por',
            ]
        )

        serializer = self.get_serializer(indicador)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        indicador = self.get_object()

        indicador.estado = 'anulado'
        indicador.save(update_fields=['estado'])

        serializer = self.get_serializer(indicador)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MetaKPIViewSet(viewsets.ModelViewSet):
    queryset = MetaKPI.objects.select_related(
        'indicador',
    ).all()
    serializer_class = MetaKPISerializer
    permission_classes = [IsAuthenticated]


class ResponsableKPIViewSet(viewsets.ModelViewSet):
    queryset = ResponsableKPI.objects.select_related(
        'indicador',
        'usuario',
    ).all()
    serializer_class = ResponsableKPISerializer
    permission_classes = [IsAuthenticated]


class EstadoCumplimientoViewSet(viewsets.ModelViewSet):
    queryset = EstadoCumplimiento.objects.filter(estado=True).order_by('nombre')
    serializer_class = EstadoCumplimientoSerializer
    permission_classes = [IsAuthenticated]


class RangoKPIViewSet(viewsets.ModelViewSet):
    queryset = RangoKPI.objects.select_related(
        'indicador',
        'estado_cumplimiento',
    ).all()
    serializer_class = RangoKPISerializer
    permission_classes = [IsAuthenticated]


class PeriodoMedicionViewSet(viewsets.ModelViewSet):
    queryset = PeriodoMedicion.objects.all()
    serializer_class = PeriodoMedicionSerializer
    permission_classes = [IsAuthenticated]


class MedicionViewSet(viewsets.ModelViewSet):
    queryset = Medicion.objects.select_related(
        'indicador',
        'meta',
        'estado_cumplimiento',
        'periodo',
        'registrado_por',
        'archivo_importado',
        'consulta_dw',
    ).all()
    serializer_class = MedicionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)


class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.select_related(
        'indicador',
        'medicion',
        'revisado_por',
    ).all()
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated]

