import api from './api'

export async function obtenerSolicitudesRestablecimiento() {
  const { data } = await api.get('solicitudes-restablecimiento/')
  return data
}

export async function aprobarSolicitudRestablecimiento(id, payload = {}) {
  const { data } = await api.post(`solicitudes-restablecimiento/${id}/aprobar/`, payload)
  return data
}

export async function rechazarSolicitudRestablecimiento(id, payload = {}) {
  const { data } = await api.post(`solicitudes-restablecimiento/${id}/rechazar/`, payload)
  return data
}

export async function asignarPasswordTemporal(id, payload) {
  const { data } = await api.post(
    `solicitudes-restablecimiento/${id}/asignar-password-temporal/`,
    payload
  )
  return data
}
