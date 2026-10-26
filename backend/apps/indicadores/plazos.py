"""Vencimientos por fecha de INICIO del período, independientes del reloj.

Oportunidad conserva sus umbrales calendario (0, 1–2, 3+), pendientes
de validación funcional; no deben confundirse con los días hábiles.
"""
from datetime import date, timedelta

INICIO_REGLA_HABIL = date(2026, 11, 1)
DIAS_ORDINARIOS = 5
DIAS_TOTALES = 10


def usa_dias_habiles(inicio):
    return inicio is not None and inicio >= INICIO_REGLA_HABIL


def sumar_dias(fecha, dias, habiles=False):
    if not habiles:
        return fecha + timedelta(days=dias)
    if dias < 0:
        raise ValueError("Los días deben ser no negativos.")
    while dias:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:
            dias -= 1
    return fecha


def limite_ordinario(cierre, inicio=None, dias_calendario=5):
    habiles = usa_dias_habiles(inicio)
    return sumar_dias(cierre, DIAS_ORDINARIOS if habiles else dias_calendario, habiles)


def maximo_adicional(inicio):
    return 5 if usa_dias_habiles(inicio) else 10


def limite_maximo(cierre, ordinario, inicio):
    if usa_dias_habiles(inicio):
        return sumar_dias(cierre, DIAS_TOTALES, True)
    return sumar_dias(ordinario, 10)


def limite_ampliado(ordinario, dias, inicio):
    return sumar_dias(ordinario, dias, usa_dias_habiles(inicio))


def minimo_autorizable(ordinario, referencia, inicio):
    if not usa_dias_habiles(inicio):
        return max(1, (referencia - ordinario).days)
    # Buscar la primera fecha vigente también cuando hoy es sábado/domingo.
    for dias in range(1, maximo_adicional(inicio) + 1):
        if limite_ampliado(ordinario, dias, inicio) >= referencia:
            return dias
    return maximo_adicional(inicio) + 1
