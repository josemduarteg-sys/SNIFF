import api from './api'

// Bloque 3, segunda parte (ponderaciones): porcentaje del cumplimiento
// estratégico de un objetivo general que le corresponde a cada año de su
// Plan estratégico (reglas 1/2/3 confirmadas por Hernán).

export async function obtenerPonderacionesAnuales() {
  const response = await api.get('ponderaciones-anuales/')
  return normalizarRespuesta(response)
}

export async function crearPonderacionAnual(payload) {
  const response = await api.post('ponderaciones-anuales/', limpiarPayload(payload))
  return response.data
}

export async function actualizarPonderacionAnual(id, payload) {
  const response = await api.patch(`ponderaciones-anuales/${id}/`, limpiarPayload(payload))
  return response.data
}

function limpiarPayload(payload) {
  return {
    objetivo_general: payload.objetivo_general,
    plan_anual: payload.plan_anual,
    porcentaje: payload.porcentaje,
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
