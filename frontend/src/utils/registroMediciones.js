// Registro de mediciones: el selector del formulario muestra solo los KPI
// que hoy tienen un periodo disponible para registrar (pedido de Hernán,
// reunión del 06/10/2026: "que le aparezcan solo los que tocan"). La regla
// real la decide el backend (obtener_info_siguiente_periodo, expuesta como
// periodo_disponible, que ya considera las ampliaciones autorizadas) y la
// vuelve a validar al guardar.

// periodo_disponible no mira si el plan está Cerrado (eso lo valida aparte
// IndicadorKPI.esta_bloqueado() al guardar); se excluyen acá con la misma
// regla para no ofrecer un KPI que el backend luego rechazaría.
export function kpiDePlanAbierto(indicador) {
  return indicador?.plan_anual_estado !== 'cerrado' && indicador?.plan_estrategico_estado !== 'cerrado'
}

export function kpisDisponiblesParaRegistro(indicadores) {
  return (indicadores || []).filter(
    (indicador) => indicador.estado === 'autorizado'
      && indicador.periodo_disponible === true
      && kpiDePlanAbierto(indicador),
  )
}

export const MENSAJE_SIN_KPI_DISPONIBLES =
  'Ningún KPI tiene hoy un periodo disponible para registrar. Cada periodo se habilita desde su fecha ' +
  'de cierre y hasta el fin de su plazo de registro.'

// Filtro "Estado del periodo" del listado: los EstadoCumplimiento que de
// verdad tienen las mediciones cargadas (incluido "Sin registro" de las
// omisiones). Es la clasificación de cada medición contra los rangos de su
// KPI; no el estado acumulado del KPI. Antes se esperaba un catálogo que
// obtenerDatosFormularioMedicion() nunca devolvía, y solo quedaba "Todos".
export function estadosDelPeriodo(mediciones, textoEstado = (nombre) => nombre) {
  const vistos = new Map()

  ;(mediciones || []).forEach((medicion) => {
    const id = medicion.estado_cumplimiento

    if (id === null || id === undefined || vistos.has(id)) return

    vistos.set(id, { id, nombre: textoEstado(medicion.estado_cumplimiento_nombre) || `Estado ${id}` })
  })

  return [...vistos.values()].sort((a, b) => a.nombre.localeCompare(b.nombre))
}
