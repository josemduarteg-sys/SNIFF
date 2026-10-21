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
export function sumarDias(fechaIso, dias) {
  if (!fechaIso) return null

  const [anio, mes, dia] = fechaIso.slice(0, 10).split('-').map(Number)
  const fecha = new Date(Date.UTC(anio, mes - 1, dia + Number(dias || 0)))

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

// Oportunidad de registro (Dashboard): una sola categoría por medición.
// "Con ampliación" = registrada después del plazo ordinario gracias a una
// ampliación autorizada (lo decide el backend: registrada_con_ampliacion).
export const OPORTUNIDAD_A_TIEMPO = 'A tiempo'
export const OPORTUNIDAD_CON_RETRASO = 'Con retraso'
export const OPORTUNIDAD_CON_AMPLIACION = 'Con ampliación'

// Etapa 6 (M5): el backend decide la categoría (oportunidad_registro,
// criterio "por plazo"). El cálculo de abajo queda solo como respaldo para
// una respuesta que todavía no traiga ese campo.
export function categoriaOportunidad(medicion, sinRegistro) {
  if (medicion.oportunidad_registro) return medicion.oportunidad_registro
  if (medicion.cierre_automatico) return sinRegistro
  if (medicion.registrada_con_ampliacion) return OPORTUNIDAD_CON_AMPLIACION

  const fechaRegistro = (medicion.fecha_registro || '').slice(0, 10)
  const fechaCierre = medicion.fecha_medicion

  if (fechaRegistro && fechaCierre && fechaRegistro > fechaCierre) return OPORTUNIDAD_CON_RETRASO

  return OPORTUNIDAD_A_TIEMPO
}
