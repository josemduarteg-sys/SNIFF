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
