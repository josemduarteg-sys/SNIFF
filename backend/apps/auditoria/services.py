from django.db.models import Q

from .models import Bitacora, Notificacion


def obtener_ip_usuario(request):
    if not request:
        return None

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def registrar_bitacora(usuario, accion, modulo, descripcion, request=None):
    ip_usuario = obtener_ip_usuario(request)

    return Bitacora.objects.create(
        usuario=usuario,
        accion=accion,
        modulo=modulo,
        descripcion=descripcion,
        ip_usuario=ip_usuario,
    )


def crear_notificacion(usuario_destino, tipo, titulo, mensaje, enlace=None):
    if usuario_destino is None:
        return None

    return Notificacion.objects.create(
        usuario_destino=usuario_destino,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        enlace=enlace,
    )


def notificar_administradores(tipo, titulo, mensaje, enlace=None):
    from apps.usuarios.models import Usuario

    administradores = Usuario.objects.filter(
        Q(rol__nombre__iexact='administrador') | Q(rol__nombre__iexact='admin'),
        is_active=True,
    )

    notificaciones = []

    for administrador in administradores:
        notificacion = crear_notificacion(
            usuario_destino=administrador,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            enlace=enlace,
        )

        if notificacion:
            notificaciones.append(notificacion)

    return notificaciones


def notificar_usuarios_gestion(tipo, titulo, mensaje, enlace=None, excluir_usuario=None):
    from apps.usuarios.models import Usuario
    from apps.usuarios.permissions import es_administrador, es_operativo_o_supervisor

    usuarios_activos = Usuario.objects.filter(is_active=True).select_related('rol')

    notificaciones = []

    for usuario in usuarios_activos:
        if excluir_usuario and usuario.id == excluir_usuario.id:
            continue

        if not (es_administrador(usuario) or es_operativo_o_supervisor(usuario)):
            continue

        notificacion = crear_notificacion(
            usuario_destino=usuario,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            enlace=enlace,
        )

        if notificacion:
            notificaciones.append(notificacion)

    return notificaciones