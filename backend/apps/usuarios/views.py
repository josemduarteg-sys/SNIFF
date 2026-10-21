from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from django.utils.decorators import method_decorator
from rest_framework.exceptions import AuthenticationFailed, Throttled, ValidationError
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Rol, SolicitudRestablecimientoPassword, Usuario
from .permissions import EsAdministradorSistema, es_administrador_sistema
from .throttles import (
    LimiteLoginPorIP,
    LimiteLoginPorUsuario,
    LimiteRestablecimientoPorIdentificador,
    LimiteRestablecimientoPorIP,
)
from .serializers import (
    CambiarPasswordSerializer,
    RolSerializer,
    SolicitarRestablecimientoPasswordSerializer,
    SolicitudRestablecimientoPasswordSerializer,
    UsuarioActualSerializer,
    UsuarioSerializer,
)


class MensajeLimiteIntentosMixin:
    """Etapa 2 (B2): 429 con un mensaje claro y el tiempo de espera."""

    def throttled(self, request, wait):
        raise Throttled(
            wait=wait,
            detail='Demasiados intentos. Esperá unos minutos antes de volver a intentarlo.',
        )


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class LoginView(MensajeLimiteIntentosMixin, TokenObtainPairView):
    """Mismo inicio de sesión JWT de siempre, con límite de intentos por IP
    y por nombre de usuario (Etapa 2, B2). Los límites expiran solos: no
    se bloquea la cuenta.

    Etapa 4 (M7): registra en bitácora el inicio de sesión exitoso (y
    actualiza ultimo_acceso / last_login) y el intento fallido sobre una
    cuenta existente. Queda fuera de ATOMIC_REQUESTS a propósito: el intento
    fallido debe guardarse aunque la respuesta sea un 401. Nunca se registra
    la contraseña ni los tokens."""

    throttle_classes = [LimiteLoginPorIP, LimiteLoginPorUsuario]

    def post(self, request, *args, **kwargs):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except AuthenticationFailed:
            self._registrar_intento_fallido(request)
            raise
        except TokenError as error:
            raise InvalidToken(error.args[0])

        usuario = serializer.user
        ahora = timezone.now()

        with transaction.atomic():
            Usuario.objects.filter(pk=usuario.pk).update(ultimo_acceso=ahora, last_login=ahora)
            registrar_bitacora_obligatoria(
                usuario=usuario,
                accion='inicio_sesion',
                modulo='Inicio de sesión',
                descripcion=f'El usuario {usuario.username} inició sesión.',
                request=request,
            )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    def handle_exception(self, exc):
        # El manejador de DRF llama a set_rollback(), pensado para vistas
        # atómicas. Esta no lo es: se le da un bloque propio (vacío) para
        # que marque solo ese bloque y no una transacción externa, que
        # revertiría el registro del intento fallido ya guardado.
        with transaction.atomic():
            return super().handle_exception(exc)

    def _registrar_intento_fallido(self, request):
        from apps.auditoria.services import registrar_bitacora_seguro

        datos = request.data if hasattr(request.data, 'get') else {}
        username = str(datos.get('username') or '').strip()
        usuario = Usuario.objects.filter(username=username).first() if username else None

        # Solo para cuentas existentes (la bitácora exige un usuario). Un
        # fallo al registrar el intento no cambia la respuesta (401).
        if usuario:
            registrar_bitacora_seguro(
                usuario=usuario,
                accion='error',
                modulo='Inicio de sesión',
                descripcion=f'Intento fallido de inicio de sesión para el usuario {usuario.username}.',
                request=request,
            )


