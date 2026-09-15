import api from './api'

export async function obtenerAreas() {
  const response = await api.get('areas/')
  return normalizarRespuesta(response)
}

export async function crearArea(payload) {
  const response = await api.post('areas/', limpiarPayloadArea(payload))
  return response.data
}

export async function actualizarArea(id, payload) {
  const response = await api.patch(`areas/${id}/`, limpiarPayloadArea(payload))
  return response.data
}

export async function activarArea(id) {
  const response = await api.patch(`areas/${id}/`, {
    estado: true,
  })

  return response.data
}

export async function inactivarArea(id) {
  const response = await api.patch(`areas/${id}/`, {
    estado: false,
  })

  return response.data
}

function limpiarPayloadArea(payload) {
  return {
    nombre: payload.nombre?.trim(),
    descripcion: payload.descripcion?.trim() || '',
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
