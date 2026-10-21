import ipaddress
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle

from .models import Bitacora, Notificacion

logger = logging.getLogger(__name__)


class BitacoraNoDisponible(APIException):
    """Etapa 4 (auditoría M7): la operación no puede quedar sin su registro
    de auditoría. Como cada petición es atómica (ATOMIC_REQUESTS), al
    lanzarse se revierte TODO lo que la petición había guardado: no queda
    una operación a medias y reintentar es seguro."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = (
        'No se pudo registrar la operación en la bitácora, así que no se guardó '
        'ningún cambio. Intentá nuevamente en unos minutos.'
    )
    default_code = 'bitacora_no_disponible'


def obtener_ip_usuario(request):
    """Etapa 4 (auditoría M7): mismo criterio que los límites de intentos de
    la Etapa 2 (SimpleRateThrottle.get_ident, que respeta
    REST_FRAMEWORK['NUM_PROXIES']). Con 0 proxies usa REMOTE_ADDR e ignora
    X-Forwarded-For, que el cliente puede falsificar; detrás de N proxies de
    confianza toma la dirección que agregó el más cercano. Si el valor no es
    una IP válida, se guarda vacío en lugar de un texto arbitrario."""
    if not request:
        return None

    ident = BaseThrottle().get_ident(request)

    try:
        return str(ipaddress.ip_address((ident or '').strip()))
    except ValueError:
        return None


def registrar_bitacora(usuario, accion, modulo, descripcion, request=None):
    # Etapa 4 (M7): una acción de usuario siempre lleva un usuario real. Los
    # eventos del sistema usan registrar_bitacora_sistema().
    if usuario is None or getattr(usuario, 'pk', None) is None:
        raise ValueError('Una acción de usuario requiere un usuario válido para la bitácora.')

    ip_usuario = obtener_ip_usuario(request)

    return Bitacora.objects.create(
        usuario=usuario,
        accion=accion,
        modulo=modulo,
        descripcion=descripcion,
        ip_usuario=ip_usuario,
    )


def registrar_bitacora_sistema(accion, modulo, descripcion):
    """Etapa 4 (auditoría M7): evento ejecutado automáticamente por el sistema
    (tareas programadas). Queda con usuario NULL y sin IP, y se muestra como
    "Sistema". Lanza la excepción si no puede guardarse: el llamador decide
    cómo informarlo (ver registrar_ejecucion_tarea_automatica)."""
    return Bitacora.objects.create(
        usuario=None,
        accion=accion,
        modulo=modulo,
        descripcion=descripcion,
        ip_usuario=None,
    )


MODULO_TAREAS_AUTOMATICAS = 'Tareas automáticas'


def registrar_ejecucion_tarea_automatica(nombre_tarea, resumen, con_errores=False):
    """Registra en bitácora una ejecución REAL de una tarea automática (las
    simulaciones no llaman a esta función). Si el registro falla, lanza
    CommandError con constancia de que las operaciones de la tarea YA
    quedaron confirmadas: no se revierten ni se repiten."""
    from django.core.management.base import CommandError

    try:
        with transaction.atomic():
            registrar_bitacora_sistema(
                accion='error' if con_errores else 'actualizar',
                modulo=MODULO_TAREAS_AUTOMATICAS,
                descripcion=f'{nombre_tarea}: {resumen}',
            )
    except Exception as error:
        logger.exception('No se pudo registrar en bitácora la ejecución de %s.', nombre_tarea)
        raise CommandError(
            f'La tarea "{nombre_tarea}" terminó y sus operaciones ya quedaron guardadas '
            f'({resumen}), pero no se pudo registrar su ejecución en la bitácora: {error}. '
            'No se revirtió ni se repitió nada; revisá la bitácora y el log del servidor.'
        ) from error


def registrar_bitacora_obligatoria(usuario, accion, modulo, descripcion, request=None):
    """Etapa 4 (auditoría M7): registro de bitácora de una operación hecha en
    una petición. Si falla, lanza BitacoraNoDisponible (503) y la petición
    completa se revierte (ATOMIC_REQUESTS): nunca queda guardada una
    operación sin su registro, ni el usuario ve un 500.

    Se ejecuta en un savepoint propio para que un error de base de datos
    no deje rota la transacción de la petición."""
    if usuario is None or getattr(usuario, 'pk', None) is None:
        # Error de programación, no una caída de la bitácora: no se disfraza de 503.
        raise ValueError('Una acción de usuario requiere un usuario válido para la bitácora.')

    try:
        with transaction.atomic():
            return registrar_bitacora(
                usuario=usuario,
                accion=accion,
                modulo=modulo,
                descripcion=descripcion,
                request=request,
            )
    except Exception as error:
        logger.exception(
            'No se pudo registrar en bitácora (usuario=%s, accion=%s, modulo=%s); '
            'la operación se revierte.',
            getattr(usuario, 'username', usuario),
            accion,
            modulo,
        )
        raise BitacoraNoDisponible() from error


def registrar_bitacora_seguro(usuario, accion, modulo, descripcion, request=None):
    """Igual que registrar_bitacora, pero nunca interrumpe la acción principal
    si el registro falla — solo lo deja loggeado.

    Etapa 4: ya no se usa dentro de peticiones (ahí se usa
    registrar_bitacora_obligatoria). Queda solo para procesos fuera de una
    petición donde perder el registro sea preferible a detener el proceso."""
    try:
        return registrar_bitacora(
            usuario=usuario,
            accion=accion,
            modulo=modulo,
            descripcion=descripcion,
            request=request,
        )
    except Exception:
        logger.exception(
            'No se pudo registrar en bitácora (usuario=%s, accion=%s, modulo=%s).',
            getattr(usuario, 'username', usuario),
            accion,
            modulo,
        )
        return None


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
    from apps.usuarios.permissions import es_administrador_sistema

    # Bug detectado tras el Bloque 2: esta consulta seguía buscando
    # literalmente rol__nombre 'administrador'/'admin', nombres que la
    # migración usuarios.0003_adaptar_roles_bloque2_hernan ya había
    # renombrado a 'Administrador del sistema'. Como resultado, dejó de
    # coincidir con cualquier usuario real y las solicitudes de
    # restablecimiento (el único llamador de esta función) quedaron sin
    # notificar a nadie. Se reemplaza por el mismo helper centralizado que
    # ya usa apps/usuarios/permissions.py, para que exista un único lugar
    # que decida quién es "Administrador del sistema".
    administradores = [
        usuario
        for usuario in Usuario.objects.filter(is_active=True).select_related('rol')
        if es_administrador_sistema(usuario)
    ]

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


def generar_recordatorios_pendientes(fecha_referencia=None):
    from django.utils import timezone

    from apps.estrategia.models import PlanEstrategico
    from apps.indicadores.models import IndicadorKPI
    from apps.usuarios.models import Usuario
    from apps.usuarios.permissions import es_administrador_planificacion

    fecha_referencia = fecha_referencia or timezone.localdate()

    # Bloque 2: "pendiente de formalizarse" (Plan estratégico en Borrador,
    # KPI pendiente de autorización) es exclusivamente dominio de
    # Administrador de planificación — Administrador del sistema ya no
    # gestiona planificación, y Ejecutor operativo nunca lo hizo.
    destinatarios = [
        usuario
        for usuario in Usuario.objects.filter(is_active=True).select_related('rol')
        if es_administrador_planificacion(usuario)
    ]

    elementos = []

    # Antes (Bloque 0): recordaba Estrategia/Objetivo con estado='en_revision'.
    # Ese estado ya no existe en el nuevo modelo Borrador/En uso/Cerrado.
    # El equivalente funcional más cercano de "pendiente de formalizarse" es
    # un Plan estratégico que sigue en Borrador — se mantiene el mecanismo,
    # solo se adapta el estado que consulta.
    # ObjetivoGeneral ya no tiene ningún campo de estado propio (su ciclo de
    # vida lo gobierna el Plan estratégico al que pertenece), así que no
    # existe una condición equivalente para él: se retiró ese recordatorio
    # sin reemplazarlo por ninguna regla nueva no confirmada.
    for plan in PlanEstrategico.objects.filter(estado=PlanEstrategico.ESTADO_BORRADOR):
        elementos.append({
            'tipo': 'recordatorio_plan_estrategico_borrador',
            'titulo': 'Plan estratégico pendiente de poner En uso',
            'mensaje': f'El Plan estratégico "{plan.titulo}" continúa en Borrador.',
            'enlace': f'/planes-estrategicos?resaltar={plan.id}',
            'nombre': plan.titulo,
        })

    for indicador in IndicadorKPI.objects.filter(estado='borrador'):
        elementos.append({
            'tipo': 'recordatorio_kpi_borrador',
            'titulo': 'KPI pendiente de autorización',
            'mensaje': f'El KPI "{indicador.nombre}" continúa pendiente de autorización.',
            'enlace': f'/indicadores?resaltar={indicador.id}',
            'nombre': indicador.nombre,
        })

    total_creadas = 0
    total_omitidas = 0
    detalle = []

    for elemento in elementos:
        for destinatario in destinatarios:
            ya_existe = Notificacion.objects.filter(
                usuario_destino=destinatario,
                tipo=elemento['tipo'],
                enlace=elemento['enlace'],
                fecha_creacion__date=fecha_referencia,
            ).exists()

            if ya_existe:
                total_omitidas += 1
                detalle.append({
                    'usuario': destinatario.username,
                    'tipo': elemento['tipo'],
                    'elemento': elemento['nombre'],
                    'accion': 'omitida',
                })
                continue

            crear_notificacion(
                usuario_destino=destinatario,
                tipo=elemento['tipo'],
                titulo=elemento['titulo'],
                mensaje=elemento['mensaje'],
                enlace=elemento['enlace'],
            )

            total_creadas += 1
            detalle.append({
                'usuario': destinatario.username,
                'tipo': elemento['tipo'],
                'elemento': elemento['nombre'],
                'accion': 'creada',
            })

    return {
        'revisados': len(elementos),
        'creadas': total_creadas,
        'omitidas': total_omitidas,
        'detalle': detalle,
    }


def notificar_usuarios_gestion(tipo, titulo, mensaje, enlace=None, excluir_usuario=None):
    from apps.usuarios.models import Usuario
    from apps.usuarios.permissions import es_administrador_planificacion

    usuarios_activos = Usuario.objects.filter(is_active=True).select_related('rol')

    notificaciones = []

    # Bloque 2: todos los llamadores de esta función notifican la creación
    # de un Plan/Objetivo/KPI — dominio exclusivo de Administrador de
    # planificación bajo los 4 roles definitivos.
    for usuario in usuarios_activos:
        if excluir_usuario and usuario.id == excluir_usuario.id:
            continue

        if not es_administrador_planificacion(usuario):
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