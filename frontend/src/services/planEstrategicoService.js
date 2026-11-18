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
  // PATCH debe conservar la ausencia de campos bloqueados: omitir una
  // fecha no equivale a solicitar que se borre con null.
  const limpio = {}
  for (const campo of ['titulo', 'descripcion', 'fecha_inicio', 'fecha_fin']) {
    if (Object.hasOwn(payload, campo)) {
      limpio[campo] = campo.startsWith('fecha_')
        ? payload[campo] || null
        : campo === 'descripcion' ? payload[campo] || '' : payload[campo]
    }
  }
  return limpio
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
