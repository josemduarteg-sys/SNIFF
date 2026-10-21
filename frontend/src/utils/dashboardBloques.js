// Bloque B de la entrega: datos de los bloques del Dashboard aprobado por
// Hernán. Solo agrupa y cuenta lo que ya calcula el backend; no fabrica
// porcentajes ni cambia ninguna clasificación.

import {
  OPORTUNIDAD_A_TIEMPO,
  OPORTUNIDAD_CON_AMPLIACION,
  OPORTUNIDAD_CON_RETRASO,
  categoriaOportunidad,
} from './ampliaciones.js'

// Código corto con el formato de la referencia aprobada ("KPI-09"), derivado
// del id real del KPI: no es un dato nuevo ni se guarda.
export function codigoKpi(kpi) {
  return `KPI-${String(kpi.id).padStart(2, '0')}`
}

// Nombre resumido para debajo de una barra; el completo va en el tooltip.
export function nombreCorto(nombre, maximo = 22) {
  const texto = String(nombre || '').trim()
  return texto.length > maximo ? `${texto.slice(0, maximo - 1).trimEnd()}…` : texto
}

// Paginación en el navegador sobre una lista ya filtrada. La página pedida
// se ajusta al rango válido (nunca deja una tabla vacía si hay datos).
export function paginar(lista, pagina, porPagina) {
  const total = lista.length
  const totalPaginas = Math.max(1, Math.ceil(total / porPagina))
  const actual = Math.min(Math.max(1, Number(pagina) || 1), totalPaginas)
  const inicio = (actual - 1) * porPagina

  return {
    elementos: lista.slice(inicio, inicio + porPagina),
    pagina: actual,
    totalPaginas,
    total,
    desde: total ? inicio + 1 : 0,
    hasta: Math.min(inicio + porPagina, total),
    hayAnterior: actual > 1,
    haySiguiente: actual < totalPaginas,
  }
}

// Eje de un gráfico de conteos: tope entero y cuatro divisiones.
export function ejeConteo(maximo) {
  const paso = Math.max(1, Math.ceil(Math.max(0, maximo) / 4))
  return { tope: paso * 4, marcas: [0, 1, 2, 3, 4].map((i) => i * paso) }
}

// Eje de un grupo de Cumplimiento: cinco marcas entre 0 y la escala.
export function ejeEscala(escala) {
  return [0, 1, 2, 3, 4].map((i) => (escala * i) / 4)
}

// Posición (en % del contenedor) de la etiqueta de cada segmento de la dona,
// en el punto medio de su arco. Los segmentos muy chicos no llevan etiqueta.
export function etiquetasDona(segmentos, radio = 40, minimo = 8) {
  let acumulado = 0

  return segmentos.flatMap((segmento) => {
    const medio = acumulado + segmento.porcentaje / 2
    acumulado += segmento.porcentaje

    if (segmento.porcentaje < minimo) return []

    const angulo = (medio / 100) * 2 * Math.PI
    return [{
      nombre: segmento.nombre,
      texto: `${Math.round(segmento.porcentaje)}%`,
      x: 50 + radio * Math.sin(angulo),
      y: 50 - radio * Math.cos(angulo),
    }]
  })
}

// Tarjetas resumen del contexto. "En uso" es el estado real de un plan
// vigente (borrador / en_uso / cerrado). Favorable y "requieren atención"
// (En riesgo o Incumplido) salen del estado acumulado del backend: son
// excluyentes, y un KPI sin mediciones no cuenta en ninguno de los dos.
export const ESTADOS_ATENCION = ['En riesgo', 'Incumplido']

export function resumenTarjetas(planesEstrategicos, planesAnuales, kpisAutorizados) {
  return {
    planesEnUso: planesEstrategicos.filter((plan) => plan.estado === 'en_uso').length,
    planesRegistrados: planesEstrategicos.length,
    anualesEnUso: planesAnuales.filter((plan) => plan.estado === 'en_uso').length,
    anualesRegistrados: planesAnuales.length,
    kpiAutorizados: kpisAutorizados.length,
    kpiFavorables: kpisAutorizados.filter((kpi) => kpi.cantidad_mediciones > 0 && kpi.estado_acumulado_nombre === 'Favorable').length,
    kpiAtencion: kpisAutorizados.filter((kpi) => ESTADOS_ATENCION.includes(kpi.estado_acumulado_nombre)).length,
  }
}

