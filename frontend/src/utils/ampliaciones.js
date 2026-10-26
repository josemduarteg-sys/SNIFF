// Etapa 5: solicitudes de días adicionales para registrar mediciones. Las
// reglas reales viven en el backend (SolicitudAmpliacionPlazo); acá solo
// se calcula lo que se muestra.

export const DIAS_MAXIMOS_AMPLIACION = 10

export const ESTADOS_AMPLIACION = [
  { valor: 'pendiente', nombre: 'Pendiente', clase: 'warning' },
  { valor: 'autorizada', nombre: 'Autorizada', clase: 'ok' },
  { valor: 'rechazada', nombre: 'Rechazada', clase: 'danger' },
  { valor: 'vencida', nombre: 'Vencida', clase: 'neutral' },
  { valor: 'sin_efecto', nombre: 'Sin efecto', clase: 'neutral' },
  { valor: 'retirada', nombre: 'Retirada', clase: 'neutral' },
]

export function datosEstadoAmpliacion(valor) {
  return ESTADOS_AMPLIACION.find((estado) => estado.valor === valor) || { valor, nombre: valor, clase: 'neutral' }
}

export function contarPorEstado(solicitudes) {
  const conteos = Object.fromEntries(ESTADOS_AMPLIACION.map((estado) => [estado.valor, 0]))

  solicitudes.forEach((solicitud) => {
    if (solicitud.estado in conteos) conteos[solicitud.estado] += 1
  })

  return conteos
}

// Suma días calendario a una fecha ISO (AAAA-MM-DD) sin pasar por la zona
// horaria del navegador.
export function sumarDias(fechaIso, dias, habiles = false) {
  if (!fechaIso) return null

  const [anio, mes, dia] = fechaIso.slice(0, 10).split('-').map(Number)
  const fecha = new Date(Date.UTC(anio, mes - 1, dia))
  let restantes = Number(dias || 0)
  if (habiles) {
    while (restantes > 0) {
      fecha.setUTCDate(fecha.getUTCDate() + 1)
      if (fecha.getUTCDay() !== 0 && fecha.getUTCDay() !== 6) restantes -= 1
    }
  } else {
    fecha.setUTCDate(fecha.getUTCDate() + restantes)
  }

  return fecha.toISOString().slice(0, 10)
}

export function formatearFechaIso(fecha) {
  if (!fecha) return '—'

  const [anio, mes, dia] = String(fecha).slice(0, 10).split('-')

  return anio && mes && dia ? `${dia}/${mes}/${anio}` : String(fecha)
}

export function diasValidos(dias, minimo = 1, maximo = DIAS_MAXIMOS_AMPLIACION) {
  const numero = Number(dias)

  return Number.isInteger(numero) && numero >= minimo && numero <= maximo
}

// Oportunidad de registro (criterio de Hernán, 06/10/2026): días entre el
// cierre del periodo y el registro. La categoría la calcula el backend
// (oportunidad_registro) con el plazo y las ampliaciones; una medición
// registrada con ampliación es Tardía y además trae registrada_con_ampliacion.
export const OPORTUNIDAD_OPORTUNO = 'Oportuno'
export const OPORTUNIDAD_DEMORADO = 'Demorado'
export const OPORTUNIDAD_TARDIO = 'Tardío'
export const OPORTUNIDAD_FUERA_DE_PLAZO = 'Fuera de plazo'

// Sin el campo del backend no se puede clasificar (hace falta el plazo):
// devuelve null en lugar de suponer una categoría.
export function categoriaOportunidad(medicion, sinRegistro) {
  if (medicion.oportunidad_registro) return medicion.oportunidad_registro
  if (medicion.cierre_automatico) return sinRegistro

  return null
}
