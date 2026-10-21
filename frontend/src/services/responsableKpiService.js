import api from './api'

// Etapa 4 (auditoría M6): responsables (Ejecutores operativos) de cada KPI.
// Los gestiona el Administrador de planificación; el backend valida rol,
// estado del usuario y estado del KPI.

export async function obtenerResponsablesKpi(indicadorId) {
  const response = await api.get('responsables-kpi/', { params: { indicador: indicadorId } })
  return normalizarRespuesta(response)
}

export async function obtenerCandidatosResponsable() {
  const response = await api.get('responsables-kpi/candidatos/')
  return Array.isArray(response.data) ? response.data : []
}

// Crea la asignación o reactiva una anterior del mismo usuario (sin duplicarla).
export async function asignarResponsableKpi(indicadorId, usuarioId) {
  const response = await api.post('responsables-kpi/', { indicador: indicadorId, usuario: usuarioId })
  return response.data
}

export async function desactivarResponsableKpi(id) {
  const response = await api.patch(`responsables-kpi/${id}/`, { estado: false })
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
