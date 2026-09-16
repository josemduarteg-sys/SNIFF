from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Rol, SolicitudRestablecimientoPassword, Usuario
from .permissions import EsAdministradorSistema
from .serializers import (
    CambiarPasswordSerializer,
    RolSerializer,
    SolicitarRestablecimientoPasswordSerializer,
    SolicitudRestablecimientoPasswordSerializer,
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

    def perform_create(self, serializer):
        from apps.auditoria.services import registrar_bitacora_seguro

        usuario_creado = serializer.save()

        registrar_bitacora_seguro(
            usuario=self.request.user,
            accion='crear',
            modulo='Usuarios',
            descripcion=f'Creó el usuario {usuario_creado.username}.',
            request=self.request,
        )

    def perform_update(self, serializer):
        from apps.auditoria.services import registrar_bitacora_seguro

        estaba_inactivo = (
            serializer.instance.estado is False or serializer.instance.is_active is False
        )

        usuario_actualizado = serializer.save()

        quedo_activo = (
            usuario_actualizado.estado is not False
            and usuario_actualizado.is_active is not False
        )

        if estaba_inactivo and quedo_activo:
            descripcion = f'Reactivó el usuario {usuario_actualizado.username}.'
        else:
            descripcion = f'Actualizó datos del usuario {usuario_actualizado.username}.'

        registrar_bitacora_seguro(
            usuario=self.request.user,
            accion='actualizar',
            modulo='Usuarios',
            descripcion=descripcion,
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        from apps.auditoria.services import registrar_bitacora_seguro

        usuario = self.get_object()

        if usuario.id == request.user.id:
            return Response(
                {'detail': 'No podés inactivar tu propio usuario desde esta opción.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario.estado = False
        usuario.is_active = False
        usuario.save(update_fields=['estado', 'is_active'])

        registrar_bitacora_seguro(
            usuario=request.user,
            accion='eliminar',
            modulo='Usuarios',
            descripcion=f'Inactivó el usuario {usuario.username}.',
            request=request,
        )

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


class SolicitarRestablecimientoPasswordView(APIView):
    permission_classes = [AllowAny]

    MENSAJE_GENERICO = (
        'Si la cuenta existe, la solicitud fue enviada para revisión administrativa.'
    )

    def post(self, request):
        from apps.auditoria.services import notificar_administradores, registrar_bitacora_seguro

        serializer = SolicitarRestablecimientoPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identificador = serializer.validated_data['identificador'].strip()
        motivo = serializer.validated_data.get('motivo', '').strip()

        usuario = Usuario.objects.filter(
            Q(username__iexact=identificador) | Q(correo__iexact=identificador),
            is_active=True,
        ).first()

        if usuario:
            ya_tiene_solicitud_activa = SolicitudRestablecimientoPassword.objects.filter(
                usuario=usuario,
                estado__in=['pendiente', 'aprobada'],
            ).exists()

            if not ya_tiene_solicitud_activa:
                solicitud = SolicitudRestablecimientoPassword.objects.create(
                    usuario=usuario,
                    identificador_ingresado=identificador,
                    motivo=motivo,
                )

                registrar_bitacora_seguro(
                    usuario=usuario,
                    accion='crear',
                    modulo='Restablecimiento de contraseña',
                    descripcion=(
                        f'El usuario {usuario.username} solicitó restablecimiento de contraseña.'
                    ),
                    request=request,
                )

                notificar_administradores(
                    tipo='solicitud_restablecimiento_password',
                    titulo='Solicitud de restablecimiento de contraseña',
                    mensaje=f'El usuario {usuario.username} solicitó restablecer su contraseña.',
                    enlace=f'/usuarios?tab=solicitudes&resaltarSolicitud={solicitud.id}',
                )

        return Response({'detail': self.MENSAJE_GENERICO}, status=status.HTTP_200_OK)


class SolicitudRestablecimientoPasswordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SolicitudRestablecimientoPassword.objects.select_related(
        'usuario',
        'revisado_por',
        'atendido_por',
    ).all()
    serializer_class = SolicitudRestablecimientoPasswordSerializer
    permission_classes = [IsAuthenticated, EsAdministradorSistema]

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        from apps.auditoria.services import registrar_bitacora_seguro

        solicitud = self.get_object()

        if solicitud.estado != 'pendiente':
            return Response(
                {'detail': 'Solo se pueden aprobar solicitudes pendientes.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitud.estado = 'aprobada'
        solicitud.revisado_por = request.user
        solicitud.fecha_revision = timezone.now()
        solicitud.observacion_admin = request.data.get(
            'observacion_admin', solicitud.observacion_admin
        )
        solicitud.save(
            update_fields=['estado', 'revisado_por', 'fecha_revision', 'observacion_admin']
        )

        registrar_bitacora_seguro(
            usuario=request.user,
            accion='actualizar',
            modulo='Restablecimiento de contraseña',
            descripcion=(
                f'Aprobó la solicitud de restablecimiento #{solicitud.id} '
                f'del usuario {solicitud.usuario.username}.'
            ),
            request=request,
        )

        serializer = self.get_serializer(solicitud)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        from apps.auditoria.services import registrar_bitacora_seguro

        solicitud = self.get_object()

        if solicitud.estado != 'pendiente':
            return Response(
                {'detail': 'Solo se pueden rechazar solicitudes pendientes.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitud.estado = 'rechazada'
        solicitud.revisado_por = request.user
        solicitud.fecha_revision = timezone.now()
        solicitud.observacion_admin = request.data.get(
            'observacion_admin', solicitud.observacion_admin
        )
        solicitud.save(
            update_fields=['estado', 'revisado_por', 'fecha_revision', 'observacion_admin']
        )

        registrar_bitacora_seguro(
            usuario=request.user,
            accion='actualizar',
            modulo='Restablecimiento de contraseña',
            descripcion=(
                f'Rechazó la solicitud de restablecimiento #{solicitud.id} '
                f'del usuario {solicitud.usuario.username}.'
            ),
            request=request,
        )

        serializer = self.get_serializer(solicitud)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='asignar-password-temporal')
    def asignar_password_temporal(self, request, pk=None):
        from apps.auditoria.services import registrar_bitacora_seguro

        solicitud = self.get_object()

        if solicitud.estado not in ('pendiente', 'aprobada'):
            return Response(
                {
                    'detail': (
                        'Solo se puede asignar contraseña temporal a solicitudes '
                        'pendientes o aprobadas.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        password_temporal = request.data.get('password_temporal')

        if not password_temporal:
            return Response(
                {'detail': 'Debe enviar la contraseña temporal.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = solicitud.usuario
        usuario.set_password(password_temporal)
        usuario.debe_cambiar_password = True
        usuario.save(update_fields=['password', 'debe_cambiar_password'])

        ahora = timezone.now()

        if solicitud.estado == 'pendiente':
            solicitud.revisado_por = request.user
            solicitud.fecha_revision = ahora

        solicitud.estado = 'atendida'
        solicitud.atendido_por = request.user
        solicitud.fecha_atencion = ahora
        solicitud.save()

        registrar_bitacora_seguro(
            usuario=request.user,
            accion='actualizar',
            modulo='Restablecimiento de contraseña',
            descripcion=(
                f'Asignó contraseña temporal al usuario {solicitud.usuario.username} '
                f'mediante la solicitud #{solicitud.id}.'
            ),
            request=request,
        )

        return Response(
            {'detail': 'Contraseña temporal asignada correctamente.'},
            status=status.HTTP_200_OK,
        )