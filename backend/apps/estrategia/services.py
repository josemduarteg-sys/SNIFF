"""Reglas reutilizables de inmutabilidad ligadas al Plan estratégico.

Este módulo es el ÚNICO lugar que debe decidir si un elemento que depende
de un Plan estratégico puede modificarse. En el Bloque 1 se usa con
PlanEstrategico y ObjetivoGeneral; en bloques futuros (Plan anual, Objetivo
específico, KPI, Medición) el mismo helper debe reutilizarse en vez de
copiar esta validación en cada serializer.
"""


def plan_estrategico_esta_cerrado(plan_estrategico):
    """True si el Plan estratégico (o None) está en estado Cerrado.

    Acepta None para que pueda usarse directamente sobre relaciones
    opcionales sin que cada llamador tenga que chequear null primero.
    """
    if plan_estrategico is None:
        return False

    return plan_estrategico.esta_cerrado()


def plan_estrategico_esta_en_uso(plan_estrategico):
    if plan_estrategico is None:
        return False

    return plan_estrategico.esta_en_uso()


def plan_anual_esta_bloqueado(plan_anual):
    """True si el PlanAnual (o None) no admite modificaciones: porque él
    mismo está Cerrado, o porque su Plan estratégico padre está Cerrado
    (este último tiene prioridad absoluta sobre su descendencia, incluso
    si el propio PlanAnual quedó históricamente en otro estado)."""
    if plan_anual is None:
        return False

    if plan_anual.esta_cerrado():
        return True

    return plan_estrategico_esta_cerrado(plan_anual.plan_estrategico)


def objetivo_especifico_esta_bloqueado(objetivo_especifico):
    """True si el ObjetivoEspecifico (o None) no admite modificaciones:
    delega por completo en el bloqueo de su PlanAnual (que a su vez ya
    contempla el estado del Plan estratégico)."""
    if objetivo_especifico is None:
        return False

    return plan_anual_esta_bloqueado(objetivo_especifico.plan_anual)


TEXTO_OBJETIVO_ESPECIFICO_DIRECTO = 'KPI directo del objetivo general'
"""Único lugar donde vive este literal (Bloque 3, KPI directo): lo usa
tanto la creación/reutilización del objetivo específico implícito como
cualquier código que necesite reconocer ese texto (no se duplica el
literal en otro archivo)."""


def obtener_o_crear_objetivo_especifico_directo(plan_anual, objetivo_general, usuario):
    """Obtiene (o crea) el ObjetivoEspecifico 'implícito' que reutilizan los
    KPI directos (Bloque 3, punto 2): uno por cada combinación
    (plan_anual, objetivo_general), nunca uno por KPI.

    El llamador (IndicadorKPISerializer.validate) ya debe haber validado
    que plan_anual/objetivo_general pertenecen al mismo Plan estratégico y
    que el Plan anual admite creación de KPI — esta función no repite esas
    reglas de negocio, solo resuelve el registro interno.

    Protegido contra condiciones de carrera por la UniqueConstraint
    'unique_objetivo_especifico_implicito' (DB), no solo por get_or_create:
    si dos requests concurrentes intentan crear el mismo implícito, la que
    pierde la carrera atrapa el IntegrityError y relee la fila que la otra
    ya insertó.
    """
    from django.db import IntegrityError, transaction
    from .models import ObjetivoEspecifico

    existente = ObjetivoEspecifico.objects.filter(
        plan_anual=plan_anual,
        objetivo_general=objetivo_general,
        es_generado_automaticamente=True,
    ).first()

    if existente:
        return existente

    try:
        with transaction.atomic():
            return ObjetivoEspecifico.objects.create(
                plan_anual=plan_anual,
                objetivo_general=objetivo_general,
                texto_objetivo=TEXTO_OBJETIVO_ESPECIFICO_DIRECTO,
                es_generado_automaticamente=True,
                creado_por=usuario,
            )
    except IntegrityError:
        return ObjetivoEspecifico.objects.get(
            plan_anual=plan_anual,
            objetivo_general=objetivo_general,
            es_generado_automaticamente=True,
        )


def resumen_ponderacion_anual(objetivo_general, excluir_id=None):
    """Suma de PonderacionAnualObjetivoGeneral ya configuradas para un
    ObjetivoGeneral (regla 1/2/3 confirmada por Hernán: el 100% de su
    cumplimiento estratégico se distribuye entre los años de su Plan
    estratégico). `excluir_id` permite calcular "cuánto hay en los DEMÁS
    años" al validar que una fila nueva o editada no haga superar el 100%.

    Una distribución incompleta (suma < 100) es un estado válido "en
    preparación" (no un error): solo se informa cuánto falta, nunca se
    completa ni se pondera automáticamente."""
    from decimal import Decimal

    from .models import PonderacionAnualObjetivoGeneral

    ponderaciones = PonderacionAnualObjetivoGeneral.objects.filter(
        objetivo_general=objetivo_general,
    )

    if excluir_id is not None:
        ponderaciones = ponderaciones.exclude(id=excluir_id)

    total_asignado = sum(
        (p.porcentaje for p in ponderaciones), Decimal('0')
    )

    return {
        'total_asignado': total_asignado,
        'pendiente': Decimal('100') - total_asignado,
        'completo': total_asignado == Decimal('100'),
    }
