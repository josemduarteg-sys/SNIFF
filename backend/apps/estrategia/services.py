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
