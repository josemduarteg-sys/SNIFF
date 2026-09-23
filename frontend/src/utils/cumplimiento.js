const MAPA_COLOR_CLASE = {
  verde: 'ok',
  amarillo: 'warning',
  rojo: 'danger',
  gris: 'neutral',
}

/**
 * Traduce el color real de EstadoCumplimiento (guardado en backend, vía
 * RangoKPI) a la clase CSS ya usada en la interfaz. Es la única fuente de
 * verdad del color visual: nunca recalcular verde/amarillo/rojo a partir
 * de un umbral fijo en frontend.
 */
export function claseColorCumplimiento(color) {
  return MAPA_COLOR_CLASE[(color || '').toLowerCase().trim()] || 'neutral'
}

/**
 * Traduce el nombre real de EstadoCumplimiento a un texto visible. El
 * backend usa internamente "Pendiente de actualización" cuando el KPI no
 * tiene un RangoKPI aplicable; ese valor interno no se toca, pero en toda
 * la interfaz debe verse como "Sin criterio de cumplimiento configurado"
 * (no como un estado de revisión/aprobación, que el sistema no tiene).
 */
export function textoEstadoCumplimiento(estado) {
  if (!estado) {
    return 'Sin criterio de cumplimiento configurado'
  }

  const texto = estado.toLowerCase()

  if (texto.includes('pendiente')) {
    return 'Sin criterio de cumplimiento configurado'
  }

  return estado
}

// Criterio PROVISIONAL para clasificar valores agregados (promedios). Único
// lugar donde vive 85/70 para este propósito — si el cliente valida otros
// valores, cambiar solo acá.
const UMBRAL_FAVORABLE_AGREGADO = 85
const UMBRAL_RIESGO_AGREGADO = 70

/**
 * Clasifica visualmente un porcentaje AGREGADO (promedio por estrategia,
 * promedio por periodo en "Evolución de mediciones", etc.) según el
 * criterio provisional de cumplimiento.
 *
 * SOLO para presentación de promedios del Panel de control. Nunca usar para
 * clasificar una medición real: esas siempre obtienen su estado desde
 * RangoKPI/EstadoCumplimiento en backend (ver claseColorCumplimiento). No
 * escribe ni sobrescribe nada en base de datos.
 */
export function claseCumplimientoAgregado(valor) {
  const numero = Number(valor)

  if (Number.isNaN(numero)) {
    return 'neutral'
  }

  if (numero >= UMBRAL_FAVORABLE_AGREGADO) {
    return 'ok'
  }

  if (numero >= UMBRAL_RIESGO_AGREGADO) {
    return 'warning'
  }

  return 'danger'
}

const TEXTO_POR_CLASE_AGREGADO = {
  ok: 'Favorable',
  warning: 'En riesgo',
  danger: 'Incumplido',
  neutral: 'Sin datos',
}

/**
 * Texto visible correspondiente a la clasificación de un porcentaje
 * agregado (ver claseCumplimientoAgregado). Mismo criterio provisional,
 * un solo lugar.
 */
export function textoCumplimientoAgregado(valor) {
  return TEXTO_POR_CLASE_AGREGADO[claseCumplimientoAgregado(valor)]
}
