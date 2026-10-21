// Registro de mediciones: el selector del formulario muestra solo los KPI
// que hoy tienen un periodo disponible para registrar (pedido de Hernán,
// reunión del 06/10/2026: "que le aparezcan solo los que tocan"). La regla
// real la decide el backend (obtener_info_siguiente_periodo, expuesta como
// periodo_disponible, que ya considera las ampliaciones autorizadas) y la
// vuelve a validar al guardar.

export function kpisDisponiblesParaRegistro(indicadores) {
  return (indicadores || []).filter(
    (indicador) => indicador.estado === 'autorizado' && indicador.periodo_disponible === true,
  )
}

export const MENSAJE_SIN_KPI_DISPONIBLES =
  'Ningún KPI tiene hoy un periodo disponible para registrar. Cada periodo se habilita desde su fecha ' +
  'de cierre y hasta el fin de su plazo de registro.'
