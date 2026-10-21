// Etapa 6: filtros del Dashboard (M12), oportunidad de registro (M5) y
// navegación desde notificaciones. Se ejecuta con `npm test`.
import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  descripcionContexto,
  filtrarContexto,
  normalizarSeleccion,
  planesAnualesDe,
} from '../src/utils/dashboardFiltros.js'
import { categoriaOportunidad } from '../src/utils/ampliaciones.js'
import {
  alertaCorresponde,
  kpiDisponible,
  leerParametrosNotificacion,
} from '../src/utils/navegacionNotificaciones.js'
import { categoriaKpi } from '../src/utils/cumplimiento.js'

const planesEstrategicos = [
  { id: 1, titulo: 'Plan A', estado: 'en_uso' },
  { id: 2, titulo: 'Plan B', estado: 'en_uso' },
]
const planesAnuales = [
  { id: 10, plan_estrategico: 1, nombre: 'Plan anual 2026', plan_estrategico_titulo: 'Plan A' },
  { id: 11, plan_estrategico: 1, nombre: 'Plan anual 2027', plan_estrategico_titulo: 'Plan A' },
  { id: 20, plan_estrategico: 2, nombre: 'Plan anual 2026', plan_estrategico_titulo: 'Plan B' },
]
const indicadores = [
  { id: 100, plan_estrategico: 1, plan_anual: 10, cantidad_mediciones: 2, cantidad_omisiones: 0 },
  { id: 101, plan_estrategico: 1, plan_anual: 11, cantidad_mediciones: 0, cantidad_omisiones: 0 },
  { id: 200, plan_estrategico: 2, plan_anual: 20, cantidad_mediciones: 0, cantidad_omisiones: 3 },
]
const mediciones = [
  { id: 1, indicador: 100 },
  { id: 2, indicador: 100 },
  { id: 3, indicador: 200 },
]
const alertas = [{ id: 7, indicador: 100 }, { id: 8, indicador: 200 }]
const datos = { planesEstrategicos, planesAnuales, indicadores, mediciones, alertas }

function ids(lista) {
  return lista.map((item) => item.id)
}

test('sin filtro el contexto incluye todo', () => {
  const contexto = filtrarContexto(datos, { planEstrategico: null, planAnual: null, anio: null })

  assert.deepEqual(ids(contexto.indicadores), [100, 101, 200])
  assert.equal(contexto.mediciones.length, 3)
  assert.equal(contexto.alertas.length, 2)
  assert.match(descripcionContexto({}, planesEstrategicos, planesAnuales), /Todos los planes \(2/)
})

test('filtro por plan estratégico: KPI, mediciones, alertas y planes del mismo plan', () => {
  const contexto = filtrarContexto(datos, { planEstrategico: 1, planAnual: null, anio: null })

  assert.deepEqual(ids(contexto.planesEstrategicos), [1])
  assert.deepEqual(ids(contexto.planesAnuales), [10, 11])
  assert.deepEqual(ids(contexto.indicadores), [100, 101])
  assert.deepEqual(ids(contexto.mediciones), [1, 2])
  assert.deepEqual(ids(contexto.alertas), [7])
})

test('filtros combinados de plan estratégico y plan anual', () => {
  const contexto = filtrarContexto(datos, { planEstrategico: 1, planAnual: 11 })

  assert.deepEqual(ids(contexto.planesAnuales), [11])
  assert.deepEqual(ids(contexto.indicadores), [101])
  assert.deepEqual(contexto.mediciones, [])
  assert.deepEqual(contexto.alertas, [])
  // KPI sin mediciones: sigue en el contexto, como "Sin mediciones".
  assert.equal(categoriaKpi(contexto.indicadores[0]), 'Sin mediciones')
})

test('KPI con omisiones se conserva al filtrar', () => {
  const contexto = filtrarContexto(datos, { planEstrategico: 2, planAnual: 20, anio: null })

  assert.deepEqual(ids(contexto.indicadores), [200])
  assert.equal(categoriaKpi(contexto.indicadores[0]), 'Sin registro')
})

test('la selección respeta la relación entre planes y descarta ids inválidos', () => {
  // Plan anual sin plan estratégico: se completa con su plan.
  assert.deepEqual(normalizarSeleccion({ planAnual: '20' }, planesEstrategicos, planesAnuales), { planEstrategico: 2, planAnual: 20, anio: null })
  // Plan anual de otro plan estratégico: se descarta.
  assert.deepEqual(normalizarSeleccion({ planEstrategico: '1', planAnual: '20' }, planesEstrategicos, planesAnuales), { planEstrategico: 1, planAnual: null, anio: null })
  // Ids inexistentes o no numéricos.
  assert.deepEqual(normalizarSeleccion({ planEstrategico: '99', planAnual: 'abc' }, planesEstrategicos, planesAnuales), { planEstrategico: null, planAnual: null, anio: null })
  assert.deepEqual(normalizarSeleccion({ planEstrategico: '-1' }, planesEstrategicos, planesAnuales), { planEstrategico: null, planAnual: null, anio: null })
  assert.deepEqual(ids(planesAnualesDe(planesAnuales, 2)), [20])
  assert.match(descripcionContexto({ planEstrategico: 1, planAnual: 11 }, planesEstrategicos, planesAnuales), /Plan anual 2027 · Plan estratégico Plan A/)
})

test('oportunidad de registro: la categoría del backend manda', () => {
  const base = { fecha_medicion: '2027-01-31', fecha_registro: '2027-02-03T10:00:00', cierre_automatico: false }

  assert.equal(categoriaOportunidad({ ...base, oportunidad_registro: 'A tiempo' }, 'Sin registro'), 'A tiempo')
  assert.equal(categoriaOportunidad({ ...base, oportunidad_registro: 'Con ampliación' }, 'Sin registro'), 'Con ampliación')
  assert.equal(categoriaOportunidad({ ...base, oportunidad_registro: 'Con retraso' }, 'Sin registro'), 'Con retraso')
  assert.equal(categoriaOportunidad({ ...base, cierre_automatico: true, oportunidad_registro: 'Sin registro' }, 'Sin registro'), 'Sin registro')
})

test('parámetros de notificación válidos e inválidos', () => {
  assert.deepEqual(leerParametrosNotificacion({ indicador: '12', alerta: '5' }), { indicador: 12, alerta: 5, hayParametros: true, invalidos: false })
  assert.deepEqual(leerParametrosNotificacion({}), { indicador: null, alerta: null, hayParametros: false, invalidos: false })

  for (const valor of ['abc', '0', '-3', '1.5', '12abc', ' ']) {
    assert.equal(leerParametrosNotificacion({ indicador: valor }).invalidos, true, valor)
  }

  assert.equal(leerParametrosNotificacion({ indicador: '3', alerta: 'x' }).invalidos, true)
  assert.equal(leerParametrosNotificacion({ indicador: ['4', '5'] }).indicador, 4)
})

test('el KPI y la alerta del enlace solo se aplican si corresponden', () => {
  assert.equal(kpiDisponible(100, indicadores, []), true)
  assert.equal(kpiDisponible(555, [], mediciones), false)
  assert.equal(kpiDisponible(200, [], mediciones), true) // Visible por sus mediciones.
  assert.equal(kpiDisponible(null, indicadores, mediciones), false)

  assert.equal(alertaCorresponde({ indicador: 100 }, 100), true)
  assert.equal(alertaCorresponde({ indicador: 200 }, 100), false)
  assert.equal(alertaCorresponde({ indicador: 200 }, null), true)
  assert.equal(alertaCorresponde(null, 100), false)
})
