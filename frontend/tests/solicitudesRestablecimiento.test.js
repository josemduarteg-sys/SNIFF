// Solicitudes de restablecimiento: acciones visibles según el estado real
// (src/utils/solicitudesRestablecimiento.js) y aprobación sin window.prompt.
// Se ejecuta con `npm test`.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { accionesSolicitud, tieneAcciones } from '../src/utils/solicitudesRestablecimiento.js'

test('Pendiente: solo Aprobar y Rechazar (nunca Asignar contraseña)', () => {
  assert.deepEqual(accionesSolicitud('pendiente'), { aprobar: true, rechazar: true, asignarPassword: false })
})

test('Aprobada sin contraseña: solo Asignar contraseña temporal', () => {
  assert.deepEqual(accionesSolicitud('aprobada'), { aprobar: false, rechazar: false, asignarPassword: true })
})

test('Atendida (contraseña ya asignada) y Rechazada: sin acciones', () => {
  for (const estado of ['atendida', 'rechazada', undefined, 'desconocido']) {
    assert.deepEqual(accionesSolicitud(estado), { aprobar: false, rechazar: false, asignarPassword: false }, estado)
    assert.equal(tieneAcciones(estado), false, estado)
  }

  assert.equal(tieneAcciones('pendiente'), true)
  assert.equal(tieneAcciones('aprobada'), true)
})

test('la pantalla de Usuarios no usa window.prompt y decide los botones por estado', () => {
  const vista = readFileSync(new URL('../src/views/UsuariosView.vue', import.meta.url), 'utf8')

  assert.doesNotMatch(vista, /window\.prompt\s*\(/)
  assert.doesNotMatch(vista, /observacion_admin/)
  assert.match(vista, /v-if="accionesSolicitud\(solicitud\.estado\)\.aprobar"/)
  assert.match(vista, /v-if="accionesSolicitud\(solicitud\.estado\)\.rechazar"/)
  assert.match(vista, /v-if="accionesSolicitud\(solicitud\.estado\)\.asignarPassword"/)
  // "Asignar contraseña temporal" aparece una sola vez como botón de la tabla.
  assert.equal(vista.match(/>\s*Asignar contraseña temporal\s*</g).length, 1)
})
