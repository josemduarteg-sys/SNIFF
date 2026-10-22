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

// D3: aquí había umbrales 70/85 fijos para clasificar promedios agregados
// (claseCumplimientoAgregado), sin uso desde el rediseño del Dashboard. Se
// retiraron: toda clasificación sale de los RangoKPI del backend.

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
