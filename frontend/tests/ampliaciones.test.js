// Etapa 5: días adicionales para registrar mediciones (src/utils/ampliaciones.js)
// y su permiso en la interfaz (src/utils/permisos.js). Se ejecuta con `npm test`.
import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  OPORTUNIDAD_DEMORADO,
  OPORTUNIDAD_FUERA_DE_PLAZO,
  OPORTUNIDAD_OPORTUNO,
  OPORTUNIDAD_TARDIO,
  categoriaOportunidad,
  contarPorEstado,
  datosEstadoAmpliacion,
  diasValidos,
  formatearFechaIso,
  sumarDias,
} from '../src/utils/ampliaciones.js'
import {
  puedeResolverAmpliacion,
  puedeSolicitarAmpliacion,
  puedeVerSolicitudesAmpliacion,
} from '../src/utils/permisos.js'

const SIN_REGISTRO = 'Sin registro'

test('sumarDias usa días calendario y cruza meses y años', () => {
  assert.equal(sumarDias('2027-02-05', 10), '2027-02-15')
  assert.equal(sumarDias('2027-02-25', 10), '2027-03-07')
  assert.equal(sumarDias('2028-02-25', 10), '2028-03-06') // Año bisiesto.
  assert.equal(sumarDias('2027-12-28', 5), '2028-01-02')
  assert.equal(sumarDias(null, 3), null)
})

test('formatearFechaIso muestra día/mes/año', () => {
  assert.equal(formatearFechaIso('2027-02-15'), '15/02/2027')
  assert.equal(formatearFechaIso('2027-02-15T10:30:00-06:00'), '15/02/2027')
  assert.equal(formatearFechaIso(null), '—')
})

test('diasValidos respeta el rango de 1 a 10 y enteros', () => {
  assert.equal(diasValidos(1), true)
  assert.equal(diasValidos(10), true)
  assert.equal(diasValidos(0), false)
  assert.equal(diasValidos(11), false)
  assert.equal(diasValidos(2.5), false)
  assert.equal(diasValidos(''), false)
  assert.equal(diasValidos(3, 5, 7), false) // Mínimo para que el plazo siga vigente.
  assert.equal(diasValidos(8, 1, 7), false) // No más de lo solicitado.
})

test('contarPorEstado y etiquetas de estado', () => {
  const conteos = contarPorEstado([{ estado: 'pendiente' }, { estado: 'pendiente' }, { estado: 'retirada' }])

  assert.equal(conteos.pendiente, 2)
  assert.equal(conteos.retirada, 1)
  assert.equal(conteos.autorizada, 0)
  assert.equal(datosEstadoAmpliacion('sin_efecto').nombre, 'Sin efecto')
  assert.equal(datosEstadoAmpliacion('autorizada').clase, 'ok')
})

test('oportunidad de registro: categorías del criterio de Hernán', () => {
  assert.deepEqual(
    [OPORTUNIDAD_OPORTUNO, OPORTUNIDAD_DEMORADO, OPORTUNIDAD_TARDIO, OPORTUNIDAD_FUERA_DE_PLAZO],
    ['Oportuno', 'Demorado', 'Tardío', 'Fuera de plazo'],
  )

  const base = { fecha_medicion: '2027-01-31', fecha_registro: '2027-02-10T09:00:00', cierre_automatico: false }

  // La categoría la calcula el backend (con el plazo y las ampliaciones).
  assert.equal(categoriaOportunidad({ ...base, oportunidad_registro: 'Tardío', registrada_con_ampliacion: true }, SIN_REGISTRO), OPORTUNIDAD_TARDIO)
  assert.equal(categoriaOportunidad({ ...base, cierre_automatico: true }, SIN_REGISTRO), SIN_REGISTRO)
  // Sin el dato del backend no se supone ninguna categoría.
  assert.equal(categoriaOportunidad(base, SIN_REGISTRO), null)
})

test('solo Ejecutor y Administrador de planificación ven las solicitudes', () => {
  const ejecutor = { rol_nombre: 'Ejecutor operativo' }
  const planificacion = { rol_nombre: 'Administrador de planificación' }
  const sistema = { rol_nombre: 'Administrador del sistema' }
  const consulta = { rol_nombre: 'Usuario de consulta' }

  assert.equal(puedeSolicitarAmpliacion(ejecutor), true)
  assert.equal(puedeSolicitarAmpliacion(planificacion), false)
  assert.equal(puedeResolverAmpliacion(planificacion), true)
  assert.equal(puedeResolverAmpliacion(ejecutor), false)

  for (const usuario of [ejecutor, planificacion]) assert.equal(puedeVerSolicitudesAmpliacion(usuario), true)
  for (const usuario of [sistema, consulta, null]) assert.equal(puedeVerSolicitudesAmpliacion(usuario), false)
})

test('días hábiles: viernes, cruce de mes y máximo total', () => {
  assert.equal(sumarDias('2027-04-30', 5, true), '2027-05-07')
  assert.equal(sumarDias('2027-04-30', 10, true), '2027-05-14')
  assert.equal(sumarDias('2027-05-07', 5, true), '2027-05-14')
  assert.equal(sumarDias('2026-07-31', 5, false), '2026-08-05')
})
