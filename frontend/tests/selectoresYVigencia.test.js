// Correcciones finales: filtro "Estado del periodo" de Registro de
// mediciones, selectores buscables y vigencia (Reportes y registro).
// `npm test`.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { filtrarOpciones, normalizarTexto } from '../src/utils/busqueda.js'
import { textoEstadoCumplimiento } from '../src/utils/cumplimiento.js'
import { textoObjetivoEspecifico } from '../src/utils/objetivos.js'
import { estadosDelPeriodo, kpiDePlanAbierto, kpisDisponiblesParaRegistro } from '../src/utils/registroMediciones.js'
import {
  kpiVigente,
  kpisConsultables,
  normalizarSeleccion,
  planesAnualesDe,
  planesEstrategicosDe,
} from '../src/utils/reportes.js'

const leer = (ruta) => readFileSync(new URL(ruta, import.meta.url), 'utf8')

// ---------- 1. Filtro Estado del periodo ----------

test('estado del periodo: opciones = estados reales de las mediciones, sin repetir ni inventar', () => {
  const mediciones = [
    { estado_cumplimiento: 1, estado_cumplimiento_nombre: 'Favorable' },
    { estado_cumplimiento: 2, estado_cumplimiento_nombre: 'En riesgo' },
    { estado_cumplimiento: 1, estado_cumplimiento_nombre: 'Favorable' },
    { estado_cumplimiento: 3, estado_cumplimiento_nombre: 'Incumplido' },
    { estado_cumplimiento: 5, estado_cumplimiento_nombre: 'Sin registro' },
    { estado_cumplimiento: 4, estado_cumplimiento_nombre: 'Pendiente de actualización' },
    { estado_cumplimiento: null, estado_cumplimiento_nombre: null },
  ]

  assert.deepEqual(estadosDelPeriodo(mediciones, textoEstadoCumplimiento), [
    { id: 2, nombre: 'En riesgo' },
    { id: 1, nombre: 'Favorable' },
    { id: 3, nombre: 'Incumplido' },
    { id: 4, nombre: 'Sin criterio de cumplimiento configurado' },
    { id: 5, nombre: 'Sin registro' },
  ])
  assert.deepEqual(estadosDelPeriodo([]), [])
})

test('la vista arma el filtro desde las mediciones y lo rotula "Estado del periodo"', () => {
  const vista = leer('../src/views/MedicionesView.vue')

  assert.match(vista, /estadosDelPeriodo\(mediciones\.value, textoEstadoCumplimiento\)/)
  assert.doesNotMatch(vista, /datosFormulario\.estadosCumplimiento/)
  assert.match(vista, /Estado del periodo:<\/span>/)
  assert.match(vista, /<option value="">Todos<\/option>\s*<option v-for="estado in estadosCumplimiento"/)
  // Filtra por el estado de CADA medición, no por el acumulado.
  assert.match(vista, /Number\(medicion\.estado_cumplimiento\) === Number\(estadoSeleccionado\.value\)/)
})

// ---------- 2 y 3. Selectores buscables ----------

test('búsqueda sin distinguir mayúsculas ni acentos, por cualquier parte del texto', () => {
  const opciones = [
    { id: 1, texto: 'Planificación estratégica 2026-2030' },
    { id: 2, texto: 'Gestión de cobros' },
    { id: 3, texto: 'Atención al cliente' },
  ]

  assert.equal(normalizarTexto('  PlaNificaCIÓN '), 'planificacion')
  assert.deepEqual(filtrarOpciones(opciones, 'planificacion').map((o) => o.id), [1])
  assert.deepEqual(filtrarOpciones(opciones, 'ATENCION').map((o) => o.id), [3])
  assert.deepEqual(filtrarOpciones(opciones, 'cob').map((o) => o.id), [2])
  assert.deepEqual(filtrarOpciones(opciones, '').map((o) => o.id), [1, 2, 3])
  assert.deepEqual(filtrarOpciones(opciones, 'xyz'), [])
})