class LogoutView(APIView):
    """Etapa 4 (M7): cierre de sesión explícito, solo para dejar constancia
    en bitácora. Los tokens JWT no se invalidan en el servidor (no está
    activada la lista negra de SimpleJWT): el frontend los elimina."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        registrar_bitacora_obligatoria(
            usuario=request.user,
            accion='cierre_sesion',
            modulo='Inicio de sesión',
            descripcion=f'El usuario {request.user.username} cerró sesión.',
            request=request,
        )

        return Response({'detail': 'Sesión cerrada.'}, status=status.HTTP_200_OK)


MENSAJE_ULTIMO_ADMIN_SISTEMA = (
    'No se puede quitar el rol ni desactivar al último Administrador del sistema '
    'activo. Asigná primero ese rol a otro usuario activo.'
)


_SIN_CAMBIO = object()


def _es_admin_sistema_activo(usuario, rol=_SIN_CAMBIO, is_active=_SIN_CAMBIO, estado=_SIN_CAMBIO):
    """True si `usuario` (con los valores que quedarían tras la operación)
    es un Administrador del sistema habilitado. Reutiliza
    es_administrador_sistema, así que un superusuario técnico de Django
    solo cuenta mientras no tenga un Rol de aplicación asignado — is_staff/
    is_superuser NO equivalen por sí solos al rol funcional."""
    rol = usuario.rol if rol is _SIN_CAMBIO else rol
    is_active = usuario.is_active if is_active is _SIN_CAMBIO else is_active
    estado = usuario.estado if estado is _SIN_CAMBIO else estado

    if not is_active or estado is False:
        return False

    copia = Usuario(rol=rol, is_superuser=usuario.is_superuser, is_active=True)
    copia.rol_id = rol.id if rol else None
    return es_administrador_sistema(copia)


def _validar_continuidad_admin_sistema(usuario, rol=_SIN_CAMBIO, is_active=_SIN_CAMBIO, estado=_SIN_CAMBIO):
    """Etapa 2 (auditoría M10): impide que una operación deje al sistema sin
    ningún Administrador del sistema activo. Debe llamarse dentro de una
    transacción: bloquea las filas de los administradores activos, así dos
    operaciones simultáneas sobre los dos últimos administradores no pueden
    pasar ambas la verificación."""
    from django.db.models import Q

    from .permissions import ROL_ADMIN_SISTEMA

    if not _es_admin_sistema_activo(usuario):
        return

    if _es_admin_sistema_activo(usuario, rol=rol, is_active=is_active, estado=estado):
        return

    candidatos = (
        Usuario.objects
        .select_for_update(of=('self',))
        .select_related('rol')
        .filter(is_active=True, estado=True)
        .filter(Q(rol__nombre__iexact=ROL_ADMIN_SISTEMA) | Q(rol__isnull=True, is_superuser=True))
    )
    otros_activos = [
        candidato for candidato in candidatos
        if candidato.pk != usuario.pk and _es_admin_sistema_activo(candidato)
    ]

    if not otros_activos:
        raise ValidationError({'detail': MENSAJE_ULTIMO_ADMIN_SISTEMA})


class RolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Rol.objects.filter(estado=True).order_by('nombre')
    serializer_class = RolSerializer
    permission_classes = [IsAuthenticated]


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.select_related('rol').order_by('id')
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated, EsAdministradorSistema]

    def perform_create(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        usuario_creado = serializer.save()

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='crear',
            modulo='Usuarios',
            descripcion=f'Creó el usuario {usuario_creado.username}.',
            request=self.request,
        )

    def perform_update(self, serializer):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        estaba_inactivo = (
            serializer.instance.estado is False or serializer.instance.is_active is False
        )

        datos = serializer.validated_data

        with transaction.atomic():
            _validar_continuidad_admin_sistema(
                serializer.instance,
                rol=datos.get('rol', _SIN_CAMBIO),
                is_active=datos.get('is_active', _SIN_CAMBIO),
                estado=datos.get('estado', _SIN_CAMBIO),
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

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='actualizar',
            modulo='Usuarios',
            descripcion=descripcion,
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        usuario = self.get_object()

        if usuario.id == request.user.id:
            return Response(
                {'detail': 'No podés inactivar tu propio usuario desde esta opción.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            _validar_continuidad_admin_sistema(usuario, is_active=False, estado=False)
            usuario.estado = False
            usuario.is_active = False
            usuario.save(update_fields=['estado', 'is_active'])

        registrar_bitacora_obligatoria(
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

        from apps.auditoria.services import registrar_bitacora_obligatoria

        campos = ('first_name', 'last_name', 'correo')
        antes = {campo: getattr(request.user, campo) for campo in campos}

        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()

        # Etapa 4 (M7): el correo identifica la cuenta en la recuperación de
        # acceso; se registra qué campos cambiaron (sin sus valores).
        cambiados = [campo for campo in campos if getattr(usuario, campo) != antes[campo]]

        if cambiados:
            nombres = {'first_name': 'nombre', 'last_name': 'apellido', 'correo': 'correo'}
            registrar_bitacora_obligatoria(
                usuario=usuario,
                accion='actualizar',
                modulo='Perfil',
                descripcion=(
                    f'El usuario {usuario.username} actualizó su perfil: '
                    f'{", ".join(nombres[campo] for campo in cambiados)}.'
                ),
                request=request,
            )

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


class SolicitarRestablecimientoPasswordView(MensajeLimiteIntentosMixin, APIView):
    permission_classes = [AllowAny]
    # Etapa 2 (B2): el límite se cuenta exista o no la cuenta, así que el
    # 429 tampoco revela si existe.
    throttle_classes = [LimiteRestablecimientoPorIP, LimiteRestablecimientoPorIdentificador]

    MENSAJE_GENERICO = (
        'Si la cuenta existe, la solicitud fue enviada para revisión administrativa.'
    )

    def post(self, request):
        from apps.auditoria.services import notificar_administradores, registrar_bitacora_obligatoria

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

                registrar_bitacora_obligatoria(
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


def consulta_bloqueo_solicitud_restablecimiento():
    """Bloquea SOLO la fila de la solicitud (FOR UPDATE OF la tabla propia).

    PostgreSQL no admite FOR UPDATE sobre el lado nulable de un LEFT OUTER
    JOIN: revisado_por y atendido_por son opcionales, así que incluirlos en
    select_related junto con select_for_update() sin `of` provocaba
    NotSupportedError (HTTP 500 al asignar la contraseña temporal). Solo se
    une `usuario` (obligatorio, INNER JOIN), que la acción necesita; el
    revisor y quien atendió se cargan después, sin bloqueo."""
    return SolicitudRestablecimientoPassword.objects.select_for_update(of=('self',)).select_related('usuario')


class SolicitudRestablecimientoPasswordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SolicitudRestablecimientoPassword.objects.select_related(
        'usuario',
        'revisado_por',
        'atendido_por',
    ).all()
    serializer_class = SolicitudRestablecimientoPasswordSerializer
    permission_classes = [IsAuthenticated, EsAdministradorSistema]

    def _bloquear_solicitud(self):
        """Bloquea la fila durante la petición (que es atómica): dos
        aprobaciones, rechazos o asignaciones simultáneas no aplican la misma
        transición dos veces; la segunda ve el estado ya actualizado."""
        solicitud = self.get_object()

        return consulta_bloqueo_solicitud_restablecimiento().get(pk=solicitud.pk)

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        from apps.auditoria.services import registrar_bitacora_obligatoria

        solicitud = self._bloquear_solicitud()

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

        registrar_bitacora_obligatoria(
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
        from apps.auditoria.services import registrar_bitacora_obligatoria

        solicitud = self._bloquear_solicitud()

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

        registrar_bitacora_obligatoria(
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
        from apps.auditoria.services import registrar_bitacora_obligatoria

        solicitud = self._bloquear_solicitud()

        # La aprobación y la asignación son operaciones independientes: la
        # contraseña temporal solo se asigna a una solicitud ya Aprobada, y
        # una sola vez (al asignarla pasa a Atendida).
        if solicitud.estado != 'aprobada':
            mensajes = {
                'pendiente': 'Primero hay que aprobar la solicitud para poder asignar una contraseña temporal.',
                'atendida': 'Esta solicitud ya tiene una contraseña temporal asignada.',
                'rechazada': 'La solicitud fue rechazada: no se puede asignar una contraseña temporal.',
            }
            return Response(
                {'detail': mensajes.get(solicitud.estado, 'La solicitud no admite asignar una contraseña temporal.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password_temporal = request.data.get('password_temporal')

        if not password_temporal:
            return Response(
                {'detail': 'Debe enviar la contraseña temporal.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = solicitud.usuario

        # Etapa 2 (B5): misma política de AUTH_PASSWORD_VALIDATORS que la
        # contraseña definitiva. Los mensajes de Django no incluyen la
        # contraseña ingresada.
        try:
            validate_password(password_temporal, user=usuario)
        except DjangoValidationError as error:
            return Response(
                {'password_temporal': list(error.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario.set_password(password_temporal)
        usuario.debe_cambiar_password = True
        usuario.save(update_fields=['password', 'debe_cambiar_password'])

        ahora = timezone.now()

        solicitud.estado = 'atendida'
        solicitud.atendido_por = request.user
        solicitud.fecha_atencion = ahora
        solicitud.save()

        registrar_bitacora_obligatoria(
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