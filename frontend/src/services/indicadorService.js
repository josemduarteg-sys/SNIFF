import api from './api'

export async function obtenerIndicadoresKpi() {
  const response = await api.get('indicadores-kpi/')
  return normalizarRespuesta(response)
}

export async function crearIndicador(payload) {
  const response = await api.post('indicadores-kpi/', limpiarPayloadIndicador(payload))
  return response.data
}

export async function actualizarIndicador(id, payload) {
  const response = await api.patch(`indicadores-kpi/${id}/`, limpiarPayloadIndicador(payload))
  return response.data
}

export async function obtenerObjetivos() {
  const response = await api.get('objetivos/')
  return normalizarRespuesta(response)
}

export async function obtenerEstrategias() {
  const response = await api.get('estrategias/')
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
    estrategias,
    objetivos,
    frecuencias,
    tiposCalculo,
    fuentesDato,
  ] = await Promise.all([
    obtenerEstrategias(),
    obtenerObjetivos(),
    obtenerFrecuencias(),
    obtenerTiposCalculo(),
    obtenerFuentesDato(),
  ])

  return {
    estrategias,
    objetivos,
    frecuencias,
    tiposCalculo,
    fuentesDato,
  }
}

export async function obtenerRangosKpi() {
  const response = await api.get('rangos-kpi/')
  return normalizarRespuesta(response)
}

export async function autorizarIndicador(id) {
  const response = await api.post(`indicadores-kpi/${id}/autorizar/`)
  return response.data
}

export async function anularIndicador(id) {
  const response = await api.post(`indicadores-kpi/${id}/anular/`)
  return response.data
}

function limpiarPayloadIndicador(payload) {
  return {
    objetivo: payload.objetivo,
    frecuencia: payload.frecuencia,
    tipo_calculo: payload.tipo_calculo,
    fuente_dato: payload.fuente_dato,
    nombre: payload.nombre,
    descripcion: payload.descripcion || '',
    unidad_medida: payload.unidad_medida,
    valor_meta: payload.valor_meta,
    fecha_inicio: payload.fecha_inicio,
    fecha_fin: payload.fecha_fin,
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