import api from './api'

export async function obtenerPerfil() {
  const response = await api.get('usuarios/me/')
  return response.data
}

export async function actualizarPerfil(datos) {
  const response = await api.patch('usuarios/me/', datos)
  return response.data
}

export async function cambiarPassword(datos) {
  const response = await api.post('usuarios/cambiar-password/', datos)
  return response.data
}

export async function obtenerUsuarios() {
  const response = await api.get('usuarios/')
  return normalizarRespuesta(response)
}

export async function obtenerRoles() {
  const response = await api.get('roles/')
  return normalizarRespuesta(response)
}

export async function crearUsuario(datos) {
  const response = await api.post('usuarios/', datos)
  return response.data
}

export async function actualizarUsuario(id, datos) {
  const response = await api.patch(`usuarios/${id}/`, datos)
  return response.data
}

export async function inactivarUsuario(id) {
  const response = await api.delete(`usuarios/${id}/`)
  return response.data
}

function normalizarRespuesta(response) {
  if (Array.isArray(response.data)) {
    return response.data
  }

  if (Array.isArray(response.data.results)) {
    return response.data.results
  }

  return []
}