// Etapa 3 (auditoría C3): clasificación de KPI y mediciones con omisiones
// "Sin registro" (src/utils/cumplimiento.js), usada por el Dashboard,
// Indicadores y Mediciones. Se ejecuta con `npm test`.
import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  SIN_MEDICIONES,
  SIN_REGISTRO,
  categoriaAcumuladaMedicion,
  categoriaKpi,
  esMedicionSinRegistro,
  textoEstadoCumplimiento,
  textoOmisiones,
} from '../src/utils/cumplimiento.js'

test('KPI sin ninguna medición ni omisión: "Sin mediciones"', () => {
  assert.equal(categoriaKpi({ cantidad_mediciones: 0, cantidad_omisiones: 0, estado_acumulado_nombre: null }), SIN_MEDICIONES)
})

test('KPI con únicamente omisiones: "Sin registro", distinto de "Sin mediciones"', () => {
  const kpi = { cantidad_mediciones: 0, cantidad_omisiones: 3, estado_acumulado_nombre: null }

  assert.equal(categoriaKpi(kpi), SIN_REGISTRO)
  assert.notEqual(categoriaKpi(kpi), SIN_MEDICIONES)
})

test('KPI con resultados reales y omisiones conserva su estado acumulado', () => {
  const kpi = { cantidad_mediciones: 2, cantidad_omisiones: 4, estado_acumulado_nombre: 'Favorable' }

  assert.equal(categoriaKpi(kpi), 'Favorable')
  assert.equal(textoOmisiones(kpi.cantidad_omisiones), '4 periodos sin registro')
})

test('KPI con resultados sin rango aplicable sigue en "Pendiente de actualización"', () => {
  assert.equal(
    categoriaKpi({ cantidad_mediciones: 1, cantidad_omisiones: 0, estado_acumulado_nombre: null }),
    'Pendiente de actualización',
  )
})

test('una medición real con resultado 0 no es una omisión', () => {
  const ceroReal = { valor_resultado: '0.0000', sin_registro: false, cierre_automatico: false }

  assert.equal(esMedicionSinRegistro(ceroReal), false)
})

test('una omisión se reconoce por sin_registro', () => {
  const omision = { valor_resultado: null, sin_registro: true, cierre_automatico: true }

  assert.equal(esMedicionSinRegistro(omision), true)
})

test('un cierre automático anterior guardado en 0.00 no se reinterpreta como omisión', () => {
  const anterior = { valor_resultado: '0.0000', sin_registro: false, cierre_automatico: true }

  assert.equal(esMedicionSinRegistro(anterior), false)
})

test('evolución mensual: omisión sin resultados previos cuenta como "Sin registro"', () => {
  assert.equal(
    categoriaAcumuladaMedicion({ sin_registro: true, estado_acumulado_hasta_medicion_nombre: null }),
    SIN_REGISTRO,
  )
})

test('evolución mensual: omisión con resultados previos conserva el estado acumulado real', () => {
  assert.equal(
    categoriaAcumuladaMedicion({ sin_registro: true, estado_acumulado_hasta_medicion_nombre: 'En riesgo' }),
    'En riesgo',
  )
  assert.equal(
    categoriaAcumuladaMedicion({ sin_registro: false, estado_acumulado_hasta_medicion_nombre: 'Favorable' }),
    'Favorable',
  )
})

test('textos visibles de omisiones y del estado "Sin registro"', () => {
  assert.equal(textoOmisiones(0), '')
  assert.equal(textoOmisiones(1), '1 periodo sin registro')
  assert.equal(textoOmisiones('2'), '2 periodos sin registro')
  assert.equal(textoEstadoCumplimiento(SIN_REGISTRO), SIN_REGISTRO)
  assert.equal(textoEstadoCumplimiento(SIN_MEDICIONES), SIN_MEDICIONES)
})
