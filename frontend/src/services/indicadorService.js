import api from './api'

export async function obtenerIndicadoresKpi() {
  const response = await api.get('indicadores-kpi/')
  return normalizarRespuesta(response)
}

export async function crearIndicador(payload) {
  const response = await api.post('indicadores-kpi/', limpiarPayloadIndicador(payload))
  return response.data
}

export async function actualizarIndicador(id, payload) {
  const response = await api.patch(`indicadores-kpi/${id}/`, limpiarPayloadIndicador(payload))
  return response.data
}

// Bloque 3, segunda parte (ponderaciones): a diferencia de
// actualizarIndicador, este PATCH envía ÚNICAMENTE el campo ponderación —
// necesario para un KPI ya autorizado, donde el resto de campos quedan
// bloqueados (ver IndicadorKPISerializer.validate) y limpiarPayloadIndicador
// los reenviaría igual (con valores por defecto como '' o null que
// pisarían datos existentes), disparando ese bloqueo sin motivo.
export async function actualizarPonderacionIndicador(id, ponderacion) {
  const response = await api.patch(`indicadores-kpi/${id}/`, {
    ponderacion: ponderacion === '' || ponderacion === undefined ? null : ponderacion,
  })
  return response.data
}

export async function obtenerPlanesAnualesParaIndicador() {
  const response = await api.get('planes-anuales/')
  return normalizarRespuesta(response)
}

export async function obtenerObjetivosEspecificosParaIndicador() {
  const response = await api.get('objetivos-especificos/')
  return normalizarRespuesta(response)
}

export async function obtenerObjetivosGeneralesParaIndicador() {
  const response = await api.get('objetivos-generales/')
  return normalizarRespuesta(response)
}

export async function obtenerFrecuencias() {
  const response = await api.get('frecuencias/')
  return normalizarRespuesta(response)
}

export async function obtenerDatosFormularioIndicador() {
  const [planesAnuales, objetivosGenerales, objetivosEspecificos, frecuencias] = await Promise.all([
    obtenerPlanesAnualesParaIndicador(),
    obtenerObjetivosGeneralesParaIndicador(),
    obtenerObjetivosEspecificosParaIndicador(),
    obtenerFrecuencias(),
  ])

  // Solo se pueden crear/reasociar KPI sobre un Plan anual En uso (ver
  // también la validación equivalente y autoritativa en backend:
  // IndicadorKPISerializer.validate). El listado de objetivos específicos
  // que llega acá ya excluye los "implícitos" de KPI directos (Bloque 3):
  // el backend los filtra en ObjetivoEspecificoViewSet.queryset.
  const planesAnualesEnUso = planesAnuales.filter((plan) => plan.estado === 'en_uso')

  return {
    planesAnuales: planesAnualesEnUso,
    objetivosGenerales,
    objetivosEspecificos,
    frecuencias,
  }
}

export async function obtenerRangosKpi() {
  const response = await api.get('rangos-kpi/')
  return normalizarRespuesta(response)
}

export async function obtenerEstadosCumplimiento() {
  const response = await api.get('estados-cumplimiento/')
  return normalizarRespuesta(response)
}

export async function autorizarIndicador(id) {
  const response = await api.post(`indicadores-kpi/${id}/autorizar/`)
  return response.data
}

export async function anularIndicador(id) {
  const response = await api.post(`indicadores-kpi/${id}/anular/`)
  return response.data
}

function limpiarPayloadIndicador(payload) {
  return {
    // Bloque 3 (KPI directo): objetivo_especifico es opcional. plan_anual
    // y objetivo_general siempre se envían: el backend los usa para
    // resolver/crear el objetivo específico implícito cuando no se eligió
    // uno real, y para validar que el objetivo específico elegido (si lo
    // hay) pertenezca a esa misma combinación.
    plan_anual: payload.plan_anual,
    objetivo_general: payload.objetivo_general,
    objetivo_especifico: payload.objetivo_especifico || null,
    frecuencia: payload.frecuencia,
    nombre: payload.nombre,
    descripcion: payload.descripcion || '',
    formula_medicion: payload.formula_medicion,
    unidad_medida: payload.unidad_medida,
    valor_meta: payload.valor_meta,
    ponderacion: payload.ponderacion === '' || payload.ponderacion === undefined ? null : payload.ponderacion,
  }
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
