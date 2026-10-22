// D3: rangos de evaluación de un KPI. El backend usa mínimo inclusivo y
// máximo exclusivo, y clasifica valores ya redondeados a dos decimales. Por
// eso la plantilla para KPI en % (criterio de Hernán) guarda 60,01 y 75,01:
// aquí esos límites técnicos se describen como "hasta 60" y "más de 60".

import { formatearNumero } from './formato.js'

export const ESTADOS_RANGO = ['Incumplido', 'En riesgo', 'Favorable']

// Un límite que termina en ,01 representa "más de / hasta" el valor anterior
// con dos decimales (60,01 -> 60).
function esLimiteTecnico(valor) {
  return Math.round(Number(valor) * 100) % 100 === 1
}

function formatear(valor, unidad) {
  return formatearNumero(valor, { unidad: unidad || '' })
}

export function describirRango(rango, unidad) {
  const minimo = Number(rango.valor_minimo)
  const tieneMaximo = rango.valor_maximo !== null && rango.valor_maximo !== undefined && rango.valor_maximo !== ''
  const maximo = tieneMaximo ? Number(rango.valor_maximo) : null

  let desde = ''
  if (minimo > 0) {
    desde = esLimiteTecnico(minimo) ? `Más de ${formatear(minimo - 0.01, unidad)}` : `Desde ${formatear(minimo, unidad)}`
  }

  let hasta = ''
  if (maximo !== null) {
    hasta = esLimiteTecnico(maximo) ? `hasta ${formatear(maximo - 0.01, unidad)}` : `menos de ${formatear(maximo, unidad)}`
  }

  if (desde && hasta) return `${desde} ${hasta.startsWith('menos') ? `hasta ${hasta}` : hasta}`
  if (desde) return desde
  if (hasta) return hasta.charAt(0).toUpperCase() + hasta.slice(1)

  return 'Cualquier valor'
}

function aNumero(valor) {
  if (valor === null || valor === undefined || String(valor).trim() === '') return null
  const numero = Number(String(valor).replace(',', '.'))
  return Number.isFinite(numero) ? numero : NaN
}

// Validación previa al envío (el backend vuelve a validar todo el conjunto).
export function validarFilasRangos(filas) {
  const errores = []
  const completas = []

  filas.forEach((fila) => {
    const minimo = aNumero(fila.valor_minimo)
    const maximo = aNumero(fila.valor_maximo)

    if (minimo === null) {
      errores.push(`Indicá el mínimo de "${fila.nombre}".`)
      return
    }
    if (Number.isNaN(minimo) || Number.isNaN(maximo)) {
      errores.push(`Los valores de "${fila.nombre}" deben ser números.`)
      return
    }
    if (minimo < 0) errores.push(`El mínimo de "${fila.nombre}" no puede ser negativo.`)
    if (maximo !== null && maximo <= minimo) errores.push(`El máximo de "${fila.nombre}" debe ser mayor que su mínimo.`)

    completas.push({ ...fila, minimo, maximo })
  })

  const ordenadas = [...completas].sort((a, b) => a.minimo - b.minimo)

  for (let i = 1; i < ordenadas.length; i += 1) {
    const anterior = ordenadas[i - 1]
    if (anterior.maximo === null || anterior.maximo > ordenadas[i].minimo) {
      errores.push(`Los rangos "${anterior.nombre}" y "${ordenadas[i].nombre}" se superponen.`)
    }
  }

  return errores
}
