from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.usuarios.permissions import (
    PermisoCatalogoSoloAdmin,
    PermisoEstrategiaObjetivo,
)
from .models import (
    Area,
    ObjetivoEspecifico,
    ObjetivoGeneral,
    PlanAnual,
    PlanEstrategico,
    PonderacionAnualObjetivoGeneral,
)
from .serializers import (
    AreaSerializer,
    CompletarVigenciaPlanAnualSerializer,
    ObjetivoEspecificoSerializer,
    ObjetivoGeneralSerializer,
    PlanAnualSerializer,
    PlanEstrategicoSerializer,
    PonderacionAnualObjetivoGeneralSerializer,
)
from .services import plan_estrategico_esta_cerrado

# Sin DELETE: un Plan estratégico o un Objetivo general con trazabilidad
# asociada no debe poder desaparecer físicamente por una acción normal de
# usuario (ver DIAGNOSTICO_REDISENO_SNIFF.md, sección 11).
METODOS_SIN_BORRADO = ['get', 'post', 'put', 'patch', 'head', 'options']


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [PermisoCatalogoSoloAdmin]
    # Etapa 1 (M3): el frontend ya inactiva Áreas por PATCH (estado=False);
    # sin borrado físico, igual que el resto de este módulo.
    http_method_names = METODOS_SIN_BORRADO

    # Etapa 4 (M7): trazabilidad de altas, cambios y (des)activaciones.
    def perform_create(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        area = serializer.save()

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='crear',
            modulo='Áreas',
            descripcion=f'Creó el área {area.nombre}.',
            request=self.request,
        )

    def perform_update(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        estado_anterior = serializer.instance.estado
        nombre_anterior = serializer.instance.nombre
        area = serializer.save()

        if estado_anterior and not area.estado:
            accion, descripcion = 'eliminar', f'Inactivó el área {area.nombre}.'
        elif not estado_anterior and area.estado:
            accion, descripcion = 'actualizar', f'Reactivó el área {area.nombre}.'
        elif nombre_anterior != area.nombre:
            accion, descripcion = 'actualizar', f'Actualizó el área {nombre_anterior} (ahora {area.nombre}).'
        else:
            accion, descripcion = 'actualizar', f'Actualizó el área {area.nombre}.'

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion=accion,
            modulo='Áreas',
            descripcion=descripcion,
            request=self.request,
        )