test('SelectorBuscable: teclado, limpiar búsqueda y variante para barras de filtros', () => {
  const selector = leer('../src/components/common/SelectorBuscable.vue')

  assert.match(selector, /@keydown\.down\.prevent="mover\(1\)"/)
  assert.match(selector, /@keydown\.up\.prevent="mover\(-1\)"/)
  assert.match(selector, /@keydown\.enter\.prevent="elegirActiva"/)
  assert.match(selector, /@keydown\.esc\.prevent/)
  assert.match(selector, /aria-label="Limpiar búsqueda"/)
  assert.match(selector, /filtrarOpciones\(props\.opciones, busqueda\.value\)/)
  assert.match(selector, /variante: \{/)
  // Mismo contrato v-model que antes.
  assert.match(selector, /emit\('update:modelValue', opcion\.id\)/)
})

test('selectores convertidos: Reportes, Mediciones (KPI), Indicadores (objetivo) y filtros de plan', () => {
  const reportes = leer('../src/views/ReportesView.vue')
  assert.equal((reportes.match(/<SelectorBuscable/g) || []).length, 3)
  assert.doesNotMatch(reportes, /<select/)

  const mediciones = leer('../src/views/MedicionesView.vue')
  assert.match(mediciones, /<SelectorBuscable\s+v-model="indicadorSeleccionado"/)

  const indicadores = leer('../src/views/IndicadoresView.vue')
  assert.match(indicadores, /<SelectorBuscable\s+v-model="objetivoSeleccionado"/)
  assert.match(indicadores, /Objetivo:<\/span>/)

  for (const vista of ['ObjetivosGeneralesView', 'PlanesAnualesView']) {
    assert.match(leer(`../src/views/${vista}.vue`), /<SelectorBuscable\s+v-model="planSeleccionadoFiltro"/, vista)
  }

  // Los selectores cortos siguen nativos.
  assert.match(mediciones, /<select v-model="estadoSeleccionado">/)
  assert.match(indicadores, /<select v-model="frecuenciaSeleccionada">/)
})

test('objetivo implícito de un KPI directo se muestra con su objetivo general', () => {
  assert.equal(textoObjetivoEspecifico({
    es_generado_automaticamente: true,
    texto_objetivo: 'KPI directo del objetivo general',
    objetivo_general_texto: 'Mejorar la cobranza',
  }), 'Mejorar la cobranza')
  assert.equal(textoObjetivoEspecifico({ texto_objetivo: 'Reducir mora', objetivo_general_texto: 'OG' }), 'Reducir mora')
})

// ---------- 4. Vigencia ----------

const kpi = (id, extra = {}) => ({
  id,
  nombre: `KPI ${id}`,
  estado: 'autorizado',
  plan_estrategico: 1,
  plan_estrategico_titulo: 'PE',
  plan_estrategico_estado: 'en_uso',
  plan_anual: 10,
  plan_anual_nombre: 'Plan 2026',
  plan_anual_estado: 'en_uso',
  periodo_disponible: true,
  ...extra,
})

test('vigencia = misma regla que esta_bloqueado(): plan anual o estratégico Cerrado', () => {
  assert.equal(kpiVigente(kpi(1)), true)
  assert.equal(kpiVigente(kpi(2, { plan_anual_estado: 'cerrado' })), false)
  assert.equal(kpiVigente(kpi(3, { plan_estrategico_estado: 'cerrado' })), false)
  assert.equal(kpiVigente(kpi(4, { plan_anual_estado: 'borrador' })), true)
})

test('Reportes: por defecto vigentes; el histórico incluye los de planes cerrados, rotulados', () => {
  const kpis = [
    kpi(1),
    kpi(2, { plan_anual: 11, plan_anual_nombre: 'Plan 2025', plan_anual_estado: 'cerrado' }),
    kpi(3, { estado: 'borrador' }),
  ]

  assert.deepEqual(kpisConsultables(kpis).map((k) => k.id), [1])
  assert.deepEqual(kpisConsultables(kpis, { incluirCerrados: true }).map((k) => k.id), [1, 2])
  assert.deepEqual(
    planesAnualesDe(kpisConsultables(kpis, { incluirCerrados: true }), 1).map((p) => p.nombre),
    ['Plan 2025 (Cerrado)', 'Plan 2026'],
  )
  assert.deepEqual(planesEstrategicosDe(kpisConsultables(kpis)).map((p) => p.nombre), ['PE'])

  // Al quitar el histórico, una selección de plan cerrado se limpia.
  assert.deepEqual(
    normalizarSeleccion(kpisConsultables(kpis), { planEstrategico: 1, planAnual: 11, kpi: 2 }),
    { planEstrategico: 1, planAnual: '', kpi: '' },
  )
})

test('registro y ampliaciones: nunca KPI de un plan Cerrado, aunque tenga periodo disponible', () => {
  const kpis = [
    kpi(1),
    kpi(2, { plan_anual_estado: 'cerrado' }),
    kpi(3, { plan_estrategico_estado: 'cerrado' }),
    kpi(4, { periodo_disponible: false }),
    kpi(5, { estado: 'anulado' }),
  ]

  assert.deepEqual(kpisDisponiblesParaRegistro(kpis).map((k) => k.id), [1])
  assert.equal(kpiDePlanAbierto(kpis[1]), false)
  assert.match(leer('../src/components/mediciones/SolicitudAmpliacionForm.vue'), /props\.indicadores\.filter\(kpiDePlanAbierto\)/)
})

test('Reportes: casilla de consulta histórica y enlace a un KPI cerrado abre el histórico', () => {
  const vista = leer('../src/views/ReportesView.vue')

  assert.match(vista, /v-model="incluirCerrados" type="checkbox"/)
  assert.match(vista, /Incluir KPI de planes cerrados \(consulta histórica\)/)
  assert.match(vista, /if \(pedido && !kpiVigente\(pedido\)\) incluirCerrados\.value = true/)
})
