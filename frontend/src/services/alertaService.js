import api from './api'

export async function obtenerAlertas() {
  const response = await api.get('alertas/')
  return normalizarRespuesta(response)
}

export async function obtenerAlertasPendientes() {
  const alertas = await obtenerAlertas()
  return alertas.filter((alerta) => alerta.estado_alerta === 'pendiente')
}

export async function marcarAlertaRevisada(id) {
  const response = await api.post(`alertas/${id}/marcar-revisada/`)
  return response.data
}

export async function marcarTodasAlertasRevisadas() {
  const response = await api.post('alertas/marcar-todas-revisadas/')
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
