import assert from 'node:assert/strict'
import { test } from 'node:test'
import { obtenerApiBaseUrl } from '../src/utils/apiBaseUrl.js'

test('API configurable: conserva desarrollo y permite mismo origen en producción', () => {
  assert.equal(obtenerApiBaseUrl(undefined, true), 'http://127.0.0.1:8000/api/')
  assert.equal(obtenerApiBaseUrl(undefined, false), '/api/')
  assert.equal(obtenerApiBaseUrl('/api/'), '/api/')
  assert.equal(obtenerApiBaseUrl('https://api.example.invalid/api'), 'https://api.example.invalid/api/')
  assert.equal(obtenerApiBaseUrl(' https://api.example.invalid/api/// '), 'https://api.example.invalid/api/')
})

test('API rechaza rutas dependientes de la pantalla y esquemas inseguros', () => {
  for (const url of ['api/', '//externo/api', 'javascript:alert(1)', 'https://api.example.invalid/api?x=1']) {
    assert.throws(() => obtenerApiBaseUrl(url))
  }
})
