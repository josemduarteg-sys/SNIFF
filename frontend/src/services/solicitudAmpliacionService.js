import api from './api'

// Etapa 5: solicitudes de días adicionales para registrar mediciones.

export async function obtenerSolicitudesAmpliacion(params = {}) {
  const response = await api.get('solicitudes-ampliacion/', { params })
  return Array.isArray(response.data) ? response.data : response.data?.results || []
}

export async function crearSolicitudAmpliacion(payload) {
  const response = await api.post('solicitudes-ampliacion/', payload)
  return response.data
}

export async function autorizarSolicitudAmpliacion(id, payload) {
  const response = await api.post(`solicitudes-ampliacion/${id}/autorizar/`, payload)
  return response.data
}

export async function rechazarSolicitudAmpliacion(id, payload) {
  const response = await api.post(`solicitudes-ampliacion/${id}/rechazar/`, payload)
  return response.data
}

export async function retirarSolicitudAmpliacion(id) {
  const response = await api.post(`solicitudes-ampliacion/${id}/retirar/`)
  return response.data
}
