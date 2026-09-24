import api from './api'

export async function obtenerObjetivosGenerales() {
  const response = await api.get('objetivos-generales/')
  return normalizarRespuesta(response)
}

export async function obtenerPlanesEstrategicosParaObjetivo() {
  const response = await api.get('planes-estrategicos/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioObjetivoGeneral() {
  const [planes] = await Promise.all([
    obtenerPlanesEstrategicosParaObjetivo(),
  ])

  // Solo se pueden crear objetivos generales sobre planes En uso (ver
  // también la validación equivalente en backend, que es la que realmente
  // protege esta regla).
  const planesEnUso = planes.filter((plan) => plan.estado === 'en_uso')

  return {
    planes: planesEnUso,
  }
}

export async function crearObjetivoGeneral(payload) {
  const response = await api.post('objetivos-generales/', limpiarPayloadObjetivoGeneral(payload))
  return response.data
}

export async function actualizarObjetivoGeneral(id, payload) {
  const response = await api.patch(`objetivos-generales/${id}/`, limpiarPayloadObjetivoGeneral(payload))
  return response.data
}

function limpiarPayloadObjetivoGeneral(payload) {
  return {
    plan_estrategico: payload.plan_estrategico,
    texto_objetivo: payload.texto_objetivo,
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
