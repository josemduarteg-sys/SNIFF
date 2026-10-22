// D3: descripción y validación de los rangos de evaluación de KPI
// (src/utils/rangos.js) y su editor en el detalle del KPI. `npm test`.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { describirRango, validarFilasRangos } from '../src/utils/rangos.js'

const plantilla = [
  { valor_minimo: '0.0000', valor_maximo: '60.0100' },
  { valor_minimo: '60.0100', valor_maximo: '75.0100' },
  { valor_minimo: '75.0100', valor_maximo: null },
]

test('plantilla 60/75: los límites técnicos se describen en lenguaje claro', () => {
  assert.deepEqual(plantilla.map((r) => describirRango(r, '%')), [
    'Hasta 60.00 %',
    'Más de 60.00 % hasta 75.00 %',
    'Más de 75.00 %',
  ])
})

test('plantilla anterior 70/85 y rangos en días usan su propia unidad', () => {
  assert.equal(describirRango({ valor_minimo: '0', valor_maximo: '70' }, '%'), 'Menos de 70.00 %')
  assert.equal(describirRango({ valor_minimo: '70', valor_maximo: '85' }, '%'), 'Desde 70.00 % hasta menos de 85.00 %')
  assert.equal(describirRango({ valor_minimo: '85', valor_maximo: null }, '%'), 'Desde 85.00 %')
  // KPI #10 (días, invertido): nunca se le agrega "%".
  const dias = describirRango({ valor_minimo: '3', valor_maximo: '6' }, 'días')
  assert.match(dias, /días/)
  assert.doesNotMatch(dias, /%/)
  assert.equal(describirRango({ valor_minimo: '0', valor_maximo: null }, 'días'), 'Cualquier valor')
})

test('validación previa del editor', () => {
  const fila = (nombre, minimo, maximo) => ({ nombre, valor_minimo: minimo, valor_maximo: maximo })

  // Rangos invertidos en días: válidos.
  assert.deepEqual(validarFilasRangos([fila('Favorable', 0, 3), fila('En riesgo', 3, 6), fila('Incumplido', 6, '')]), [])
  assert.match(validarFilasRangos([fila('Favorable', '', 3)]).join(), /mínimo/)
  assert.match(validarFilasRangos([fila('Favorable', 5, 3)]).join(), /mayor que su mínimo/)
  assert.match(validarFilasRangos([fila('Favorable', -1, 3)]).join(), /negativo/)
  assert.match(validarFilasRangos([fila('Favorable', 0, ''), fila('Incumplido', 6, '')]).join(), /se superponen/)
  assert.match(validarFilasRangos([fila('Favorable', 'x', 3)]).join(), /números/)
})

test('el editor está en el detalle del KPI, solo para Borrador y con su unidad', () => {
  const detalle = readFileSync(new URL('../src/components/indicadores/IndicadorDetalle.vue', import.meta.url), 'utf8')
  const vista = readFileSync(new URL('../src/views/IndicadoresView.vue', import.meta.url), 'utf8')

  assert.match(detalle, /describirRango\(rango, props\.indicador\.unidad_medida\)/)
  assert.doesNotMatch(detalle, /unidad: '%'/)
  assert.match(detalle, /<RangosKpiEditor/)
  assert.match(vista, /kpi\.estado === 'borrador'/)
  assert.match(vista, /:puede-editar-rangos="puedeEditarRangosDetalle"/)
})