export function porcentajeDe(cantidad, total) {
  return total ? Math.round((cantidad / total) * 100) : 0
}

function numero(valor) {
  if (valor === null || valor === undefined || valor === '') return null
  const convertido = Number(valor)
  return Number.isFinite(convertido) ? convertido : null
}

// Cumplimiento de KPI: un grupo de barras por unidad de medida. Dentro de un
// grupo los valores son comparables y la altura es proporcional al valor
// real (promedio acumulado del backend); entre grupos no se comparan
// alturas. La escala de cada grupo llega al mayor valor o meta del grupo (y
// al menos a 100 si la unidad es %), así la meta se marca como referencia.
export function gruposCumplimiento(kpis) {
  const porUnidad = new Map()

  kpis.forEach((kpi) => {
    const unidad = (kpi.unidad_medida || '').trim() || 'Sin unidad'
    if (!porUnidad.has(unidad)) porUnidad.set(unidad, [])
    porUnidad.get(unidad).push(kpi)
  })

  return Array.from(porUnidad.entries())
    .map(([unidad, lista]) => {
      const valores = lista.flatMap((kpi) => [numero(kpi.promedio_acumulado), numero(kpi.valor_meta)])
        .filter((valor) => valor !== null)
      const maximo = Math.max(unidad === '%' ? 100 : 0, ...valores, 0)
      const escala = maximo > 0 ? maximo : 1

      return {
        unidad,
        escala,
        barras: lista
          .map((kpi) => {
            const valor = numero(kpi.promedio_acumulado)
            const meta = numero(kpi.valor_meta)

            return {
              kpi,
              codigo: codigoKpi(kpi),
              valor,
              alturaPorcentaje: valor === null ? 0 : Math.min(100, (Math.max(valor, 0) / escala) * 100),
              metaPorcentaje: meta === null ? null : Math.min(100, (Math.max(meta, 0) / escala) * 100),
            }
          })
          .sort((a, b) => a.kpi.id - b.kpi.id),
      }
    })
    .sort((a, b) => b.barras.length - a.barras.length || a.unidad.localeCompare(b.unidad))
}

// Archivos de evidencia reales por KPI (una medición tiene a lo sumo uno).
// Las omisiones nunca tienen evidencia.
export function evidenciasPorKpi(mediciones) {
  const conteos = new Map()

  mediciones.forEach((medicion) => {
    if (medicion.cierre_automatico || !medicion.tiene_evidencia) return
    conteos.set(medicion.indicador, (conteos.get(medicion.indicador) || 0) + 1)
  })

  return conteos
}

// KPI con evidencias: cuenta INDICADORES, no archivos.
export function resumenEvidencias(kpis, mediciones) {
  const conteos = evidenciasPorKpi(mediciones)
  const con = kpis.filter((kpi) => (conteos.get(kpi.id) || 0) > 0).length

  return { con, sin: kpis.length - con, total: kpis.length }
}

// Oportunidad de registro con la clasificación actual del backend
// (oportunidad_registro). Las omisiones ("Sin registro") son periodos
// cerrados sin medición: se cuentan aparte de las mediciones registradas.
export function resumenOportunidad(mediciones, sinRegistro) {
  const conteos = {
    [OPORTUNIDAD_A_TIEMPO]: 0,
    [OPORTUNIDAD_CON_RETRASO]: 0,
    [OPORTUNIDAD_CON_AMPLIACION]: 0,
    [sinRegistro]: 0,
  }

  mediciones.forEach((medicion) => {
    const categoria = categoriaOportunidad(medicion, sinRegistro)
    if (categoria in conteos) conteos[categoria] += 1
  })

  return {
    aTiempo: conteos[OPORTUNIDAD_A_TIEMPO],
    conRetraso: conteos[OPORTUNIDAD_CON_RETRASO],
    conAmpliacion: conteos[OPORTUNIDAD_CON_AMPLIACION],
    sinRegistro: conteos[sinRegistro],
    registradas: conteos[OPORTUNIDAD_A_TIEMPO] + conteos[OPORTUNIDAD_CON_RETRASO] + conteos[OPORTUNIDAD_CON_AMPLIACION],
    total: mediciones.length,
  }
}

// Altura de una barra de conteo respecto del mayor conteo del gráfico.
export function alturaConteo(cantidad, maximo) {
  return maximo > 0 ? (cantidad / maximo) * 100 : 0
}
