import api from './api'

export async function obtenerMediciones() {
  const response = await api.get('mediciones/')
  return normalizarRespuesta(response)
}

export async function obtenerIndicadoresKpi() {
  const response = await api.get('indicadores-kpi/')
  return normalizarRespuesta(response)
}

export async function obtenerEstadosCumplimiento() {
  const response = await api.get('estados-cumplimiento/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioMedicion() {
  const [indicadores, estadosCumplimiento] = await Promise.all([
    obtenerIndicadoresKpi(),
    obtenerEstadosCumplimiento(),
  ])

  const indicadoresAutorizados = indicadores.filter((indicador) => {
    return (
      indicador.estado === 'autorizado' &&
      indicador.valor_meta &&
      indicador.fecha_inicio &&
      indicador.fecha_fin
    )
  })

  return {
    indicadores: indicadoresAutorizados,
    estadosCumplimiento,
  }
}

export async function crearMedicion(payload) {
  const response = await api.post('mediciones/', limpiarPayloadMedicion(payload))
  return response.data
}

export async function actualizarMedicion(id, payload) {
  const response = await api.patch(`mediciones/${id}/`, limpiarPayloadMedicion(payload))
  return response.data
}

export async function eliminarMedicion(id) {
  const response = await api.delete(`mediciones/${id}/`)
  return response.data
}

export async function obtenerSiguientePeriodo(indicadorId) {
  const response = await api.get('mediciones/siguiente-periodo/', {
    params: {
      indicador: indicadorId,
    },
  })

  return response.data
}

/*
  Estas funciones quedan solo para compatibilidad temporal.
  La lógica nueva ya no usa meta ni periodo manual desde frontend.
*/
export async function obtenerMetasKpi() {
  return []
}

export async function obtenerPeriodosMedicion() {
  return []
}

function limpiarPayloadMedicion(payload) {
  return {
    indicador: payload.indicador,
    mes_medicion: payload.mes_medicion,
    valor_resultado: payload.valor_resultado,
    observacion: payload.observacion || '',
    evidencia: payload.evidencia || '',
  }
}

function normalizarRespuesta(response) {
  if (Array.isArray(response.data)) {
    return response.data
  }

  if (Array.isArray(response.data?.results)) {
    return response.data.results
  }

  return []
}
