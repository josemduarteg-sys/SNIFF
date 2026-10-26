// Objetivos específicos deshabilitados (pedido de Hernán, 06/10/2026): en la
// interfaz se habla solo de "Objetivo". Un KPI directo está vinculado a un
// objetivo específico implícito cuyo texto es interno; en ese caso se
// muestra su objetivo general. Un KPI vinculado a un objetivo específico
// real (registrado antes) sigue mostrando ese texto.

// Mismo literal que TEXTO_OBJETIVO_ESPECIFICO_DIRECTO en
// backend/apps/estrategia/services.py.
export const TEXTO_OBJETIVO_IMPLICITO = 'KPI directo del objetivo general'

export function esObjetivoImplicito(item) {
  return Boolean(item?.es_directo) || item?.objetivo_especifico_texto === TEXTO_OBJETIVO_IMPLICITO
}

// Texto visible de un ObjetivoEspecifico (filtros): el implícito de un KPI
// directo se muestra con su objetivo general.
export function textoObjetivoEspecifico(objetivo) {
  const implicito = Boolean(objetivo?.es_generado_automaticamente)
    || objetivo?.texto_objetivo === TEXTO_OBJETIVO_IMPLICITO

  return (implicito ? objetivo?.objetivo_general_texto : objetivo?.texto_objetivo)
    || objetivo?.texto_objetivo
    || 'Sin objetivo'
}

export function textoObjetivoKpi(kpi, porDefecto = 'Sin objetivo') {
  if (!kpi) return porDefecto

  if (esObjetivoImplicito(kpi)) {
    return kpi.objetivo_general_texto || kpi.objetivo_especifico_texto || porDefecto
  }

  return kpi.objetivo_especifico_texto || kpi.objetivo_general_texto || porDefecto
}
