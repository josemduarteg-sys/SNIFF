import api from './api'

export async function obtenerBitacora() {
  const { data } = await api.get('bitacora/')
  return data
}
