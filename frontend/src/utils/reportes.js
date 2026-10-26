// D5: consulta histórica de KPI (Reportes). Solo lectura y solo datos reales:
// las mediciones son las que devuelve la API (incluidas las omisiones
// "Sin registro" que el sistema ya cerró); nunca se inventan periodos ni
// resultados.
import { claseColorCumplimiento, esMedicionSinRegistro } from './cumplimiento.js'

// Vigencia: la misma regla que IndicadorKPI.esta_bloqueado() en backend —
// un KPI deja de estar vigente cuando su Plan anual o su Plan estratégico
// están Cerrados (el Cerrado del estratégico congela toda su descendencia).
// No se usan las fechas: los datos de demostración con fechas pasadas
// siguen vigentes mientras sus planes no se cierren.
export function kpiVigente(kpi) {
  return kpi?.plan_anual_estado !== 'cerrado' && kpi?.plan_estrategico_estado !== 'cerrado'
}

// Por defecto solo KPI vigentes; con incluirCerrados también los de planes
// cerrados (consulta histórica). Siempre solo KPI autorizados.
export function kpisConsultables(kpis, { incluirCerrados = false } = {}) {
  return (kpis || []).filter((kpi) => kpi.estado === 'autorizado' && (incluirCerrados || kpiVigente(kpi)))
}

function opcionesUnicas(lista, clave, etiqueta, claveEstado) {
  const vistos = new Map()

  lista.forEach((item) => {
    const id = item[clave]
    if (id === null || id === undefined || vistos.has(id)) return
    const cerrado = item[claveEstado] === 'cerrado'
    vistos.set(id, { id, nombre: `${item[etiqueta] || `#${id}`}${cerrado ? ' (Cerrado)' : ''}` })
  })

  return [...vistos.values()].sort((a, b) => String(a.nombre).localeCompare(String(b.nombre)))
}

export function planesEstrategicosDe(kpis) {
  return opcionesUnicas(kpis, 'plan_estrategico', 'plan_estrategico_titulo', 'plan_estrategico_estado')
}

export function planesAnualesDe(kpis, planEstrategicoId) {
  const filtrados = planEstrategicoId
    ? kpis.filter((kpi) => Number(kpi.plan_estrategico) === Number(planEstrategicoId))
    : kpis

  return opcionesUnicas(filtrados, 'plan_anual', 'plan_anual_nombre', 'plan_anual_estado')
}

export function kpisDe(kpis, planEstrategicoId, planAnualId) {
  return kpis
    .filter((kpi) => !planEstrategicoId || Number(kpi.plan_estrategico) === Number(planEstrategicoId))
    .filter((kpi) => !planAnualId || Number(kpi.plan_anual) === Number(planAnualId))
    .sort((a, b) => a.nombre.localeCompare(b.nombre))
}

// Ajusta la selección para que los tres filtros sean coherentes: un plan
// anual que no pertenece al plan estratégico, o un KPI fuera de ambos, se
// limpian.
export function normalizarSeleccion(kpis, seleccion) {
  let { planEstrategico, planAnual, kpi } = seleccion

  if (planEstrategico && !planesEstrategicosDe(kpis).some((p) => Number(p.id) === Number(planEstrategico))) {
    planEstrategico = ''
  }

  if (planAnual && !planesAnualesDe(kpis, planEstrategico).some((p) => Number(p.id) === Number(planAnual))) {
    planAnual = ''
  }

  if (kpi && !kpisDe(kpis, planEstrategico, planAnual).some((k) => Number(k.id) === Number(kpi))) {
    kpi = ''
  }

  return { planEstrategico, planAnual, kpi }
}

// Orden cronológico por fin del periodo (fecha_medicion es el cierre real
// del periodo, según su frecuencia).
export function ordenarCronologicamente(mediciones) {
  return [...(mediciones || [])].sort((a, b) => {
    const fechaA = a.fecha_medicion || ''
    const fechaB = b.fecha_medicion || ''
    return fechaA.localeCompare(fechaB) || a.id - b.id
  })
}

function numeroONulo(valor) {
  if (valor === null || valor === undefined || valor === '') return null
  const numero = Number(valor)
  return Number.isFinite(numero) ? numero : null
}

// Un punto por medición existente. Las omisiones quedan con valor null:
// la gráfica las marca aparte y corta la línea (nunca se dibujan como 0).
export function serieHistorica(mediciones) {
  return ordenarCronologicamente(mediciones).map((medicion) => {
    const sinRegistro = esMedicionSinRegistro(medicion)

    return {
      id: medicion.id,
      etiqueta: medicion.periodo_nombre || '-',
      valor: sinRegistro ? null : numeroONulo(medicion.valor_resultado),
      meta: numeroONulo(medicion.valor_meta),
      sinRegistro,
      estado: medicion.estado_cumplimiento_nombre || '',
      clase: sinRegistro ? 'neutral' : claseColorCumplimiento(medicion.estado_cumplimiento_color),
    }
  })
}

// Tramos continuos de puntos con resultado: una omisión corta la línea.
export function tramosConResultado(serie) {
  const tramos = []
  let actual = []

  serie.forEach((punto, indice) => {
    if (punto.valor === null) {
      if (actual.length) tramos.push(actual)
      actual = []
      return
    }

    actual.push({ ...punto, indice })
  })

  if (actual.length) tramos.push(actual)
  return tramos
}

function pasoRedondo(bruto) {
  const potencia = 10 ** Math.floor(Math.log10(bruto))
  const fraccion = bruto / potencia
  const redondo = fraccion <= 1 ? 1 : fraccion <= 2 ? 2 : fraccion <= 2.5 ? 2.5 : fraccion <= 5 ? 5 : 10
  return redondo * potencia
}

// Eje vertical en la unidad real del KPI. Porcentaje: 0 a 100. Otras
// unidades: de 0 a un máximo redondo por encima del mayor resultado o meta.
export function escalaVertical(serie, unidad) {
  if (unidad === '%') {
    return { minimo: 0, maximo: 100, marcas: [0, 25, 50, 75, 100] }
  }

  const valores = serie.flatMap((p) => [p.valor, p.meta]).filter((v) => v !== null)
  const mayor = Math.max(0, ...valores)

  if (mayor === 0) {
    return { minimo: 0, maximo: 1, marcas: [0, 0.25, 0.5, 0.75, 1] }
  }

  const paso = pasoRedondo(mayor / 4)
  const maximo = Math.ceil((mayor * 1.05) / paso) * paso
  const marcas = []

  for (let marca = 0; marca <= maximo + paso / 2; marca += paso) {
    marcas.push(Number(marca.toPrecision(12)))
  }

  return { minimo: 0, maximo, marcas }
}
