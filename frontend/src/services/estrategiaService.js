import api from './api'

export async function obtenerEstrategias() {
  const response = await api.get('estrategias/')
  return normalizarRespuesta(response)
}

export async function obtenerAreas() {
  const response = await api.get('areas/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioEstrategia() {
  const [areas] = await Promise.all([
    obtenerAreas(),
  ])

  return {
    areas,
  }
}

export async function crearEstrategia(payload) {
  const response = await api.post('estrategias/', limpiarPayloadEstrategia(payload))
  return response.data
}

export async function actualizarEstrategia(id, payload) {
  const response = await api.patch(`estrategias/${id}/`, limpiarPayloadEstrategia(payload))
  return response.data
}

export async function inactivarEstrategia(id) {
  const response = await api.patch(`estrategias/${id}/`, {
    estado: 'inactiva',
  })

  return response.data
}

export async function reactivarEstrategia(id) {
  const response = await api.patch(`estrategias/${id}/`, {
    estado: 'activa',
  })

  return response.data
}

function limpiarPayloadEstrategia(payload) {
  return {
    area: payload.area,
    nombre: payload.nombre,
    descripcion: payload.descripcion || '',
    fecha_inicio: payload.fecha_inicio || null,
    fecha_fin: payload.fecha_fin || null,
    estado: payload.estado || 'activa',
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
