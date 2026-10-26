import os

from django.db import transaction
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

# Etapa 1 (auditoría M3): sin DELETE físico en este módulo. Mediciones,
# alertas y rangos son historial (borrarlos cambia resultados, promedios o
# deja huecos de periodo que el cálculo secuencial no vuelve a pedir); los
# catálogos con campo `estado` se desactivan por PATCH. Un DELETE responde
# 405 en lugar de borrar o fallar con 500 por las FK PROTECT.
from apps.auditoria.mixins import BitacoraCatalogoMixin
from apps.estrategia.views import METODOS_SIN_BORRADO
from apps.usuarios.permissions import (
    PermisoCatalogoSoloAdmin,
    PermisoIndicadorKPI,
    PermisoMedicion,
    PermisoPlaneacion,
    PermisoSolicitudAmpliacion,
)
from .models import (
    SolicitudAmpliacionPlazo,
    ConfiguracionMediciones,
    Frecuencia,
    IndicadorKPI,
    MetaKPI,
    ResponsableKPI,
    EstadoCumplimiento,
    RangoKPI,
    PeriodoMedicion,
    Medicion,
    Alerta,
    EvidenciaMedicion,
)
from .serializers import (
    ConfiguracionMedicionesSerializer,
    FrecuenciaSerializer,
    IndicadorKPISerializer,
    MetaKPISerializer,
    ResponsableKPISerializer,
    EstadoCumplimientoSerializer,
    RangoKPISerializer,
    PeriodoMedicionSerializer,
    MedicionSerializer,
    AgregarEvidenciasSerializer,
    EvidenciaMedicionSerializer,
    AlertaSerializer,
    SolicitudAmpliacionPlazoSerializer,
)
from .services import (
    MODULO_AMPLIACIONES,
    actualizar_alertas_por_ampliacion,
    adjuntar_evidencias,
    crear_rangos_provisionales,
    dejar_sin_efecto_solicitudes_pendientes,
    describir_solicitud_ampliacion,
    enlace_solicitud_ampliacion,
    evaluar_solicitud_ampliacion,
    motivo_no_admite_evidencias,
    notificar_sin_duplicar,
    obtener_info_siguiente_periodo,
    validar_rangos_para_autorizar,
)


class FrecuenciaViewSet(BitacoraCatalogoMixin, viewsets.ModelViewSet):
    queryset = Frecuencia.objects.filter(estado=True).order_by('nombre')
    serializer_class = FrecuenciaSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]
    http_method_names = METODOS_SIN_BORRADO
    modulo_bitacora = 'Frecuencias'

    def describir_para_bitacora(self, frecuencia):
        return f'la frecuencia {frecuencia.nombre}'


