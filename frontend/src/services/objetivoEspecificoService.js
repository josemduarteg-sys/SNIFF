import api from './api'

export async function obtenerObjetivosEspecificos() {
  const response = await api.get('objetivos-especificos/')
  return normalizarRespuesta(response)
}

export async function obtenerPlanesAnualesParaObjetivoEspecifico() {
  const response = await api.get('planes-anuales/')
  return normalizarRespuesta(response)
}

export async function obtenerObjetivosGeneralesParaObjetivoEspecifico() {
  const response = await api.get('objetivos-generales/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioObjetivoEspecifico() {
  const [planesAnuales, objetivosGenerales] = await Promise.all([
    obtenerPlanesAnualesParaObjetivoEspecifico(),
    obtenerObjetivosGeneralesParaObjetivoEspecifico(),
  ])

  // Solo se pueden crear objetivos específicos dentro de un Plan anual En
  // uso (la validación real está en backend, ver ObjetivoEspecificoSerializer).
  const planesAnualesEnUso = planesAnuales.filter((plan) => plan.estado === 'en_uso')

  return {
    planesAnuales: planesAnualesEnUso,
    objetivosGenerales,
  }
}

export async function crearObjetivoEspecifico(payload) {
  const response = await api.post(
    'objetivos-especificos/',
    limpiarPayloadObjetivoEspecifico(payload)
  )
  return response.data
}

export async function actualizarObjetivoEspecifico(id, payload) {
  const response = await api.patch(
    `objetivos-especificos/${id}/`,
    limpiarPayloadObjetivoEspecifico(payload)
  )
  return response.data
}

function limpiarPayloadObjetivoEspecifico(payload) {
  return {
    plan_anual: payload.plan_anual,
    objetivo_general: payload.objetivo_general,
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
