import api from './api'

export async function obtenerMediciones() {
  const response = await api.get('mediciones/')
  return normalizarRespuesta(response)
}

export async function obtenerIndicadoresKpi() {
  const response = await api.get('indicadores-kpi/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioMedicion() {
  const indicadores = await obtenerIndicadoresKpi()

  // Solo KPI autorizados son elegibles para medición (ver también la
  // validación equivalente y autoritativa en backend:
  // MedicionSerializer.validate / obtener_info_siguiente_periodo).
  const indicadoresAutorizados = indicadores.filter((indicador) => indicador.estado === 'autorizado')

  return {
    indicadores: indicadoresAutorizados,
  }
}

export async function obtenerSiguientePeriodo(indicadorId) {
  const response = await api.get('mediciones/siguiente-periodo/', {
    params: {
      indicador: indicadorId,
    },
  })

  return response.data
}

export async function crearMedicion(payload) {
  const formData = construirFormData(payload, { incluirIndicador: true })

  const response = await api.post('mediciones/', formData, {
    headers: { 'Content-Type': undefined },
  })

  return response.data
}

export async function actualizarMedicion(id, payload) {
  const formData = construirFormData(payload, { incluirIndicador: false })

  const response = await api.patch(`mediciones/${id}/`, formData, {
    headers: { 'Content-Type': undefined },
  })

  return response.data
}

export function obtenerUrlEvidencia(id) {
  return `mediciones/${id}/evidencia/`
}

export function obtenerUrlDescargaEvidencia(id) {
  return `mediciones/${id}/evidencia/descargar/`
}

export async function descargarEvidencia(id) {
  const response = await api.get(obtenerUrlEvidencia(id), {
    responseType: 'blob',
  })

  return response.data
}

export async function descargarArchivoEvidencia(id) {
  const response = await api.get(obtenerUrlDescargaEvidencia(id), {
    responseType: 'blob',
  })

  return response.data
}

// Construye el FormData que se envía como multipart/form-data (Bloque 4:
// la evidencia ahora es un archivo real, no texto). Solo se agrega
// `evidencia` cuando el usuario efectivamente seleccionó un archivo nuevo,
// para no pisar sin querer una evidencia ya guardada al editar.
function construirFormData(payload, { incluirIndicador }) {
  const formData = new FormData()

  if (incluirIndicador) {
    formData.append('indicador', payload.indicador)
  }

  formData.append('valor_resultado', payload.valor_resultado)
  formData.append('observacion', payload.observacion || '')

  if (payload.evidencia instanceof File) {
    formData.append('evidencia', payload.evidencia)
  }

  return formData
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
