import api from './api'

export async function obtenerNotificaciones() {
  const response = await api.get('notificaciones/')
  return normalizarRespuesta(response)
}

export async function obtenerNotificacionesNoLeidas() {
  const notificaciones = await obtenerNotificaciones()
  return notificaciones.filter((notificacion) => !notificacion.leida)
}

export async function marcarNotificacionLeida(id) {
  const response = await api.patch(`notificaciones/${id}/marcar-leida/`)
  return response.data
}

export async function marcarTodasNotificacionesLeidas() {
  const response = await api.post('notificaciones/marcar-todas-leidas/')
  return response.data
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
