from .models import Bitacora


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