class ConfiguracionMedicionesView(APIView):
    """Bloque 4: GET/PATCH del plazo de registro singleton. Mismo
    permiso que el resto de catálogos de este módulo (consulta libre,
    escritura exclusiva de Administrador de planificación) — ningún
    permiso nuevo."""

    permission_classes = [PermisoCatalogoSoloAdmin]

    def get(self, request):
        configuracion = ConfiguracionMediciones.obtener()
        serializer = ConfiguracionMedicionesSerializer(configuracion)
        return Response(serializer.data)

    def patch(self, request):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        configuracion = ConfiguracionMediciones.obtener()
        plazo_anterior = configuracion.dias_plazo_registro
        serializer = ConfiguracionMedicionesSerializer(
            configuracion, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        configuracion = serializer.save()

        # Etapa 4 (M7): el plazo afecta las fechas límite de todos los KPI.
        if configuracion.dias_plazo_registro != plazo_anterior:
            registrar_bitacora_obligatoria(
                usuario=request.user,
                accion='actualizar',
                modulo='Configuración de mediciones',
                descripcion=(
                    f'Cambió el plazo de registro de mediciones de {plazo_anterior} '
                    f'a {configuracion.dias_plazo_registro} día(s) calendario.'
                ),
                request=request,
            )

        return Response(serializer.data)


class IndicadorKPIViewSet(viewsets.ModelViewSet):
    queryset = IndicadorKPI.objects.select_related(
        'objetivo_especifico',
        'objetivo_especifico__plan_anual',
        'objetivo_especifico__plan_anual__plan_estrategico',
        'objetivo_especifico__objetivo_general',
        'frecuencia',
        'autorizado_por',
        'creado_por',
    ).all()
    serializer_class = IndicadorKPISerializer
    permission_classes = [PermisoIndicadorKPI]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action not in ('list', 'retrieve'):
            return queryset

        # Etapa 6 (M8): datos que el serializer pedía KPI por KPI (promedio,
        # conteos, rangos, siguiente periodo, ampliaciones, responsables) se
        # cargan en pocas consultas para todo el listado. Solo en lectura:
        # las acciones que modifican siguen consultando en el momento.
        from django.db.models import Count, IntegerField, OuterRef, Prefetch, Subquery
        from apps.usuarios.permissions import ROL_EJECUTOR_OPERATIVO

        responsables = ResponsableKPI.objects.filter(
            indicador=OuterRef('pk'),
            estado=True,
            usuario__is_active=True,
            usuario__estado=True,
            usuario__rol__nombre__iexact=ROL_EJECUTOR_OPERATIVO,
        ).order_by().values('indicador').annotate(total=Count('usuario', distinct=True)).values('total')

        return queryset.annotate(
            cantidad_responsables_vigentes=Coalesce(Subquery(responsables, output_field=IntegerField()), 0),
        ).prefetch_related(
            Prefetch('mediciones', queryset=Medicion.objects.select_related('periodo')),
            Prefetch('rangos', queryset=RangoKPI.objects.select_related('estado_cumplimiento')),
            Prefetch(
                'solicitudes_ampliacion',
                queryset=SolicitudAmpliacionPlazo.objects.filter(
                    estado__in=[SolicitudAmpliacionPlazo.ESTADO_AUTORIZADA, SolicitudAmpliacionPlazo.ESTADO_PENDIENTE],
                ).select_related('periodo'),
            ),
        )

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto['listado_kpi'] = self.action == 'list'
        return contexto

    @action(detail=True, methods=['get'], url_path='reporte-pdf')
    def reporte_pdf(self, request, pk=None):
        """D5: reporte PDF de solo lectura del KPI con su historial de
        mediciones. Mismos permisos de lectura que el KPI (los 4 roles);
        solo KPI autorizados. No incrusta archivos de evidencia."""
        from django.http import HttpResponse
        from apps.auditoria.services import registrar_bitacora_obligatoria
        from apps.estrategia.services import TEXTO_OBJETIVO_ESPECIFICO_DIRECTO

        from .reporte_pdf import generar_reporte_kpi_pdf

        indicador = self.get_object()

        if indicador.estado != 'autorizado':
            raise Http404('Solo hay reportes de KPI autorizados.')

        kpi = IndicadorKPISerializer(indicador, context=self.get_serializer_context()).data
        mediciones = preparar_mediciones_lectura(
            MedicionViewSet.queryset.filter(indicador=indicador).order_by('periodo__fecha_inicio', 'id'),
        )
        datos_mediciones = MedicionSerializer(mediciones, many=True, context={'request': request}).data

        # Mismo criterio que textoObjetivoKpi() del frontend: un KPI directo
        # muestra su objetivo general.
        if kpi.get('es_directo') or kpi.get('objetivo_especifico_texto') == TEXTO_OBJETIVO_ESPECIFICO_DIRECTO:
            objetivo = kpi.get('objetivo_general_texto') or kpi.get('objetivo_especifico_texto')
        else:
            objetivo = kpi.get('objetivo_especifico_texto') or kpi.get('objetivo_general_texto')

        generado_en = timezone.localtime()
        contenido = generar_reporte_kpi_pdf(
            kpi, objetivo, datos_mediciones, generado_en, request.user.username,
        )

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='consultar',
            modulo='Reportes',
            descripcion=f'Generó el reporte PDF del KPI {indicador.nombre} ({len(datos_mediciones)} mediciones).',
            request=request,
        )

        respuesta = HttpResponse(contenido, content_type='application/pdf')
        respuesta['Content-Disposition'] = (
            f'attachment; filename="reporte_kpi_{indicador.id}_{generado_en:%Y%m%d}.pdf"'
        )
        respuesta['X-Content-Type-Options'] = 'nosniff'
        return respuesta

    def perform_create(self, serializer):
        from apps.auditoria.services import notificar_usuarios_gestion, registrar_bitacora_obligatoria
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

        registrar_bitacora_obligatoria(
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
        from apps.auditoria.services import registrar_bitacora_obligatoria

        indicador = serializer.save()

        # D3: un KPI que pasa a medirse en % y no tiene ningún rango recibe la
        # plantilla, igual que al crearse. Nunca toca rangos existentes.
        if not RangoKPI.objects.filter(indicador=indicador).exists():
            crear_rangos_provisionales(indicador)

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='actualizar',
            modulo='Indicadores KPI',
            descripcion=f'Actualizó el KPI {indicador.nombre}.',
            request=self.request,
        )

    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        from apps.auditoria.services import crear_notificacion, registrar_bitacora_obligatoria

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

        # Etapa 1 (auditoría M2): Anulado es terminal. Solo Borrador ->
        # Autorizado; antes un KPI anulado podía reautorizarse por API.
        if indicador.estado != 'borrador':
            return Response(
                {'detail': 'Un KPI anulado no puede volver a autorizarse.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not indicador.valor_meta:
            return Response(
                {'detail': 'No se puede autorizar un KPI sin meta configurada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # D3: un KPI autorizado clasifica sus mediciones con sus rangos; deben
        # existir, ser coherentes y corresponder a su unidad.
        errores_rangos = validar_rangos_para_autorizar(indicador)

        if errores_rangos:
            return Response(
                {'detail': ' '.join(errores_rangos), 'rangos': errores_rangos},
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

        registrar_bitacora_obligatoria(
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

    @action(detail=True, methods=['post'], url_path='configurar-rangos')
    def configurar_rangos(self, request, pk=None):
        """D3: guarda en una sola operación los rangos de evaluación de un KPI
        en Borrador (p. ej. uno en días, que no recibe la plantilla
        porcentual). Reemplaza el conjunto completo: actualiza el rango de cada
        estado enviado, crea los que falten y desactiva los que no se envían.
        Valida el conjunto entero antes de guardar, así que nunca deja rangos
        a medias. Los KPI autorizados conservan sus rangos."""
        from apps.auditoria.services import registrar_bitacora_obligatoria
        from .services import validar_conjunto_rangos

        indicador = self.get_object()

        if indicador.esta_bloqueado():
            return Response(
                {'detail': 'El Plan anual o el Plan estratégico de este KPI están Cerrados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if indicador.estado != 'borrador':
            return Response(
                {'detail': 'Solo se pueden configurar los rangos de un KPI en Borrador.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rangos, errores = validar_conjunto_rangos(request.data.get('rangos'))

        if errores:
            return Response({'detail': ' '.join(errores), 'rangos': errores}, status=status.HTTP_400_BAD_REQUEST)

        existentes = {rango.estado_cumplimiento_id: rango for rango in RangoKPI.objects.select_for_update().filter(indicador=indicador)}
        enviados = set()

        for datos in rangos:
            estado = datos['estado_cumplimiento']
            enviados.add(estado.id)
            rango = existentes.get(estado.id)

            if rango is None:
                RangoKPI.objects.create(
                    indicador=indicador, estado_cumplimiento=estado,
                    valor_minimo=datos['valor_minimo'], valor_maximo=datos['valor_maximo'], estado=True,
                )
            else:
                rango.valor_minimo = datos['valor_minimo']
                rango.valor_maximo = datos['valor_maximo']
                rango.estado = True
                rango.save(update_fields=['valor_minimo', 'valor_maximo', 'estado'])

        for estado_id, rango in existentes.items():
            if estado_id not in enviados and rango.estado:
                rango.estado = False
                rango.save(update_fields=['estado'])

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='actualizar',
            modulo='Rangos KPI',
            descripcion=(
                f'Configuró los rangos de evaluación del KPI {indicador.nombre} ({indicador.unidad_medida}): '
                + '; '.join(
                    f"{d['estado_cumplimiento'].nombre} desde {d['valor_minimo']}"
                    + (f" hasta menos de {d['valor_maximo']}" if d['valor_maximo'] is not None else ' sin límite')
                    for d in rangos
                )
                + '.'
            ),
            request=request,
        )

        serializer = RangoKPISerializer(
            RangoKPI.objects.filter(indicador=indicador).select_related('estado_cumplimiento', 'indicador'),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        from apps.auditoria.services import crear_notificacion, registrar_bitacora_obligatoria

        indicador = self.get_object()

        if indicador.esta_bloqueado():
            return Response(
                {'detail': 'El Plan anual o el Plan estratégico de este KPI están Cerrados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Etapa 1 (M2): evita re-anular (duplicaba bitácora y notificación).
        if indicador.estado == 'anulado':
            return Response(
                {'detail': 'El KPI ya se encuentra anulado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        indicador.estado = 'anulado'
        indicador.save(update_fields=['estado'])

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='eliminar',
            modulo='Indicadores KPI',
            descripcion=f'Anuló el KPI {indicador.nombre}.',
            request=request,
        )

        # Etapa 5: un KPI anulado no admite ampliaciones de plazo.
        dejar_sin_efecto_solicitudes_pendientes(
            indicador, 'el KPI fue anulado.', usuario=request.user, request=request,
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

class MetaKPIViewSet(BitacoraCatalogoMixin, viewsets.ModelViewSet):
    queryset = MetaKPI.objects.select_related(
        'indicador',
    ).all()
    serializer_class = MetaKPISerializer
    permission_classes = [PermisoCatalogoSoloAdmin]
    http_method_names = METODOS_SIN_BORRADO
    modulo_bitacora = 'Metas KPI'

    def describir_para_bitacora(self, meta):
        return f'la meta #{meta.id} del KPI {meta.indicador.nombre}'


class ResponsableKPIViewSet(viewsets.ModelViewSet):
    """Etapa 4 (auditoría M6): asignaciones de responsables. Las gestiona el
    Administrador de planificación (PermisoPlaneacion: los demás roles solo
    consultan). Filtros: ?indicador=<id>, ?estado=true|false."""

    queryset = ResponsableKPI.objects.select_related(
        'indicador',
        'usuario',
    ).order_by('usuario__username')
    serializer_class = ResponsableKPISerializer
    permission_classes = [PermisoPlaneacion]
    http_method_names = METODOS_SIN_BORRADO

    def get_queryset(self):
        queryset = super().get_queryset()
        indicador = self.request.query_params.get('indicador')
        estado = self.request.query_params.get('estado')

        if indicador and indicador.isdigit():
            queryset = queryset.filter(indicador_id=int(indicador))

        if estado in ('true', 'false'):
            queryset = queryset.filter(estado=(estado == 'true'))

        return queryset

    def _bitacora(self, accion, verbo, responsable):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion=accion,
            modulo='Responsables KPI',
            descripcion=(
                f'{verbo} a {responsable.usuario.username} como responsable del KPI '
                f'{responsable.indicador.nombre}.'
            ),
            request=self.request,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        indicador = serializer.validated_data['indicador']
        usuario = serializer.validated_data['usuario']
        existente = ResponsableKPI.objects.select_for_update().filter(
            indicador=indicador, usuario=usuario,
        ).first()

        if existente and existente.estado:
            return Response(
                {'detail': f'{usuario.username} ya es responsable de este KPI.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if existente:
            # Reactivación: misma fila (conserva su fecha de asignación
            # original); la bitácora deja la fecha de reactivación.
            existente.estado = True
            existente.save(update_fields=['estado'])
            self._bitacora('actualizar', 'Reactivó', existente)
            return Response(self.get_serializer(existente).data, status=status.HTTP_200_OK)

        from django.db import IntegrityError

        try:
            with transaction.atomic():
                responsable = serializer.save(estado=True)
        except IntegrityError:
            # Otra solicitud simultánea creó el mismo par (indicador, usuario).
            return Response(
                {'detail': f'{usuario.username} ya es responsable de este KPI.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        self._bitacora('crear', 'Asignó', responsable)
        return Response(self.get_serializer(responsable).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        estado_anterior = serializer.instance.estado
        responsable = serializer.save()

        if estado_anterior and not responsable.estado:
            self._bitacora('eliminar', 'Desactivó', responsable)
        elif not estado_anterior and responsable.estado:
            self._bitacora('actualizar', 'Reactivó', responsable)

    @action(detail=False, methods=['get'])
    def candidatos(self, request):
        """Ejecutores operativos activos que pueden asignarse. Solo para
        quien gestiona las asignaciones."""
        from apps.usuarios.models import Usuario
        from apps.usuarios.permissions import ROL_EJECUTOR_OPERATIVO, es_administrador_planificacion

        if not es_administrador_planificacion(request.user):
            return Response(
                {'detail': 'No tenés permisos para gestionar responsables de KPI.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        usuarios = Usuario.objects.filter(
            is_active=True, estado=True, rol__nombre__iexact=ROL_EJECUTOR_OPERATIVO,
        ).order_by('username')

        return Response([
            {'id': u.id, 'username': u.username, 'nombre': u.get_full_name() or u.username}
            for u in usuarios
        ])


class EstadoCumplimientoViewSet(BitacoraCatalogoMixin, viewsets.ModelViewSet):
    queryset = EstadoCumplimiento.objects.filter(estado=True).order_by('nombre')
    serializer_class = EstadoCumplimientoSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]
    http_method_names = METODOS_SIN_BORRADO
    modulo_bitacora = 'Estados de cumplimiento'

    def describir_para_bitacora(self, estado):
        return f'el estado de cumplimiento {estado.nombre}'


class RangoKPIViewSet(BitacoraCatalogoMixin, viewsets.ModelViewSet):
    queryset = RangoKPI.objects.select_related(
        'indicador',
        'estado_cumplimiento',
    ).all()
    serializer_class = RangoKPISerializer
    permission_classes = [PermisoCatalogoSoloAdmin]
    http_method_names = METODOS_SIN_BORRADO
    modulo_bitacora = 'Rangos KPI'

    def describir_para_bitacora(self, rango):
        return (
            f'el rango "{rango.estado_cumplimiento.nombre}" del KPI {rango.indicador.nombre}'
        )


class PeriodoMedicionViewSet(viewsets.ModelViewSet):
    queryset = PeriodoMedicion.objects.all()
    serializer_class = PeriodoMedicionSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]
    http_method_names = METODOS_SIN_BORRADO


def preparar_mediciones_lectura(queryset, con_acumulados=True):
    """Anotaciones y precargas que MedicionSerializer necesita para no hacer
    consultas por cada medición. Compartido por MedicionViewSet y por el
    reporte PDF del KPI (D5), para que ambos muestren lo mismo."""
    from django.db.models import OuterRef, Prefetch, Subquery

    # Etapa 5/6: fecha extraordinaria de la ampliación autorizada del
    # periodo (si existe), para la oportunidad de registro sin una
    # consulta por cada medición del listado.
    ampliacion = SolicitudAmpliacionPlazo.objects.filter(
        indicador=OuterRef('indicador_id'),
        periodo=OuterRef('periodo_id'),
        estado=SolicitudAmpliacionPlazo.ESTADO_AUTORIZADA,
    ).values('fecha_limite_extraordinaria')[:1]

    queryset = queryset.annotate(fecha_extraordinaria_ampliacion=Subquery(ampliacion))

    # D2: las evidencias (con quién las subió) en una sola consulta.
    queryset = queryset.prefetch_related(
        Prefetch('evidencias', queryset=EvidenciaMedicion.objects.select_related('subido_por')),
    )

    if con_acumulados:
        # Etapa 6 (M8): el promedio y el estado acumulados "hasta esta
        # medición" se calculan sobre las mediciones y los rangos del KPI
        # ya cargados, en lugar de dos consultas por cada medición.
        queryset = queryset.prefetch_related(
            Prefetch('indicador__mediciones', queryset=Medicion.objects.select_related('periodo')),
            Prefetch('indicador__rangos', queryset=RangoKPI.objects.select_related('estado_cumplimiento')),
        )

    return queryset


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
    http_method_names = METODOS_SIN_BORRADO
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = preparar_mediciones_lectura(
            super().get_queryset(),
            con_acumulados=self.action in ('list', 'retrieve'),
        )

        # D5 (consulta histórica): ?indicador=<id> limita el listado a un KPI,
        # en orden cronológico. Solo filtra: los permisos no cambian.
        if self.action == 'list' and 'indicador' in self.request.query_params:
            indicador_id = self.request.query_params.get('indicador')

            if not str(indicador_id).isdigit():
                return queryset.none()

            queryset = queryset.filter(indicador_id=indicador_id).order_by('periodo__fecha_inicio', 'id')

        return queryset

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

        # Etapa 5: la misma evaluación informa la fecha límite efectiva, la
        # ordinaria, el estado de la ampliación y si hoy puede pedirse una.
        info, motivo_ampliacion = evaluar_solicitud_ampliacion(indicador)
        autorizada = info['ampliacion_autorizada']
        pendiente = info['ampliacion_pendiente']

        return Response({
            'disponible': info['disponible'],
            'periodo_nombre': info['periodo_nombre'],
            'tipo_periodo': info['tipo_periodo'],
            'fecha_inicio_periodo': info['fecha_inicio_periodo'],
            'fecha_cierre': info['fecha_cierre'],
            'fecha_limite_registro': info['fecha_limite_registro'],
            'fecha_limite_ordinaria': info['fecha_limite_ordinaria'],
            'fecha_limite_extraordinaria': (
                info['fecha_limite_registro']
                if info['fecha_limite_registro'] != info['fecha_limite_ordinaria']
                else None
            ),
            'ampliacion_autorizada': autorizada and {
                'id': autorizada.id,
                'dias_autorizados': autorizada.dias_autorizados,
                'fecha_limite_extraordinaria': autorizada.fecha_limite_extraordinaria,
            },
            'ampliacion_pendiente': pendiente and {
                'id': pendiente.id,
                'dias_solicitados': pendiente.dias_solicitados,
                'fecha_limite_maxima': pendiente.fecha_limite_maxima,
            },
            'puede_solicitar_ampliacion': not motivo_ampliacion,
            'motivo_ampliacion': motivo_ampliacion,
            'inicio_seguimiento': info['inicio_seguimiento'],
            'periodo_parcial': info['periodo_parcial'],
            'motivo': info['motivo'],
        })

    # D2: evidencias múltiples. Consultar y descargar: cualquier autenticado
    # (GET, mismos permisos y queryset que el detalle). Agregar: solo
    # Ejecutor operativo (PermisoMedicion en POST). Nada se reemplaza ni se
    # elimina: no hay PUT/PATCH/DELETE sobre una evidencia.
    @action(detail=True, methods=['get', 'post'], url_path='evidencias')
    def evidencias(self, request, pk=None):
        medicion = self.get_object()

        if request.method == 'GET':
            return Response(EvidenciaMedicionSerializer(medicion.evidencias.all(), many=True).data)

        motivo = motivo_no_admite_evidencias(medicion)

        if motivo:
            return Response({'detail': motivo}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AgregarEvidenciasSerializer(data={'archivos': request.FILES.getlist('archivos')})
        serializer.is_valid(raise_exception=True)

        creadas = adjuntar_evidencias(
            medicion,
            serializer.validated_data['archivos'],
            request.user,
            request=request,
        )

        return Response(
            EvidenciaMedicionSerializer(creadas, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['get'],
        url_path=r'evidencias/(?P<evidencia_id>[0-9]+)/(?P<modo>ver|descargar)',
    )
    def evidencia_archivo(self, request, pk=None, evidencia_id=None, modo=None):
        medicion = self.get_object()
        evidencia = medicion.evidencias.filter(id=evidencia_id).first()

        if evidencia is None:
            raise Http404('La evidencia no existe en esta medición.')

        return self._responder_evidencia(evidencia, como_descarga=(modo == 'descargar'))

    # Rutas anteriores (un archivo por medición): se mantienen por
    # compatibilidad y sirven la evidencia más reciente.
    @action(detail=True, methods=['get'], url_path='evidencia')
    def evidencia(self, request, pk=None):
        return self._responder_evidencia(self._ultima_evidencia(), como_descarga=False)

    @action(detail=True, methods=['get'], url_path='evidencia/descargar')
    def evidencia_descargar(self, request, pk=None):
        return self._responder_evidencia(self._ultima_evidencia(), como_descarga=True)

    def _ultima_evidencia(self):
        medicion = self.get_object()
        evidencia = medicion.evidencias.order_by('-fecha_subida', '-id').first()

        if evidencia is None and medicion.evidencia:
            # Campo heredado aún no migrado: se sirve tal cual (instancia en
            # memoria, nunca se guarda).
            evidencia = EvidenciaMedicion(
                medicion=medicion,
                archivo=medicion.evidencia.name,
                nombre_original=os.path.basename(medicion.evidencia.name),
            )

        if evidencia is None:
            raise Http404('Esta medición no tiene evidencia adjunta.')

        return evidencia

    def _responder_evidencia(self, evidencia, como_descarga):
        try:
            archivo = evidencia.archivo.open('rb')
        except (FileNotFoundError, OSError):
            raise Http404('El archivo de evidencia no está disponible.')

        respuesta = FileResponse(
            archivo,
            as_attachment=como_descarga,
            filename=evidencia.nombre_original or os.path.basename(evidencia.archivo.name),
        )

        if evidencia.tipo_contenido:
            respuesta['Content-Type'] = evidencia.tipo_contenido

        respuesta['X-Content-Type-Options'] = 'nosniff'
        return respuesta


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    """Etapa 4 (auditoría M6/M7): solo consulta y las dos acciones de
    revisión. Antes era un ModelViewSet: por PUT/PATCH se podían cambiar el
    tipo, el mensaje, el KPI o el estado de una alerta sin dejar rastro.
    Las alertas las crea únicamente el sistema.

    Filtros opcionales: ?estado_alerta=pendiente y ?vigentes=1 (excluye
    alertas de KPI anulados o de planes Cerrados: siguen guardadas como
    historial, pero ya no requieren atención)."""

    queryset = Alerta.objects.select_related(
        'indicador',
        'medicion',
        'revisado_por',
    ).all()
    serializer_class = AlertaSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]

    def get_queryset(self):
        from .services import filtrar_alertas_vigentes

        queryset = super().get_queryset()
        estado_alerta = self.request.query_params.get('estado_alerta')

        if estado_alerta:
            queryset = queryset.filter(estado_alerta=estado_alerta)

        if self.request.query_params.get('vigentes') == '1':
            queryset = filtrar_alertas_vigentes(queryset)

        return queryset

    @action(detail=True, methods=['post'], url_path='marcar-revisada')
    def marcar_revisada(self, request, pk=None):
        from apps.auditoria.services import registrar_bitacora_obligatoria
        from .services import marcar_alerta_revisada

        alerta = self.get_object()
        estado_anterior = alerta.estado_alerta
        marcar_alerta_revisada(alerta, usuario=request.user)

        if alerta.estado_alerta != estado_anterior:
            registrar_bitacora_obligatoria(
                usuario=request.user,
                accion='actualizar',
                modulo='Alertas',
                descripcion=(
                    f'Marcó como revisada la alerta #{alerta.id} ({alerta.tipo_alerta}) '
                    f'del KPI {alerta.indicador.nombre}.'
                ),
                request=request,
            )

        serializer = self.get_serializer(alerta)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='marcar-todas-revisadas')
    def marcar_todas_revisadas(self, request):
        from apps.auditoria.services import registrar_bitacora_obligatoria
        from .services import marcar_todas_alertas_revisadas

        # Etapa 4: solo las vigentes, que son las que el usuario ve en el
        # centro de notificaciones; las de KPI anulados o planes Cerrados no
        # se dan por revisadas sin que nadie las haya visto.
        actualizadas = marcar_todas_alertas_revisadas(usuario=request.user, solo_vigentes=True)

        if actualizadas:
            registrar_bitacora_obligatoria(
                usuario=request.user,
                accion='actualizar',
                modulo='Alertas',
                descripcion=f'Marcó como revisadas {actualizadas} alerta(s) pendientes.',
                request=request,
            )

        return Response({
            'detail': f'{actualizadas} alerta(s) marcada(s) como revisada(s).'
        })



def consulta_bloqueo_solicitud_ampliacion():
    """Bloquea SOLO la fila de la solicitud (FOR UPDATE OF la tabla propia).
    PostgreSQL no admite FOR UPDATE sobre el lado nulable de un LEFT OUTER
    JOIN, y revisado_por es opcional: se une únicamente lo obligatorio
    (INNER JOIN) y el revisor se carga después, sin bloqueo."""
    return SolicitudAmpliacionPlazo.objects.select_for_update(of=('self',)).select_related(
        'indicador', 'periodo', 'solicitante',
    )


class SolicitudAmpliacionPlazoViewSet(viewsets.ModelViewSet):
    """Etapa 5: solicitudes de días adicionales para registrar mediciones.
    Sin edición ni borrado: se crean y luego solo cambian de estado por las
    acciones autorizar / rechazar / retirar (o por la tarea diaria, que las
    deja Vencidas o Sin efecto). El Ejecutor operativo ve solo las suyas.
    Filtros: ?estado=<estado>, ?indicador=<id>."""

    queryset = SolicitudAmpliacionPlazo.objects.select_related(
        'indicador',
        'periodo',
        'solicitante',
        'revisado_por',
    ).all()
    serializer_class = SolicitudAmpliacionPlazoSerializer
    permission_classes = [PermisoSolicitudAmpliacion]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        from apps.usuarios.permissions import es_administrador_planificacion

        queryset = super().get_queryset()

        if not es_administrador_planificacion(self.request.user):
            queryset = queryset.filter(solicitante=self.request.user)

        estado = self.request.query_params.get('estado')
        indicador = self.request.query_params.get('indicador')

        if estado:
            queryset = queryset.filter(estado=estado)

        if indicador and indicador.isdigit():
            queryset = queryset.filter(indicador_id=int(indicador))

        return queryset

    @staticmethod
    def _bloquear_indicador(indicador_id):
        """Serializa las operaciones sobre las solicitudes de un mismo KPI
        (crear, autorizar) para que dos peticiones simultáneas no evalúen
        el mismo estado a la vez."""
        return IndicadorKPI.objects.select_for_update().filter(pk=indicador_id).first()

    def _bloquear_solicitud(self):
        solicitud = self.get_object()
        self._bloquear_indicador(solicitud.indicador_id)

        return consulta_bloqueo_solicitud_ampliacion().get(pk=solicitud.pk)

    @staticmethod
    def _error(detalle, codigo=status.HTTP_400_BAD_REQUEST):
        return Response({'detail': detalle}, status=codigo)

    @staticmethod
    def _validar_resoluble(solicitud):
        """Mensaje de error si la solicitud ya no puede resolverse, o '' si
        sigue pendiente y dentro de su plazo máximo."""
        if solicitud.estado != SolicitudAmpliacionPlazo.ESTADO_PENDIENTE:
            return f'La solicitud ya no está pendiente: su estado es {solicitud.get_estado_display()}.'

        if solicitud.indicador.esta_bloqueado():
            # Defensa adicional: al Cerrar el plan la pendiente ya queda Sin
            # efecto; ninguna resolución (autorizar, rechazar, retirar) se
            # admite sobre un plan Cerrado.
            return (
                'El Plan anual o el Plan estratégico de este KPI están Cerrados: '
                'la solicitud ya no puede resolverse.'
            )

        from .services import hoy

        if hoy() > solicitud.fecha_limite_maxima:
            return (
                'Venció el plazo máximo para resolver esta solicitud '
                f'({solicitud.fecha_limite_maxima.strftime("%d/%m/%Y")}). '
                'El sistema la marcará como Vencida.'
            )

        return ''

    def create(self, request, *args, **kwargs):
        from django.db import IntegrityError
        from apps.auditoria.services import notificar_usuarios_gestion, registrar_bitacora_obligatoria

        indicador_id = str(request.data.get('indicador', ''))

        if indicador_id.isdigit():
            self._bloquear_indicador(int(indicador_id))

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                solicitud = serializer.save(solicitante=request.user)
        except IntegrityError:
            return self._error('Ya existe una solicitud pendiente de días adicionales para este periodo.')

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='crear',
            modulo=MODULO_AMPLIACIONES,
            descripcion=(
                f'Solicitó {solicitud.dias_solicitados} día(s) adicional(es) para el KPI '
                f'{solicitud.indicador.nombre} (periodo {solicitud.periodo.descripcion}, plazo '
                f'ordinario hasta el {solicitud.fecha_limite_ordinaria.strftime("%d/%m/%Y")}). '
                f'Motivo: {solicitud.motivo}'
            ),
            request=request,
        )

        notificar_usuarios_gestion(
            tipo='ampliacion_solicitada',
            titulo='Nueva solicitud de días adicionales',
            mensaje=(
                f'{request.user.username} pidió {solicitud.dias_solicitados} día(s) adicional(es) '
                f'para registrar el KPI "{solicitud.indicador.nombre}" '
                f'(periodo {solicitud.periodo.descripcion}).'
            ),
            enlace=enlace_solicitud_ampliacion(solicitud),
            excluir_usuario=request.user,
        )

        return Response(self.get_serializer(solicitud).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        from datetime import timedelta

        from django.db import IntegrityError
        from apps.auditoria.services import registrar_bitacora_obligatoria
        from .services import hoy

        solicitud = self._bloquear_solicitud()
        error = self._validar_resoluble(solicitud)

        if error:
            return self._error(error)

        indicador = solicitud.indicador

        if indicador.estado != 'autorizado':
            return self._error('El KPI ya no está autorizado: la solicitud solo puede rechazarse.')

        if Medicion.objects.filter(indicador=indicador, periodo=solicitud.periodo).exists():
            return self._error('El periodo ya tiene una medición: no corresponde ampliar su plazo.')

        if SolicitudAmpliacionPlazo.objects.filter(
            indicador=indicador, periodo=solicitud.periodo, estado=SolicitudAmpliacionPlazo.ESTADO_AUTORIZADA,
        ).exists():
            return self._error('Este periodo ya tiene una ampliación autorizada.')

        dias = request.data.get('dias_autorizados', solicitud.dias_solicitados)

        try:
            dias = int(dias)
        except (TypeError, ValueError):
            return self._error('Indicá un número entero de días a autorizar.')

        if dias < 1:
            return self._error('Autorizá al menos 1 día.')

        if dias > solicitud.dias_solicitados:
            return self._error(
                f'No se pueden autorizar más días de los solicitados ({solicitud.dias_solicitados}).'
            )

        fecha_extraordinaria = solicitud.fecha_limite_ordinaria + timedelta(days=dias)
        fecha_hoy = hoy()

        if fecha_extraordinaria < fecha_hoy:
            # Regla 8: nunca se autoriza un plazo que ya venció.
            minimo = (fecha_hoy - solicitud.fecha_limite_ordinaria).days
            return self._error(
                f'Con {dias} día(s) el plazo terminaría el {fecha_extraordinaria.strftime("%d/%m/%Y")}, '
                f'que ya pasó. Autorizá al menos {minimo} día(s).'
            )

        solicitud.estado = SolicitudAmpliacionPlazo.ESTADO_AUTORIZADA
        solicitud.dias_autorizados = dias
        solicitud.fecha_limite_extraordinaria = fecha_extraordinaria
        solicitud.revisado_por = request.user
        solicitud.fecha_resolucion = timezone.now()
        solicitud.observacion_revision = (request.data.get('observacion') or '').strip()

        try:
            with transaction.atomic():
                solicitud.save(update_fields=[
                    'estado', 'dias_autorizados', 'fecha_limite_extraordinaria',
                    'revisado_por', 'fecha_resolucion', 'observacion_revision',
                ])
        except IntegrityError:
            return self._error('Este periodo ya tiene una ampliación autorizada.')

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='actualizar',
            modulo=MODULO_AMPLIACIONES,
            descripcion=(
                f'Autorizó {dias} de {solicitud.dias_solicitados} día(s) solicitado(s) en '
                f'{describir_solicitud_ampliacion(solicitud)}, pedida por '
                f'{solicitud.solicitante.username}. Nuevo plazo de registro: '
                f'{fecha_extraordinaria.strftime("%d/%m/%Y")}.'
            ),
            request=request,
        )

        actualizar_alertas_por_ampliacion(solicitud, request.user, fecha_referencia=fecha_hoy)

        notificar_sin_duplicar(
            solicitud.solicitante,
            tipo='ampliacion_autorizada',
            titulo='Días adicionales autorizados',
            mensaje=(
                f'Se autorizaron {dias} día(s) adicional(es) para el KPI "{indicador.nombre}" '
                f'(periodo {solicitud.periodo.descripcion}). Podés registrar la medición hasta el '
                f'{fecha_extraordinaria.strftime("%d/%m/%Y")}.'
            ),
            enlace=enlace_solicitud_ampliacion(solicitud),
        )

        return Response(self.get_serializer(solicitud).data)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        solicitud = self._bloquear_solicitud()
        error = self._validar_resoluble(solicitud)

        if error:
            return self._error(error)

        observacion = (request.data.get('observacion') or '').strip()

        if not observacion:
            return Response(
                {'observacion': 'Indicá el motivo del rechazo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitud.estado = SolicitudAmpliacionPlazo.ESTADO_RECHAZADA
        solicitud.revisado_por = request.user
        solicitud.fecha_resolucion = timezone.now()
        solicitud.observacion_revision = observacion
        solicitud.save(update_fields=['estado', 'revisado_por', 'fecha_resolucion', 'observacion_revision'])

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='actualizar',
            modulo=MODULO_AMPLIACIONES,
            descripcion=(
                f'Rechazó {describir_solicitud_ampliacion(solicitud)}, pedida por '
                f'{solicitud.solicitante.username}. Motivo: {observacion}'
            ),
            request=request,
        )

        notificar_sin_duplicar(
            solicitud.solicitante,
            tipo='ampliacion_rechazada',
            titulo='Solicitud de días adicionales rechazada',
            mensaje=(
                f'Se rechazó tu solicitud de días adicionales para el KPI '
                f'"{solicitud.indicador.nombre}" (periodo {solicitud.periodo.descripcion}). '
                f'Motivo: {observacion}'
            ),
            enlace=enlace_solicitud_ampliacion(solicitud),
        )

        return Response(self.get_serializer(solicitud).data)

    @action(detail=True, methods=['post'])
    def retirar(self, request, pk=None):
        from apps.auditoria.services import notificar_usuarios_gestion, registrar_bitacora_obligatoria

        solicitud = self._bloquear_solicitud()

        if solicitud.solicitante_id != request.user.id:
            return self._error('Solo quien hizo la solicitud puede retirarla.', status.HTTP_403_FORBIDDEN)

        error = self._validar_resoluble(solicitud)

        if error:
            return self._error(error)

        solicitud.estado = SolicitudAmpliacionPlazo.ESTADO_RETIRADA
        solicitud.fecha_resolucion = timezone.now()
        solicitud.save(update_fields=['estado', 'fecha_resolucion'])

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='actualizar',
            modulo=MODULO_AMPLIACIONES,
            descripcion=f'Retiró {describir_solicitud_ampliacion(solicitud)}.',
            request=request,
        )

        notificar_usuarios_gestion(
            tipo='ampliacion_retirada',
            titulo='Solicitud de días adicionales retirada',
            mensaje=(
                f'{request.user.username} retiró su solicitud de días adicionales para el KPI '
                f'"{solicitud.indicador.nombre}" (periodo {solicitud.periodo.descripcion}).'
            ),
            enlace=enlace_solicitud_ampliacion(solicitud),
        )

        return Response(self.get_serializer(solicitud).data)
