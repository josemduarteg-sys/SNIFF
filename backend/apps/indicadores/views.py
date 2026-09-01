from datetime import date

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from apps.usuarios.permissions import (
    PermisoCatalogoSoloAdmin,
    PermisoIndicadorKPI,
    PermisoMedicion,
    PermisoPlaneacion,
)
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
from .services import formatear_periodo, obtener_siguiente_periodo_esperado


class FrecuenciaViewSet(viewsets.ModelViewSet):
    queryset = Frecuencia.objects.filter(estado=True).order_by('nombre')
    serializer_class = FrecuenciaSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]


class TipoCalculoViewSet(viewsets.ModelViewSet):
    queryset = TipoCalculo.objects.filter(estado=True).order_by('nombre')
    serializer_class = TipoCalculoSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]


class FuenteDatoViewSet(viewsets.ModelViewSet):
    queryset = FuenteDato.objects.filter(estado=True).order_by('nombre')
    serializer_class = FuenteDatoSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]


class IndicadorKPIViewSet(viewsets.ModelViewSet):
    queryset = IndicadorKPI.objects.select_related(
        'objetivo',
        'frecuencia',
        'tipo_calculo',
        'fuente_dato',
        'autorizado_por',
    ).all()
    serializer_class = IndicadorKPISerializer
    permission_classes = [PermisoIndicadorKPI]

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
    permission_classes = [PermisoCatalogoSoloAdmin]


class ResponsableKPIViewSet(viewsets.ModelViewSet):
    queryset = ResponsableKPI.objects.select_related(
        'indicador',
        'usuario',
    ).all()
    serializer_class = ResponsableKPISerializer
    permission_classes = [PermisoPlaneacion]


class EstadoCumplimientoViewSet(viewsets.ModelViewSet):
    queryset = EstadoCumplimiento.objects.filter(estado=True).order_by('nombre')
    serializer_class = EstadoCumplimientoSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]


class RangoKPIViewSet(viewsets.ModelViewSet):
    queryset = RangoKPI.objects.select_related(
        'indicador',
        'estado_cumplimiento',
    ).all()
    serializer_class = RangoKPISerializer
    permission_classes = [PermisoCatalogoSoloAdmin]


class PeriodoMedicionViewSet(viewsets.ModelViewSet):
    queryset = PeriodoMedicion.objects.all()
    serializer_class = PeriodoMedicionSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]


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
    permission_classes = [PermisoMedicion]

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)

    @action(detail=False, methods=['get'], url_path='siguiente-periodo')
    def siguiente_periodo(self, request):
        indicador_id = request.query_params.get('indicador')

        if not indicador_id:
            return Response(
                {'detail': 'Debe enviar el KPI para calcular el siguiente periodo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        indicador = (
            IndicadorKPI.objects
            .select_related('frecuencia')
            .filter(id=indicador_id)
            .first()
        )

        if not indicador:
            return Response(
                {'detail': 'El KPI seleccionado no existe.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if indicador.estado != 'autorizado':
            return Response(
                {'detail': 'Solo se pueden registrar mediciones para KPI activos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not indicador.valor_meta:
            return Response(
                {'detail': 'El KPI seleccionado no tiene una meta configurada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not indicador.fecha_inicio or not indicador.fecha_fin:
            return Response(
                {'detail': 'El KPI seleccionado no tiene vigencia configurada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        periodo_esperado = obtener_siguiente_periodo_esperado(indicador)

        fecha_fin_kpi = date(
            indicador.fecha_fin.year,
            indicador.fecha_fin.month,
            1,
        )

        if periodo_esperado > fecha_fin_kpi:
            return Response({
                'disponible': False,
                'mes_medicion': None,
                'periodo_nombre': None,
                'mensaje': 'Este KPI ya tiene registradas todas las mediciones dentro de su vigencia.',
            })

        return Response({
            'disponible': True,
            'mes_medicion': periodo_esperado.strftime('%Y-%m'),
            'periodo_nombre': formatear_periodo(periodo_esperado),
            'mensaje': f'El siguiente periodo a registrar es {formatear_periodo(periodo_esperado)}.',
        })


class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.select_related(
        'indicador',
        'medicion',
        'revisado_por',
    ).all()
    serializer_class = AlertaSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]

