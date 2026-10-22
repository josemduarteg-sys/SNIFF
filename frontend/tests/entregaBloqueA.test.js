// Entrega a Hernán, Bloque A (alcance de la reunión del 06/10/2026):
// objetivos específicos deshabilitados, responsables individuales retirados
// de la interfaz y registro de mediciones solo con los KPI disponibles.
// Se ejecuta con `npm test`.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { TEXTO_OBJETIVO_IMPLICITO, esObjetivoImplicito, textoObjetivoKpi } from '../src/utils/objetivos.js'
import { MENSAJE_SIN_KPI_DISPONIBLES, kpisDisponiblesParaRegistro } from '../src/utils/registroMediciones.js'

function fuente(ruta) {
  return readFileSync(new URL(`../src/${ruta}`, import.meta.url), 'utf8')
}

test('KPI directo muestra su objetivo general; uno con objetivo real conserva el suyo', () => {
  const directo = {
    es_directo: true,
    objetivo_especifico_texto: TEXTO_OBJETIVO_IMPLICITO,
    objetivo_general_texto: 'Mejorar la cartera',
  }
  const historico = {
    es_directo: false,
    objetivo_especifico_texto: 'Objetivo registrado antes',
    objetivo_general_texto: 'Mejorar la cartera',
  }

  assert.equal(textoObjetivoKpi(directo), 'Mejorar la cartera')
  assert.equal(esObjetivoImplicito(directo), true)
  assert.equal(textoObjetivoKpi(historico), 'Objetivo registrado antes')
  assert.equal(esObjetivoImplicito(historico), false)
  // Sin es_directo (p. ej. datos de una medición), se reconoce por el texto implícito.
  assert.equal(esObjetivoImplicito({ objetivo_especifico_texto: TEXTO_OBJETIVO_IMPLICITO }), true)
  assert.equal(textoObjetivoKpi(null), 'Sin objetivo')
  assert.equal(textoObjetivoKpi({}), 'Sin objetivo')
})

test('el texto implícito coincide con el del backend', () => {
  const backend = readFileSync(new URL('../../backend/apps/estrategia/services.py', import.meta.url), 'utf8')
  assert.match(backend, new RegExp(`TEXTO_OBJETIVO_ESPECIFICO_DIRECTO = '${TEXTO_OBJETIVO_IMPLICITO}'`))
})

test('el registro de mediciones lista solo los KPI disponibles', () => {
  const indicadores = [
    { id: 1, estado: 'autorizado', periodo_disponible: true },
    { id: 2, estado: 'autorizado', periodo_disponible: false },
    { id: 3, estado: 'borrador', periodo_disponible: true },
    { id: 4, estado: 'anulado', periodo_disponible: true },
    { id: 5, estado: 'autorizado' },
  ]

  assert.deepEqual(kpisDisponiblesParaRegistro(indicadores).map((kpi) => kpi.id), [1])
  assert.deepEqual(kpisDisponiblesParaRegistro([]), [])
  assert.deepEqual(kpisDisponiblesParaRegistro(undefined), [])
  assert.match(MENSAJE_SIN_KPI_DISPONIBLES, /Ningún KPI/)
})

test('el formulario de medición usa el filtro y avisa cuando no hay KPI disponibles', () => {
  const formulario = fuente('components/mediciones/MedicionForm.vue')

  assert.match(formulario, /kpisDisponiblesParaRegistro\(props\.indicadores\)/)
  assert.match(formulario, /v-if="sinKpiDisponibles"/)
  assert.doesNotMatch(formulario, /periodo_disponible \? '\(Disponible\)' : '\(No disponible\)'/)
  assert.doesNotMatch(formulario, /<span>Objetivo específico<\/span>/)
})

test('objetivos específicos: sin menú, sin pantalla accesible y sin selector en el KPI', () => {
  assert.doesNotMatch(fuente('components/layout/SidebarMenu.vue'), /to="\/objetivos-especificos"/)

  const rutas = fuente('router/index.js')
  assert.match(rutas, /path: '\/objetivos-especificos',\s*redirect: '\/indicadores'/)
  assert.doesNotMatch(rutas, /import ObjetivosEspecificosView/)

  const formulario = fuente('components/indicadores/IndicadorForm.vue')
  assert.doesNotMatch(formulario, /Objetivo específico \(opcional\)/)
  assert.doesNotMatch(formulario, /v-model="estado\.objetivo_especifico"/)
  // El vínculo existente se sigue enviando al guardar.
  assert.match(formulario, /objetivo_especifico: estado\.objetivo_especifico \|\| null/)

  assert.doesNotMatch(fuente('views/IndicadoresView.vue'), /<th>Objetivo específico<\/th>/)
  assert.doesNotMatch(fuente('components/indicadores/IndicadorDetalle.vue'), /<span>Objetivo específico<\/span>/)
})

test('responsables individuales: sin sección, filtro ni contador', () => {
  const detalle = fuente('components/indicadores/IndicadorDetalle.vue')
  assert.doesNotMatch(detalle, /<ResponsablesKpi/)
  assert.doesNotMatch(detalle, /import ResponsablesKpi/)

  const listado = fuente('views/IndicadoresView.vue')
  assert.doesNotMatch(listado, /responsableSeleccionado/)
  assert.doesNotMatch(listado, /Sin responsable/)
  assert.doesNotMatch(listado, /textoResponsables/)
})

test('C2: el formulario y el detalle muestran el inicio real del seguimiento', () => {
  const formulario = fuente('components/mediciones/MedicionForm.vue')
  const detalle = fuente('components/indicadores/IndicadorDetalle.vue')

  assert.match(formulario, /v-if="estado\.periodo\.periodo_parcial"/)
  assert.match(formulario, /formatearFechaIso\(estado\.periodo\.inicio_seguimiento\)/)
  assert.match(detalle, /Seguimiento desde/)
  assert.match(detalle, /formatearFechaIso\(indicador\.fecha_inicio_seguimiento\)/)
})
