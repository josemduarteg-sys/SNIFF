import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFileSync } from 'node:fs'
import { computed, reactive, watch } from 'vue'
import { parse } from '@vue/compiler-sfc'

const leer = ruta => readFileSync(new URL(ruta, import.meta.url), 'utf8')
const formulario = parse(leer('../src/components/planes-estrategicos/PlanEstrategicoForm.vue')).descriptor
const servicio = leer('../src/services/planEstrategicoService.js')
  .replace(/^import api from .*$/m, '').replaceAll('export async function', 'async function')

function cliente() {
  const llamadas = []
  const api = Object.fromEntries(['patch', 'post'].map(metodo => [metodo, async (url, payload) => {
    // La serializaci?n real de JSON elimina undefined, pero conserva null.
    llamadas.push({ metodo, url, payload: JSON.parse(JSON.stringify(payload)) })
    return { data: { id: 1, ...payload } }
  }]))
  return { llamadas, ...new Function('api', servicio + '; return { actualizarPlanEstrategico, crearPlanEstrategico }')(api) }
}

for (const descripcion of ['Descripci?n actualizada', 'Descripci?n original', '']) {
  test(`En uso: formulario y servicio solo env?an descripci?n (${JSON.stringify(descripcion)})`, async () => {
    const plan = { id: 1, estado: 'en_uso', titulo: 'Plan', descripcion: 'Descripci?n original', fecha_inicio: '2026-01-01', fecha_fin: '2026-12-31' }
    let emitido
    const codigo = formulario.scriptSetup.content.replace(/^import .* from 'vue'$/m, '')
    const form = new Function('computed', 'reactive', 'watch', 'defineProps', 'defineEmits', codigo + '; return { estado, guardar }')(
      computed, reactive, watch, () => ({ plan }), () => (evento, payload) => { emitido = { evento, payload } },
    )
    form.estado.descripcion = descripcion
    // Incluso si el estado interno cambia, no deben viajar campos bloqueados.
    form.estado.titulo = 'Cambio accidental'
    form.estado.fecha_inicio = '2026-02-01'
    form.guardar()
    assert.equal(emitido.evento, 'guardar')
    assert.deepEqual(emitido.payload, { descripcion })
    const c = cliente()
    await c.actualizarPlanEstrategico(1, emitido.payload)
    assert.deepEqual(c.llamadas, [{ metodo: 'patch', url: 'planes-estrategicos/1/', payload: { descripcion } }])
  })
}

test('creaci?n y borrador conservan t?tulo y fechas expl?citas, incluyendo borrado con null', async () => {
  const c = cliente()
  const payload = { titulo: 'Plan nuevo', descripcion: '', fecha_inicio: '2026-01-01', fecha_fin: '2026-12-31' }
  await c.crearPlanEstrategico(payload)
  assert.deepEqual(c.llamadas[0].payload, payload)
  await c.actualizarPlanEstrategico(1, { fecha_fin: '' })
  assert.deepEqual(c.llamadas[1].payload, { fecha_fin: null })
})

test('controles bloqueados, descripci?n habilitada y sin recuadro redundante', () => {
  const template = formulario.template.content
  assert.equal((template.match(/:disabled="esEnUso"/g) || []).length, 3)
  assert.doesNotMatch(template.match(/<textarea[\s\S]*?>/)[0], /disabled/)
  assert.doesNotMatch(template, /help-box/)
})
