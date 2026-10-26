// D5: consulta histórica de KPI (src/utils/reportes.js), su gráfica y la
// vista Reportes. `npm test`.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import {
  escalaVertical,
  kpisConsultables,
  kpisDe,
  normalizarSeleccion,
  ordenarCronologicamente,
  planesAnualesDe,
  planesEstrategicosDe,
  serieHistorica,
  tramosConResultado,
} from '../src/utils/reportes.js'

const leer = (ruta) => readFileSync(new URL(ruta, import.meta.url), 'utf8')

const kpis = [
  { id: 1, nombre: 'Ventas', estado: 'autorizado', plan_estrategico: 10, plan_estrategico_titulo: 'PE 2026-2030', plan_anual: 100, plan_anual_nombre: 'Plan 2026' },
  { id: 2, nombre: 'Cobertura', estado: 'autorizado', plan_estrategico: 10, plan_estrategico_titulo: 'PE 2026-2030', plan_anual: 101, plan_anual_nombre: 'Plan 2027' },
  { id: 3, nombre: 'Atención', estado: 'autorizado', plan_estrategico: 20, plan_estrategico_titulo: 'PE 2031-2035', plan_anual: 200, plan_anual_nombre: 'Plan 2031' },
  { id: 4, nombre: 'Borrador', estado: 'borrador', plan_estrategico: 10, plan_estrategico_titulo: 'PE 2026-2030', plan_anual: 100, plan_anual_nombre: 'Plan 2026' },
]

const medicion = (id, fecha, extra = {}) => ({
  id,
  fecha_medicion: fecha,
  periodo_nombre: `P${id}`,
  valor_resultado: '50.0000',
  valor_meta: '80.0000',
  sin_registro: false,
  estado_cumplimiento_nombre: 'En riesgo',
  estado_cumplimiento_color: 'amarillo',
  ...extra,
})

test('solo KPI autorizados y filtros coherentes entre sí', () => {
  const consultables = kpisConsultables(kpis)

  assert.deepEqual(consultables.map((k) => k.id), [1, 2, 3])
  assert.deepEqual(planesEstrategicosDe(consultables).map((p) => p.id), [10, 20])
  assert.deepEqual(planesAnualesDe(consultables, 10).map((p) => p.id), [100, 101])
  assert.deepEqual(kpisDe(consultables, 10, 101).map((k) => k.id), [2])
  assert.deepEqual(kpisDe(consultables, 20, '').map((k) => k.id), [3])
})

test('cambiar de plan limpia el plan anual y el KPI que ya no corresponden', () => {
  const consultables = kpisConsultables(kpis)

  assert.deepEqual(
    normalizarSeleccion(consultables, { planEstrategico: 20, planAnual: 100, kpi: 1 }),
    { planEstrategico: 20, planAnual: '', kpi: '' },
  )
  assert.deepEqual(
    normalizarSeleccion(consultables, { planEstrategico: 10, planAnual: 100, kpi: 1 }),
    { planEstrategico: 10, planAnual: 100, kpi: 1 },
  )
})

test('orden cronológico por cierre del periodo, sea cual sea la frecuencia', () => {
  const trimestral = [medicion(3, '2027-09-30'), medicion(1, '2027-03-31'), medicion(2, '2027-06-30')]

  assert.deepEqual(ordenarCronologicamente(trimestral).map((m) => m.id), [1, 2, 3])
})

test('serie: "Sin registro" queda sin valor (no 0), corta la línea y no inventa periodos', () => {
  const mediciones = [
    medicion(1, '2027-01-31', { valor_resultado: '80.0000', estado_cumplimiento_color: 'verde' }),
    medicion(2, '2027-02-28', { sin_registro: true, valor_resultado: null, estado_cumplimiento_nombre: 'Sin registro', estado_cumplimiento_color: 'gris' }),
    medicion(3, '2027-03-31', { valor_resultado: '60.0000' }),
    medicion(4, '2027-04-30', { valor_resultado: '70.0000' }),
  ]

  const serie = serieHistorica(mediciones)

  assert.equal(serie.length, 4)
  assert.equal(serie[1].valor, null)
  assert.equal(serie[1].sinRegistro, true)
  assert.deepEqual(serie.map((p) => p.clase), ['ok', 'neutral', 'warning', 'warning'])
  assert.deepEqual(tramosConResultado(serie).map((t) => t.map((p) => p.indice)), [[0], [2, 3]])
  assert.deepEqual(serieHistorica([]), [])
})

test('eje vertical en la unidad del KPI: 0-100 para %, redondo para otras unidades', () => {
  assert.deepEqual(escalaVertical([], '%').marcas, [0, 25, 50, 75, 100])

  const quetzales = escalaVertical([{ valor: 1234.5, meta: 2500 }, { valor: null, meta: 2500 }], 'Q')
  assert.equal(quetzales.minimo, 0)
  assert.ok(quetzales.maximo >= 2500)
  assert.ok(quetzales.marcas.every((marca, i, lista) => i === 0 || marca > lista[i - 1]))

  assert.equal(escalaVertical([{ valor: null, meta: null }], 'horas').maximo, 1)
})

test('gráfica: una sola unidad, meta punteada, omisiones marcadas y mensaje sin mediciones', () => {
  const grafica = leer('../src/components/reportes/GraficaHistoricaKpi.vue')

  assert.match(grafica, /unidad: \{/)
  assert.match(grafica, /class="linea-meta"/)
  assert.match(grafica, /marca-sin-registro/)
  assert.match(grafica, /Sin registro \(no es cero\)/)
  assert.match(grafica, /todavía no tiene mediciones/)
  assert.match(grafica, /overflow-x: auto/)
})

test('vista Reportes: solo lectura para los cuatro roles, con PDF y detalle de evidencias', () => {
  const vista = leer('../src/views/ReportesView.vue')
  const router = leer('../src/router/index.js')
  const menu = leer('../src/components/layout/SidebarMenu.vue')

  assert.match(vista, /obtenerMedicionesKpi/)
  assert.match(vista, /descargarReportePdfKpi/)
  assert.match(vista, /<MedicionDetalle v-if="medicionDetalle" :medicion="medicionDetalle" \/>/)
  assert.doesNotMatch(vista, /puede-agregar-evidencia|crearMedicion|actualizarMedicion/)
  assert.match(router, /path: '\/reportes'/)
  assert.doesNotMatch(router.slice(router.indexOf("path: '/reportes'"), router.indexOf("path: '/mapa-estrategico'")), /verificarAcceso/)
  assert.match(menu, /to="\/reportes"/)
})
