import logging

from django.db.models import Q

from .models import Bitacora, Notificacion

logger = logging.getLogger(__name__)


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


def registrar_bitacora_seguro(usuario, accion, modulo, descripcion, request=None):
    """Igual que registrar_bitacora, pero nunca interrumpe la acción principal
    si el registro falla — solo lo deja loggeado."""
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


def generar_recordatorios_pendientes(fecha_referencia=None):
    from django.utils import timezone

    from apps.estrategia.models import PlanEstrategico
    from apps.indicadores.models import IndicadorKPI
    from apps.usuarios.models import Usuario
    from apps.usuarios.permissions import es_administrador, es_operativo_o_supervisor

    fecha_referencia = fecha_referencia or timezone.localdate()

    destinatarios = [
        usuario
        for usuario in Usuario.objects.filter(is_active=True).select_related('rol')
        if es_administrador(usuario) or es_operativo_o_supervisor(usuario)
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