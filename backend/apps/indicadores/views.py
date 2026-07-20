from rest_framework import viewsets
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
    queryset = Frecuencia.objects.all()
    serializer_class = FrecuenciaSerializer
    permission_classes = [IsAuthenticated]


class TipoCalculoViewSet(viewsets.ModelViewSet):
    queryset = TipoCalculo.objects.all()
    serializer_class = TipoCalculoSerializer
    permission_classes = [IsAuthenticated]


class FuenteDatoViewSet(viewsets.ModelViewSet):
    queryset = FuenteDato.objects.all()
    serializer_class = FuenteDatoSerializer
    permission_classes = [IsAuthenticated]


class IndicadorKPIViewSet(viewsets.ModelViewSet):
    queryset = IndicadorKPI.objects.select_related(
        'objetivo',
        'frecuencia',
        'tipo_calculo',
        'fuente_dato',
    ).all()
    serializer_class = IndicadorKPISerializer
    permission_classes = [IsAuthenticated]


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
    queryset = EstadoCumplimiento.objects.all()
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


class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.select_related(
        'indicador',
        'medicion',
        'revisado_por',
    ).all()
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated]

