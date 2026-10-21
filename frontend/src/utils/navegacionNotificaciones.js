// Etapa 6: enlaces de las notificaciones hacia Mediciones
// (/mediciones?indicador=X&alerta=Y). Solo se aceptan ids enteros
// positivos; cualquier otro valor se informa como enlace no válido en lugar
// de usarse.

function leerId(valor) {
  if (valor === undefined || valor === null || valor === '') return { presente: false, id: null }

  const texto = Array.isArray(valor) ? valor[0] : valor
  const valido = /^\d+$/.test(String(texto)) && Number(texto) > 0

  return { presente: true, id: valido ? Number(texto) : null }
}

export function leerParametrosNotificacion(query = {}) {
  const indicador = leerId(query.indicador)
  const alerta = leerId(query.alerta)

  return {
    indicador: indicador.id,
    alerta: alerta.id,
    hayParametros: indicador.presente || alerta.presente,
    invalidos: (indicador.presente && !indicador.id) || (alerta.presente && !alerta.id),
  }
}

// El KPI del enlace solo se aplica como filtro si figura entre los datos que
// el usuario ya puede ver (KPI disponibles o mediciones listadas).
export function kpiDisponible(indicadorId, indicadores, mediciones) {
  if (!indicadorId) return false

  return (
    indicadores.some((kpi) => Number(kpi.id) === indicadorId) ||
    mediciones.some((medicion) => Number(medicion.indicador) === indicadorId)
  )
}

// La alerta del enlace solo se muestra si corresponde al KPI del enlace.
export function alertaCorresponde(alerta, indicadorId) {
  if (!alerta) return false
  if (!indicadorId) return true

  return Number(alerta.indicador) === indicadorId
}
