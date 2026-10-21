import api from './api'

export async function obtenerAlertas() {
  const response = await api.get('alertas/')
  return normalizarRespuesta(response)
}

// Etapa 4 (M6): el backend filtra las pendientes y excluye las de KPI
// anulados o de planes Cerrados (siguen guardadas como historial).
export async function obtenerAlertasPendientes() {
  const response = await api.get('alertas/', {
    params: { estado_alerta: 'pendiente', vigentes: 1 },
  })
  return normalizarRespuesta(response).filter((alerta) => alerta.estado_alerta === 'pendiente')
}

// Etapa 6: alerta citada en el enlace de una notificación.
export async function obtenerAlerta(id) {
  const response = await api.get(`alertas/${id}/`)
  return response.data
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
