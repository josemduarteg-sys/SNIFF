// Etapa 6 (M12): filtros del Dashboard por Plan estratégico y Plan anual.
// Un único punto decide qué planes, KPI, mediciones y alertas forman el
// contexto seleccionado; todos los bloques del Dashboard parten de él, así
// que nunca mezclan información de planes distintos.
// Ajuste visual de la entrega: se suma el año del plan anual (selector
// "Plan anual: 2026" de la referencia aprobada), sincronizado con los otros
// dos filtros. Un año puede tener varios planes anuales (uno por Plan
// estratégico): el año los incluye a todos, y los otros filtros acotan.

export function aId(valor) {
  const numero = Number(valor)
  return Number.isInteger(numero) && numero > 0 ? numero : null
}

// Años con al menos un plan anual real, del más reciente al más antiguo.
export function aniosDisponibles(planesAnuales) {
  return [...new Set(planesAnuales.map((plan) => Number(plan.anio)).filter((anio) => Number.isInteger(anio) && anio > 0))]
    .sort((a, b) => b - a)
}

// Normaliza la selección contra los planes existentes: descarta ids o años
// que no existen, completa el Plan estratégico y el año a partir del Plan
// anual, y descarta un Plan anual que no pertenece al Plan estratégico.
export function normalizarSeleccion(seleccion, planesEstrategicos, planesAnuales) {
  let planEstrategico = aId(seleccion?.planEstrategico)
  let planAnual = aId(seleccion?.planAnual)
  let anio = aId(seleccion?.anio)

  if (planEstrategico && !planesEstrategicos.some((plan) => plan.id === planEstrategico)) {
    planEstrategico = null
  }

  if (anio && !aniosDisponibles(planesAnuales).includes(anio)) {
    anio = null
  }

  const anual = planAnual ? planesAnuales.find((plan) => plan.id === planAnual) : null

  if (!anual) {
    planAnual = null
  } else if (planEstrategico && Number(anual.plan_estrategico) !== planEstrategico) {
    planAnual = null
  } else {
    // El plan anual es la selección más específica: define su plan y su año.
    planEstrategico = Number(anual.plan_estrategico)
    anio = Number(anual.anio) || anio
  }

  return { planEstrategico, planAnual, anio }
}

export function planesAnualesDe(planesAnuales, planEstrategico, anio = null) {
  return planesAnuales.filter((plan) => {
    if (planEstrategico && Number(plan.plan_estrategico) !== Number(planEstrategico)) return false
    if (anio && Number(plan.anio) !== Number(anio)) return false
    return true
  })
}

export function filtrarContexto(datos, seleccion) {
  const { planEstrategico, planAnual, anio = null } = seleccion

  const planesAnuales = planAnual
    ? datos.planesAnuales.filter((plan) => plan.id === planAnual)
    : planesAnualesDe(datos.planesAnuales, planEstrategico, anio)

  let planesEstrategicos = planEstrategico
    ? datos.planesEstrategicos.filter((plan) => plan.id === planEstrategico)
    : datos.planesEstrategicos

  // Con un año elegido, solo cuentan los planes estratégicos que tienen un
  // plan anual de ese año.
  if (anio && !planEstrategico) {
    const conPlanDelAnio = new Set(planesAnuales.map((plan) => Number(plan.plan_estrategico)))
    planesEstrategicos = planesEstrategicos.filter((plan) => conPlanDelAnio.has(plan.id))
  }

  const idsPlanesAnuales = new Set(planesAnuales.map((plan) => plan.id))

  const indicadores = datos.indicadores.filter((kpi) => {
    if (planEstrategico && Number(kpi.plan_estrategico) !== planEstrategico) return false
    if (planAnual && Number(kpi.plan_anual) !== planAnual) return false
    if (anio && !idsPlanesAnuales.has(Number(kpi.plan_anual))) return false
    return true
  })

  const idsKpi = new Set(indicadores.map((kpi) => kpi.id))

  return {
    planesEstrategicos,
    planesAnuales,
    indicadores,
    mediciones: datos.mediciones.filter((medicion) => idsKpi.has(medicion.indicador)),
    alertas: datos.alertas.filter((alerta) => idsKpi.has(alerta.indicador)),
  }
}

export function descripcionContexto(seleccion, planesEstrategicos, planesAnuales) {
  const plan = planesEstrategicos.find((item) => item.id === seleccion.planEstrategico)
  const anual = planesAnuales.find((item) => item.id === seleccion.planAnual)
  const anio = seleccion.anio

  if (anual) return `${anual.nombre} · Plan estratégico ${plan?.titulo || anual.plan_estrategico_titulo || ''}`.trim()
  if (plan && anio) return `Plan estratégico ${plan.titulo} · año ${anio}`
  if (plan) return `Plan estratégico ${plan.titulo} (todos sus planes anuales)`
  if (anio) return `Todos los planes del año ${anio}`

  return `Todos los planes (${planesEstrategicos.length} planes estratégicos)`
}
