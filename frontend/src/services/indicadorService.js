import api from './api'

export async function obtenerIndicadoresKpi() {
  const response = await api.get('indicadores-kpi/')
  return normalizarRespuesta(response)
}

export async function obtenerObjetivos() {
  const response = await api.get('objetivos/')
  return normalizarRespuesta(response)
}

export async function obtenerFrecuencias() {
  const response = await api.get('frecuencias/')
  return normalizarRespuesta(response)
}

export async function obtenerTiposCalculo() {
  const response = await api.get('tipos-calculo/')
  return normalizarRespuesta(response)
}

export async function obtenerFuentesDato() {
  const response = await api.get('fuentes-dato/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioIndicador() {
  const [
    objetivos,
    frecuencias,
    tiposCalculo,
    fuentesDato,
  ] = await Promise.all([
    obtenerObjetivos(),
    obtenerFrecuencias(),
    obtenerTiposCalculo(),
    obtenerFuentesDato(),
  ])

  return {
    objetivos,
    frecuencias,
    tiposCalculo,
    fuentesDato,
  }
}

export async function autorizarIndicador(id) {
  const response = await api.post(`indicadores-kpi/${id}/autorizar/`)
  return response.data
}

export async function anularIndicador(id) {
  const response = await api.post(`indicadores-kpi/${id}/anular/`)
  return response.data
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