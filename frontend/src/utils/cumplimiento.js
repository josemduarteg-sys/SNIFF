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

// ============================================================
// Etapa 3 (auditoría C3): omisiones "Sin registro".
//
// Un periodo que venció sin que nadie registrara un resultado queda como
// medición "Sin registro" (valor_resultado null, sin_registro true). No es
// un resultado del KPI: no entra en el promedio ni se clasifica con los
// rangos. Sustituye el criterio anterior de mostrar toda omisión como 0.00.
// ============================================================

export const SIN_REGISTRO = 'Sin registro'
export const SIN_MEDICIONES = 'Sin mediciones'

export function esMedicionSinRegistro(medicion) {
  return medicion?.sin_registro === true
}

/**
 * Categoría gerencial de un KPI a partir de los campos del backend:
 * - con resultados reales: su estado acumulado (o "Pendiente de
 *   actualización" si ningún rango cubre el promedio);
 * - sin resultados pero con omisiones: "Sin registro";
 * - sin nada todavía: "Sin mediciones".
 */
export function categoriaKpi(kpi) {
  if (!kpi?.cantidad_mediciones) {
    return kpi?.cantidad_omisiones ? SIN_REGISTRO : SIN_MEDICIONES
  }

  return kpi.estado_acumulado_nombre || 'Pendiente de actualización'
}

/** Estado acumulado "hasta esta medición" (evolución mensual). */
export function categoriaAcumuladaMedicion(medicion) {
  if (medicion?.estado_acumulado_hasta_medicion_nombre) {
    return medicion.estado_acumulado_hasta_medicion_nombre
  }

  return esMedicionSinRegistro(medicion) ? SIN_REGISTRO : null
}

export function textoOmisiones(cantidad) {
  const total = Number(cantidad) || 0

  if (!total) {
    return ''
  }

  return total === 1 ? '1 periodo sin registro' : `${total} periodos sin registro`
}