class PlanEstrategicoViewSet(viewsets.ModelViewSet):
    queryset = PlanEstrategico.objects.select_related('creado_por').all()
    serializer_class = PlanEstrategicoSerializer
    permission_classes = [PermisoEstrategiaObjetivo]
    http_method_names = METODOS_SIN_BORRADO

    def perform_create(self, serializer):
        from apps.auditoria.services import notificar_usuarios_gestion, registrar_bitacora_obligatoria

        plan = serializer.save(
            creado_por=self.request.user,
            estado=PlanEstrategico.ESTADO_BORRADOR,
        )

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='crear',
            modulo='Planes estratégicos',
            descripcion=f'Creó el Plan estratégico {plan.titulo}.',
            request=self.request,
        )

        notificar_usuarios_gestion(
            tipo='plan_estrategico_creado',
            titulo='Nuevo Plan estratégico registrado',
            mensaje=f'{self.request.user.username} registró el Plan estratégico "{plan.titulo}".',
            enlace=f'/planes-estrategicos?resaltar={plan.id}',
            excluir_usuario=self.request.user,
        )

    def perform_update(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        plan = serializer.save()

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='actualizar',
            modulo='Planes estratégicos',
            descripcion=f'Actualizó el Plan estratégico {plan.titulo}.',
            request=self.request,
        )

    @action(detail=True, methods=['post'], url_path='poner-en-uso')
    def poner_en_uso(self, request, pk=None):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        plan = self.get_object()

        if plan.estado != PlanEstrategico.ESTADO_BORRADOR:
            return Response(
                {'detail': 'Solo un Plan estratégico en Borrador puede pasar a En uso.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan.estado = PlanEstrategico.ESTADO_EN_USO
        plan.save(update_fields=['estado'])

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='actualizar',
            modulo='Planes estratégicos',
            descripcion=f'Puso en uso el Plan estratégico {plan.titulo}.',
            request=request,
        )

        serializer = self.get_serializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        plan = self.get_object()

        if plan.estado != PlanEstrategico.ESTADO_EN_USO:
            return Response(
                {'detail': 'Solo un Plan estratégico En uso puede Cerrarse.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan.estado = PlanEstrategico.ESTADO_CERRADO
        plan.save(update_fields=['estado'])

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='actualizar',
            modulo='Planes estratégicos',
            descripcion=f'Cerró el Plan estratégico {plan.titulo}.',
            request=request,
        )

        # Etapa 5: las solicitudes de días adicionales pendientes de sus KPI
        # quedan Sin efecto en esta misma operación (y transacción).
        from apps.indicadores.services import dejar_sin_efecto_por_cierre_de_plan

        dejar_sin_efecto_por_cierre_de_plan(
            f'se cerró el Plan estratégico {plan.titulo}.', request.user, request, plan_estrategico=plan,
        )

        serializer = self.get_serializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ObjetivoGeneralViewSet(viewsets.ModelViewSet):
    queryset = ObjetivoGeneral.objects.select_related(
        'plan_estrategico',
        'creado_por',
    ).all()
    serializer_class = ObjetivoGeneralSerializer
    permission_classes = [PermisoEstrategiaObjetivo]
    http_method_names = METODOS_SIN_BORRADO

    def perform_create(self, serializer):
        from apps.auditoria.services import notificar_usuarios_gestion, registrar_bitacora_obligatoria

        objetivo = serializer.save(creado_por=self.request.user)

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='crear',
            modulo='Objetivos generales',
            descripcion=(
                f'Creó un objetivo general en el Plan estratégico '
                f'{objetivo.plan_estrategico.titulo}.'
            ),
            request=self.request,
        )

        notificar_usuarios_gestion(
            tipo='objetivo_general_creado',
            titulo='Nuevo objetivo general registrado',
            mensaje=(
                f'{self.request.user.username} registró un objetivo general en '
                f'"{objetivo.plan_estrategico.titulo}".'
            ),
            enlace=f'/objetivos-generales?resaltar={objetivo.id}',
            excluir_usuario=self.request.user,
        )

    def perform_update(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        objetivo = serializer.save()

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='actualizar',
            modulo='Objetivos generales',
            descripcion=(
                f'Actualizó un objetivo general del Plan estratégico '
                f'{objetivo.plan_estrategico.titulo}.'
            ),
            request=self.request,
        )


class PlanAnualViewSet(viewsets.ModelViewSet):
    queryset = PlanAnual.objects.select_related('plan_estrategico', 'creado_por').all()
    serializer_class = PlanAnualSerializer
    permission_classes = [PermisoEstrategiaObjetivo]
    http_method_names = METODOS_SIN_BORRADO

    def perform_create(self, serializer):
        from apps.auditoria.services import notificar_usuarios_gestion, registrar_bitacora_obligatoria

        plan_anual = serializer.save(
            creado_por=self.request.user,
            estado=PlanAnual.ESTADO_BORRADOR,
        )

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='crear',
            modulo='Planes anuales',
            descripcion=(
                f'Creó el {plan_anual.nombre} del Plan estratégico '
                f'{plan_anual.plan_estrategico.titulo}.'
            ),
            request=self.request,
        )

        notificar_usuarios_gestion(
            tipo='plan_anual_creado',
            titulo='Nuevo Plan anual registrado',
            mensaje=(
                f'{self.request.user.username} registró el {plan_anual.nombre} en '
                f'"{plan_anual.plan_estrategico.titulo}".'
            ),
            enlace=f'/planes-anuales?resaltar={plan_anual.id}',
            excluir_usuario=self.request.user,
        )

    def perform_update(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        plan_anual = serializer.save()

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='actualizar',
            modulo='Planes anuales',
            descripcion=f'Actualizó el {plan_anual.nombre}.',
            request=self.request,
        )

    @action(detail=True, methods=['post'], url_path='poner-en-uso')
    def poner_en_uso(self, request, pk=None):
        from django.db import IntegrityError, transaction

        from apps.auditoria.services import registrar_bitacora_obligatoria

        plan_anual = self.get_object()

        if plan_estrategico_esta_cerrado(plan_anual.plan_estrategico):
            return Response(
                {'detail': 'El Plan estratégico está Cerrado; el Plan anual no puede modificarse.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if plan_anual.estado != PlanAnual.ESTADO_BORRADOR:
            return Response(
                {'detail': 'Solo un Plan anual en Borrador puede pasar a En uso.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Regla Hernán bloque 1 (corregida): un único Plan anual "En uso"
        # POR Plan estratégico, no en todo SNIFF — dos Planes estratégicos
        # distintos pueden tener cada uno su propio Plan anual activo al
        # mismo tiempo. select_for_update() bloquea las filas ya existentes
        # de ESTE plan_estrategico en estado En uso durante esta
        # transacción, evitando que dos cierres/activaciones concurrentes
        # dentro de la misma estrategia pisen la verificación entre sí. No
        # cierra ningún plan automáticamente: si ya hay uno activo en esta
        # misma estrategia, se rechaza y se identifica cuál es.
        with transaction.atomic():
            otro_en_uso = (
                PlanAnual.objects
                .select_for_update()
                .select_related('plan_estrategico')
                .filter(
                    estado=PlanAnual.ESTADO_EN_USO,
                    plan_estrategico_id=plan_anual.plan_estrategico_id,
                )
                .exclude(pk=plan_anual.pk)
                .first()
            )

            if otro_en_uso is not None:
                return Response(
                    {
                        'detail': (
                            f'Ya existe un Plan anual En uso en el Plan estratégico '
                            f'"{otro_en_uso.plan_estrategico.titulo}": "{otro_en_uso.nombre}". '
                            'Cerralo antes de activar otro Plan anual de esta misma estrategia.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            plan_anual.estado = PlanAnual.ESTADO_EN_USO

            try:
                plan_anual.save(update_fields=['estado'])
            except IntegrityError:
                # Resguardo final a nivel de base de datos, por si el
                # constraint de unicidad ya está aplicado (ver nota en la
                # migración) y una carrera extrema lo dispara pese al lock
                # anterior.
                return Response(
                    {
                        'detail': (
                            'Ya existe un Plan anual En uso en este Plan estratégico. '
                            'Cerralo antes de activar otro.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='actualizar',
            modulo='Planes anuales',
            descripcion=f'Puso en uso el {plan_anual.nombre}.',
            request=request,
        )

        serializer = self.get_serializer(plan_anual)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='completar-vigencia')
    def completar_vigencia(self, request, pk=None):
        """Etapa 1 (auditoría M9): completado único de fechas de un Plan
        anual antiguo En uso. Ver CompletarVigenciaPlanAnualSerializer."""
        from django.db import transaction

        from apps.auditoria.services import registrar_bitacora_obligatoria

        self.get_object()

        # La fila se bloquea y se relee dentro de la transacción: dos
        # solicitudes simultáneas no pueden completar las fechas dos veces.
        with transaction.atomic():
            plan_anual = (
                PlanAnual.objects
                .select_for_update()
                .select_related('plan_estrategico')
                .get(pk=pk)
            )
            serializer = CompletarVigenciaPlanAnualSerializer(plan_anual, data=request.data)
            serializer.is_valid(raise_exception=True)
            plan_anual = serializer.save()

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='actualizar',
            modulo='Planes anuales',
            descripcion=(
                f'Completó la vigencia del {plan_anual.nombre} del Plan estratégico '
                f'{plan_anual.plan_estrategico.titulo}: '
                f'{plan_anual.fecha_inicio.strftime("%d/%m/%Y")} al '
                f'{plan_anual.fecha_fin.strftime("%d/%m/%Y")}.'
            ),
            request=request,
        )

        return Response(self.get_serializer(plan_anual).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        plan_anual = self.get_object()

        if plan_estrategico_esta_cerrado(plan_anual.plan_estrategico):
            return Response(
                {'detail': 'El Plan estratégico está Cerrado; el Plan anual no puede modificarse.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if plan_anual.estado != PlanAnual.ESTADO_EN_USO:
            return Response(
                {'detail': 'Solo un Plan anual En uso puede Cerrarse.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan_anual.estado = PlanAnual.ESTADO_CERRADO
        plan_anual.save(update_fields=['estado'])

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='actualizar',
            modulo='Planes anuales',
            descripcion=f'Cerró el {plan_anual.nombre}.',
            request=request,
        )

        # Etapa 5: las solicitudes de días adicionales pendientes de sus KPI
        # quedan Sin efecto en esta misma operación (y transacción).
        from apps.indicadores.services import dejar_sin_efecto_por_cierre_de_plan

        dejar_sin_efecto_por_cierre_de_plan(
            f'se cerró el {plan_anual.nombre}.', request.user, request, plan_anual=plan_anual,
        )

        serializer = self.get_serializer(plan_anual)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ObjetivoEspecificoViewSet(viewsets.ModelViewSet):
    # Bloque 3 (KPI directo): excluye los objetivos específicos
    # "implícitos" que el sistema crea/reutiliza para los KPI directos
    # (ver apps/estrategia/services.obtener_o_crear_objetivo_especifico_directo).
    # No son responsabilidad de este módulo: no deben aparecer como
    # opción seleccionable en el formulario de KPI ni quedar editables o
    # eliminables desde la administración de objetivos específicos, donde
    # alguien podría romper por accidente la relación 1 a 1 que los KPI
    # directos asumen con su combinación (plan_anual, objetivo_general).
    queryset = ObjetivoEspecifico.objects.filter(
        es_generado_automaticamente=False,
    ).select_related(
        'plan_anual',
        'plan_anual__plan_estrategico',
        'objetivo_general',
        'creado_por',
    ).all()
    serializer_class = ObjetivoEspecificoSerializer
    permission_classes = [PermisoEstrategiaObjetivo]
    http_method_names = METODOS_SIN_BORRADO

    def perform_create(self, serializer):
        from apps.auditoria.services import notificar_usuarios_gestion, registrar_bitacora_obligatoria

        objetivo = serializer.save(creado_por=self.request.user)

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='crear',
            modulo='Objetivos específicos',
            descripcion=(
                f'Creó un objetivo específico en el {objetivo.plan_anual.nombre} '
                f'del Plan estratégico {objetivo.plan_anual.plan_estrategico.titulo}.'
            ),
            request=self.request,
        )

        notificar_usuarios_gestion(
            tipo='objetivo_especifico_creado',
            titulo='Nuevo objetivo específico registrado',
            mensaje=(
                f'{self.request.user.username} registró un objetivo específico en '
                f'"{objetivo.plan_anual.nombre}".'
            ),
            enlace=f'/objetivos-especificos?resaltar={objetivo.id}',
            excluir_usuario=self.request.user,
        )

    def perform_update(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        objetivo = serializer.save()

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='actualizar',
            modulo='Objetivos específicos',
            descripcion=(
                f'Actualizó un objetivo específico del {objetivo.plan_anual.nombre}.'
            ),
            request=self.request,
        )


class PonderacionAnualObjetivoGeneralViewSet(viewsets.ModelViewSet):
    # Bloque 3, segunda parte: sin DELETE, mismo criterio que el resto de
    # este módulo (ver METODOS_SIN_BORRADO) — una ponderación mal
    # ingresada se corrige con un PATCH, no se borra.
    queryset = PonderacionAnualObjetivoGeneral.objects.select_related(
        'objetivo_general',
        'objetivo_general__plan_estrategico',
        'plan_anual',
        'creado_por',
    ).all()
    serializer_class = PonderacionAnualObjetivoGeneralSerializer
    permission_classes = [PermisoEstrategiaObjetivo]
    http_method_names = METODOS_SIN_BORRADO

    def perform_create(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        ponderacion = serializer.save(creado_por=self.request.user)

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='crear',
            modulo='Ponderaciones anuales',
            descripcion=(
                f'Asignó {ponderacion.porcentaje}% de ponderación anual al objetivo '
                f'general en {ponderacion.plan_anual.nombre}.'
            ),
            request=self.request,
        )

    def perform_update(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        ponderacion = serializer.save()

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='actualizar',
            modulo='Ponderaciones anuales',
            descripcion=(
                f'Actualizó a {ponderacion.porcentaje}% la ponderación anual del '
                f'objetivo general en {ponderacion.plan_anual.nombre}.'
            ),
            request=self.request,
        )
