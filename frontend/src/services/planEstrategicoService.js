import api from './api'

export async function obtenerPlanesEstrategicos() {
  const response = await api.get('planes-estrategicos/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioPlanEstrategico() {
  // El Plan estratégico ya no depende de Área; se mantiene la función para
  // no romper el patrón de carga en paralelo que usa la vista, por si el
  // formulario necesita datos auxiliares más adelante.
  return {}
}

export async function crearPlanEstrategico(payload) {
  const response = await api.post('planes-estrategicos/', limpiarPayloadPlanEstrategico(payload))
  return response.data
}

export async function actualizarPlanEstrategico(id, payload) {
  const response = await api.patch(`planes-estrategicos/${id}/`, limpiarPayloadPlanEstrategico(payload))
  return response.data
}

export async function ponerEnUsoPlanEstrategico(id) {
  const response = await api.post(`planes-estrategicos/${id}/poner-en-uso/`)
  return response.data
}

export async function cerrarPlanEstrategico(id) {
  const response = await api.post(`planes-estrategicos/${id}/cerrar/`)
  return response.data
}

function limpiarPayloadPlanEstrategico(payload) {
  return {
    titulo: payload.titulo,
    descripcion: payload.descripcion || '',
    fecha_inicio: payload.fecha_inicio || null,
    fecha_fin: payload.fecha_fin || null,
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
