import api from './api'

export async function obtenerObjetivos() {
  const response = await api.get('objetivos/')
  return normalizarRespuesta(response)
}

export async function obtenerEstrategiasParaObjetivo() {
  const response = await api.get('estrategias/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioObjetivo() {
  const [estrategias] = await Promise.all([
    obtenerEstrategiasParaObjetivo(),
  ])

  return {
    estrategias,
  }
}

export async function crearObjetivo(payload) {
  const response = await api.post('objetivos/', limpiarPayloadObjetivo(payload))
  return response.data
}

export async function actualizarObjetivo(id, payload) {
  const response = await api.patch(`objetivos/${id}/`, limpiarPayloadObjetivo(payload))
  return response.data
}

export async function activarObjetivo(id) {
  const response = await api.post(`objetivos/${id}/activar/`)
  return response.data
}

export async function finalizarObjetivo(id) {
  const response = await api.post(`objetivos/${id}/finalizar/`)
  return response.data
}

export async function inactivarObjetivo(id) {
  const response = await api.post(`objetivos/${id}/inactivar/`)
  return response.data
}

function limpiarPayloadObjetivo(payload) {
  return {
    estrategia: payload.estrategia,
    nombre: payload.nombre,
    descripcion: payload.descripcion || '',
    fecha_inicio: payload.fecha_inicio || null,
    fecha_fin: payload.fecha_fin || null,
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
