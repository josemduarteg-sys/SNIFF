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

// D2: evidencias múltiples. Cada archivo se consulta por su id; nada se
// reemplaza ni se elimina.
export function obtenerUrlArchivoEvidencia(medicionId, evidenciaId, modo = 'ver') {
  return `mediciones/${medicionId}/evidencias/${evidenciaId}/${modo}/`
}

export async function descargarEvidencia(medicionId, evidenciaId) {
  const response = await api.get(obtenerUrlArchivoEvidencia(medicionId, evidenciaId, 'ver'), {
    responseType: 'blob',
  })

  return response.data
}

export async function descargarArchivoEvidencia(medicionId, evidenciaId) {
  const response = await api.get(obtenerUrlArchivoEvidencia(medicionId, evidenciaId, 'descargar'), {
    responseType: 'blob',
  })

  return response.data
}

// «Agregar evidencia»: suma 1 a 10 archivos a una medición ya registrada.
export async function agregarEvidencias(medicionId, archivos) {
  const formData = new FormData()
  archivos.forEach((archivo) => formData.append('archivos', archivo))

  const response = await api.post(`mediciones/${medicionId}/evidencias/`, formData, {
    headers: { 'Content-Type': undefined },
  })

  return response.data
}

// Construye el FormData que se envía como multipart/form-data (Bloque 4:
// la evidencia es un archivo real, no texto).
function construirFormData(payload, { incluirIndicador }) {
  const formData = new FormData()

  if (incluirIndicador) {
    formData.append('indicador', payload.indicador)
  }

  formData.append('valor_resultado', payload.valor_resultado)
  formData.append('observacion', payload.observacion || '')

  // D2: los archivos se agregan a las evidencias anteriores (nunca las
  // reemplazan).
  ;(payload.archivos_evidencia || []).forEach((archivo) => {
    if (archivo instanceof File) formData.append('archivos_evidencia', archivo)
  })

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

// D5 (Reportes): historial de un KPI, en orden cronológico (solo lectura).
export async function obtenerMedicionesKpi(indicadorId) {
  const response = await api.get('mediciones/', { params: { indicador: indicadorId } })
  return normalizarRespuesta(response)
}
