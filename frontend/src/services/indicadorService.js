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

export async function obtenerPlanesAnualesParaIndicador() {
  const response = await api.get('planes-anuales/')
  return normalizarRespuesta(response)
}

export async function obtenerObjetivosEspecificosParaIndicador() {
  const response = await api.get('objetivos-especificos/')
  return normalizarRespuesta(response)
}

export async function obtenerFrecuencias() {
  const response = await api.get('frecuencias/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioIndicador() {
  const [planesAnuales, objetivosEspecificos, frecuencias] = await Promise.all([
    obtenerPlanesAnualesParaIndicador(),
    obtenerObjetivosEspecificosParaIndicador(),
    obtenerFrecuencias(),
  ])

  // Solo se pueden crear/reasociar KPI sobre un Plan anual En uso (ver
  // también la validación equivalente y autoritativa en backend:
  // IndicadorKPISerializer.validate).
  const planesAnualesEnUso = planesAnuales.filter((plan) => plan.estado === 'en_uso')

  return {
    planesAnuales: planesAnualesEnUso,
    objetivosEspecificos,
    frecuencias,
  }
}

export async function obtenerRangosKpi() {
  const response = await api.get('rangos-kpi/')
  return normalizarRespuesta(response)
}

export async function obtenerEstadosCumplimiento() {
  const response = await api.get('estados-cumplimiento/')
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
    objetivo_especifico: payload.objetivo_especifico,
    frecuencia: payload.frecuencia,
    nombre: payload.nombre,
    descripcion: payload.descripcion || '',
    formula_medicion: payload.formula_medicion,
    unidad_medida: payload.unidad_medida,
    valor_meta: payload.valor_meta,
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
