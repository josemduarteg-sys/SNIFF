// D2: evidencias múltiples (src/utils/evidencias.js), el formulario, el
// detalle de la medición y el servicio. `npm test`.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import {
  extensionDe,
  formatearTamano,
  mensajeErrorEvidencias,
  validarArchivosEvidencia,
} from '../src/utils/evidencias.js'

const archivo = (name, size = 1000) => ({ name, size })
const leer = (ruta) => readFileSync(new URL(ruta, import.meta.url), 'utf8')

test('acepta PDF, JPG y JPEG de hasta 10 MB, hasta 10 por vez', () => {
  assert.equal(validarArchivosEvidencia([archivo('a.pdf'), archivo('b.JPG'), archivo('c.jpeg')]), '')
  assert.equal(validarArchivosEvidencia([archivo('limite.pdf', 10 * 1024 * 1024)]), '')
  assert.equal(validarArchivosEvidencia(Array.from({ length: 10 }, (_, i) => archivo(`${i}.pdf`))), '')
})

test('rechaza otros tipos, archivos grandes y más de 10 por operación', () => {
  assert.match(validarArchivosEvidencia([archivo('a.pdf'), archivo('informe.docx')]), /informe\.docx.*PDF, JPG o JPEG/)
  assert.match(validarArchivosEvidencia([archivo('grande.pdf', 10 * 1024 * 1024 + 1)]), /10 MB/)
  assert.match(
    validarArchivosEvidencia(Array.from({ length: 11 }, (_, i) => archivo(`${i}.pdf`))),
    /como máximo 10 archivos/,
  )
})

test('formato de tamaño, extensión y errores anidados de la API', () => {
  assert.equal(formatearTamano(2048), '2.0 KB')
  assert.equal(formatearTamano(3 * 1024 * 1024), '3.00 MB')
  assert.equal(extensionDe('respaldo.final.pdf'), 'PDF')
  assert.equal(extensionDe('sin_extension'), '')

  assert.equal(mensajeErrorEvidencias({ response: { data: { detail: 'Plan Cerrado' } } }), 'Plan Cerrado')
  assert.equal(
    mensajeErrorEvidencias({ response: { data: { archivos: { 1: ['Solo se permiten archivos PDF, JPG o JPEG.'] } } } }),
    'Solo se permiten archivos PDF, JPG o JPEG.',
  )
  assert.equal(mensajeErrorEvidencias({}), 'No se pudieron adjuntar las evidencias.')
})

test('formulario: selección múltiple que se suma a las evidencias anteriores', () => {
  const form = leer('../src/components/mediciones/MedicionForm.vue')

  assert.match(form, /type="file"\s+multiple/)
  assert.match(form, /archivos_evidencia: form\.archivos/)
  assert.match(form, /se suman a las anteriores/)
  assert.doesNotMatch(form, /No puede reemplazarse ni eliminarse/)
})

test('detalle: lista todos los archivos con Ver/Descargar y «Agregar evidencia» solo si corresponde', () => {
  const detalle = leer('../src/components/mediciones/MedicionDetalle.vue')
  const vista = leer('../src/views/MedicionesView.vue')

  assert.match(detalle, /v-for="evidencia in evidencias"/)
  assert.match(detalle, /evidencia\.nombre_original/)
  assert.match(detalle, /evidencia\.subido_por_username/)
  assert.match(detalle, /formatearFechaHora\(evidencia\.fecha_subida\)/)
  assert.match(detalle, /verEvidencia\(evidencia\)/)
  assert.match(detalle, /descargarEvidenciaArchivo\(evidencia\)/)
  assert.match(detalle, /Agregar evidencia/)
  assert.match(detalle, /!props\.medicion\.cierre_automatico/)
  assert.match(vista, /:puede-agregar-evidencia="puedeRegistrar"/)
})

test('servicio: rutas por evidencia y carga de varios archivos', () => {
  const servicio = leer('../src/services/medicionService.js')

  assert.match(servicio, /mediciones\/\$\{medicionId\}\/evidencias\/\$\{evidenciaId\}\/\$\{modo\}\//)
  assert.match(servicio, /formData\.append\('archivos', archivo\)/)
  assert.match(servicio, /formData\.append\('archivos_evidencia', archivo\)/)
  assert.doesNotMatch(servicio, /formData\.append\('evidencia'/)
})
