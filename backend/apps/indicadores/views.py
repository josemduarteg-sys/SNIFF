import os

from django.db import transaction
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from apps.usuarios.permissions import (
    PermisoCatalogoSoloAdmin,
    PermisoIndicadorKPI,
    PermisoMedicion,
    PermisoPlaneacion,
)
from .models import (
    Frecuencia,
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
    IndicadorKPISerializer,
    MetaKPISerializer,
    ResponsableKPISerializer,
    EstadoCumplimientoSerializer,
    RangoKPISerializer,
    PeriodoMedicionSerializer,
    MedicionSerializer,
    AlertaSerializer,
)
from .services import (
    crear_rangos_provisionales,
    obtener_info_siguiente_periodo,
)


class FrecuenciaViewSet(viewsets.ModelViewSet):
    queryset = Frecuencia.objects.filter(estado=True).order_by('nombre')
    serializer_class = FrecuenciaSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]


class IndicadorKPIViewSet(viewsets.ModelViewSet):
    queryset = IndicadorKPI.objects.select_related(
        'objetivo_especifico',
        'objetivo_especifico__plan_anual',
        'objetivo_especifico__plan_anual__plan_estrategico',
        'frecuencia',
        'autorizado_por',
    ).all()
    serializer_class = IndicadorKPISerializer
    permission_classes = [PermisoIndicadorKPI]

    def perform_create(self, serializer):
        from apps.auditoria.services import notificar_usuarios_gestion, registrar_bitacora_seguro
        from rest_framework.exceptions import ValidationError

        # Transaccional: el KPI y sus tres RangoKPI provisionales se crean
        # juntos o no se crea ninguno de los dos (nunca queda una
        # configuración incompleta).
        try:
            with transaction.atomic():
                indicador = serializer.save(creado_por=self.request.user, estado='borrador')
                crear_rangos_provisionales(indicador)
        except ValueError as error:
            raise ValidationError({
                'detail': (
                    'No se pudo crear el KPI con sus criterios de cumplimiento '
                    f'iniciales: {error} No se guardó ningún cambio.'
                )
            })

        registrar_bitacora_seguro(
            usuario=self.request.user,
            accion='crear',
            modulo='Indicadores KPI',
            descripcion=(
                f'Creó el KPI {indicador.nombre} en el {indicador.plan_anual.nombre} '
                f'del Plan estratégico {indicador.plan_estrategico.titulo}.'
            ),
            request=self.request,
        )

        notificar_usuarios_gestion(
            tipo='kpi_creado',
            titulo='Nuevo KPI pendiente de autorización',
            mensaje=f'{self.request.user.username} registró el KPI "{indicador.nombre}".',
            enlace=f'/indicadores?resaltar={indicador.id}',
            excluir_usuario=self.request.user,
        )

    def perform_update(self, serializer):
        from apps.auditoria.services import registrar_bitacora_seguro

        indicador = serializer.save()

        registrar_bitacora_seguro(
            usuario=self.request.user,
            accion='actualizar',
            modulo='Indicadores KPI',
            descripcion=f'Actualizó el KPI {indicador.nombre}.',
            request=self.request,
        )

    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        from apps.auditoria.services import crear_notificacion, registrar_bitacora_seguro

        indicador = self.get_object()

        if indicador.esta_bloqueado():
            return Response(
                {'detail': 'El Plan anual o el Plan estratégico de este KPI están Cerrados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        registrar_bitacora_seguro(
            usuario=request.user,
            accion='actualizar',
            modulo='Indicadores KPI',
            descripcion=f'Autorizó el KPI {indicador.nombre}.',
            request=request,
        )

        if indicador.creado_por_id and indicador.creado_por_id != request.user.id:
            crear_notificacion(
                usuario_destino=indicador.creado_por,
                tipo='kpi_autorizado',
                titulo='KPI autorizado',
                mensaje=f'Tu KPI "{indicador.nombre}" fue autorizado.',
                enlace=f'/indicadores?resaltar={indicador.id}',
            )

        serializer = self.get_serializer(indicador)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        from apps.auditoria.services import crear_notificacion, registrar_bitacora_seguro

        indicador = self.get_object()

        if indicador.esta_bloqueado():
            return Response(
                {'detail': 'El Plan anual o el Plan estratégico de este KPI están Cerrados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        indicador.estado = 'anulado'
        indicador.save(update_fields=['estado'])

        registrar_bitacora_seguro(
            usuario=request.user,
            accion='eliminar',
            modulo='Indicadores KPI',
            descripcion=f'Anuló el KPI {indicador.nombre}.',
            request=request,
        )

        if indicador.creado_por_id and indicador.creado_por_id != request.user.id:
            crear_notificacion(
                usuario_destino=indicador.creado_por,
                tipo='kpi_anulado',
                titulo='KPI anulado',
                mensaje=f'Tu KPI "{indicador.nombre}" fue anulado.',
                enlace=f'/indicadores?resaltar={indicador.id}',
            )

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
        'indicador__objetivo_especifico',
        'indicador__objetivo_especifico__plan_anual',
        'indicador__objetivo_especifico__plan_anual__plan_estrategico',
        'indicador__frecuencia',
        'meta',
        'estado_cumplimiento',
        'periodo',
        'registrado_por',
        'archivo_importado',
        'consulta_dw',
    ).all()
    serializer_class = MedicionSerializer
    permission_classes = [PermisoMedicion]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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
            .select_related(
                'frecuencia',
                'objetivo_especifico',
                'objetivo_especifico__plan_anual',
                'objetivo_especifico__plan_anual__plan_estrategico',
            )
            .filter(id=indicador_id)
            .first()
        )

        if not indicador:
            return Response(
                {'detail': 'El KPI seleccionado no existe.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        info = obtener_info_siguiente_periodo(indicador)

        return Response({
            'disponible': info['disponible'],
            'periodo_nombre': info['periodo_nombre'],
            'tipo_periodo': info['tipo_periodo'],
            'fecha_inicio_periodo': info['fecha_inicio_periodo'],
            'fecha_cierre': info['fecha_cierre'],
            'fecha_limite_registro': info['fecha_limite_registro'],
            'motivo': info['motivo'],
        })

    @action(detail=True, methods=['get'], url_path='evidencia')
    def evidencia(self, request, pk=None):

        medicion = self.get_object()

        if not medicion.evidencia:
            raise Http404('Esta medición no tiene evidencia adjunta.')

        return FileResponse(
            medicion.evidencia.open('rb'),
            as_attachment=False,
            filename=os.path.basename(medicion.evidencia.name),
        )

    @action(detail=True, methods=['get'], url_path='evidencia/descargar')
    def evidencia_descargar(self, request, pk=None):
        # Mismo archivo protegido que `evidencia`, pero forzando la
        # descarga (Content-Disposition: attachment) en vez de abrirlo
        # inline. Mismos permisos: get_object() aplica el mismo queryset y
        # permission_classes del ViewSet.
        medicion = self.get_object()

        if not medicion.evidencia:
            raise Http404('Esta medición no tiene evidencia adjunta.')

        return FileResponse(
            medicion.evidencia.open('rb'),
            as_attachment=True,
            filename=os.path.basename(medicion.evidencia.name),
        )


class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.select_related(
        'indicador',
        'medicion',
        'revisado_por',
    ).all()
    serializer_class = AlertaSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]

    @action(detail=True, methods=['post'], url_path='marcar-revisada')
    def marcar_revisada(self, request, pk=None):
        from .services import marcar_alerta_revisada

        alerta = self.get_object()
        marcar_alerta_revisada(alerta, usuario=request.user)

        serializer = self.get_serializer(alerta)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='marcar-todas-revisadas')
    def marcar_todas_revisadas(self, request):
        from .services import marcar_todas_alertas_revisadas

        actualizadas = marcar_todas_alertas_revisadas(usuario=request.user)

        return Response({
            'detail': f'{actualizadas} alerta(s) marcada(s) como revisada(s).'
        })

