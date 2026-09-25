import api from './api'

export async function obtenerPlanesAnuales() {
  const response = await api.get('planes-anuales/')
  return normalizarRespuesta(response)
}

export async function obtenerPlanesEstrategicosParaPlanAnual() {
  const response = await api.get('planes-estrategicos/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioPlanAnual() {
  const planes = await obtenerPlanesEstrategicosParaPlanAnual()

  // Solo se pueden crear planes anuales sobre un Plan estratégico En uso
  // (la validación real está en backend; esto es solo para no ofrecer
  // opciones que el backend va a rechazar).
  const planesEnUso = planes.filter((plan) => plan.estado === 'en_uso')

  return {
    planes: planesEnUso,
  }
}

export async function crearPlanAnual(payload) {
  const response = await api.post('planes-anuales/', limpiarPayloadPlanAnual(payload))
  return response.data
}

export async function actualizarPlanAnual(id, payload) {
  const response = await api.patch(`planes-anuales/${id}/`, limpiarPayloadPlanAnual(payload))
  return response.data
}

export async function ponerEnUsoPlanAnual(id) {
  const response = await api.post(`planes-anuales/${id}/poner-en-uso/`)
  return response.data
}

export async function cerrarPlanAnual(id) {
  const response = await api.post(`planes-anuales/${id}/cerrar/`)
  return response.data
}

function limpiarPayloadPlanAnual(payload) {
  return {
    plan_estrategico: payload.plan_estrategico,
    anio: payload.anio,
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
