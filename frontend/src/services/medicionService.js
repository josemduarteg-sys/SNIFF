import api from './api'

export async function obtenerMediciones() {
  const response = await api.get('mediciones/')
  return normalizarRespuesta(response)
}

export async function obtenerIndicadoresKpi() {
  const response = await api.get('indicadores-kpi/')
  return normalizarRespuesta(response)
}

export async function obtenerMetasKpi() {
  const response = await api.get('metas-kpi/')
  return normalizarRespuesta(response)
}

export async function obtenerPeriodosMedicion() {
  const response = await api.get('periodos-medicion/')
  return normalizarRespuesta(response)
}

export async function obtenerEstadosCumplimiento() {
  const response = await api.get('estados-cumplimiento/')
  return normalizarRespuesta(response)
}

export async function crearMedicion(datos) {
  const response = await api.post('mediciones/', datos)
  return response.data
}

export async function actualizarMedicion(id, datos) {
  const response = await api.patch(`mediciones/${id}/`, datos)
  return response.data
}

export async function obtenerDatosFormularioMedicion() {
  const [indicadores, metas, periodos, estadosCumplimiento] = await Promise.all([
    obtenerIndicadoresKpi(),
    obtenerMetasKpi(),
    obtenerPeriodosMedicion(),
    obtenerEstadosCumplimiento(),
  ])

  return {
    indicadores,
    metas,
    periodos,
    estadosCumplimiento,
  }
}

function normalizarRespuesta(response) {
  if (Array.isArray(response.data)) {
    return response.data
  }

  if (Array.isArray(response.data.results)) {
    return response.data.results
  }

  return []
}