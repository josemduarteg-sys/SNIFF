// Etapa 2 (A3): pruebas del manejo centralizado de 401 / renovación de
// sesión (src/services/sesion.js). Se ejecutan con `npm test`
// (node --test, incluido en Node: sin dependencias nuevas). El backend se
// simula con un adapter de axios; no hace falta navegador ni servidor.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import axios from 'axios'

import {
  CLAVE_ACCESS,
  CLAVE_REFRESH,
  configurarRenovacionSesion,
  esRutaRetornoSegura,
} from '../src/services/sesion.js'

function crearStorage(inicial = {}) {
  const datos = new Map(Object.entries(inicial))

  return {
    getItem: (clave) => (datos.has(clave) ? datos.get(clave) : null),
    setItem: (clave, valor) => datos.set(clave, String(valor)),
    removeItem: (clave) => datos.delete(clave),
    datos,
  }
}

function respuesta(config, status, data = {}) {
  const resultado = { data, status, statusText: String(status), headers: {}, config }

  if (status >= 400) {
    const error = new axios.AxiosError(`HTTP ${status}`, 'ERR_BAD_REQUEST', config, null, resultado)
    return Promise.reject(error)
  }

  return Promise.resolve(resultado)
}

// Backend simulado: acepta solo el access token vigente.
function crearEntorno({ storage, refreshResponde }) {
  const estado = { accessVigente: 'access-nuevo', llamadasRefresh: 0, peticiones: [] }

  const api = axios.create({
    baseURL: 'http://backend/api/',
    adapter: (config) => {
      estado.peticiones.push({ url: config.url, auth: config.headers.Authorization })

      if (config.url === 'auth/login/') {
        return respuesta(config, 401, { detail: 'credenciales' })
      }

      if (config.headers.Authorization !== `Bearer ${estado.accessVigente}`) {
        return respuesta(config, 401, { detail: 'token vencido' })
      }

      return respuesta(config, 200, { ok: true, url: config.url })
    },
  })

  const clienteRenovacion = {
    post: async (url, body) => {
      estado.llamadasRefresh += 1
      await new Promise((resolve) => setTimeout(resolve, 5))
      return refreshResponde(body, estado)
    },
  }

  let expiraciones = 0
  configurarRenovacionSesion(api, {
    storage,
    clienteRenovacion,
    alExpirarSesion: () => { expiraciones += 1 },
  })

  return { api, estado, expiraciones: () => expiraciones }
}

const refreshValido = async (body) => {
  if (body.refresh !== 'refresh-valido') {
    throw new Error('401')
  }

  return { data: { access: 'access-nuevo' } }
}

const refreshVencido = async () => {
  const error = new Error('Token is invalid or expired')
  error.response = { status: 401 }
  throw error
}

test('1. renueva el access token vencido y reintenta la petición', async () => {
  const storage = crearStorage({ [CLAVE_ACCESS]: 'access-viejo', [CLAVE_REFRESH]: 'refresh-valido' })
  const { api, estado, expiraciones } = crearEntorno({ storage, refreshResponde: refreshValido })

  const { data } = await api.get('notificaciones/')

  assert.equal(data.ok, true)
  assert.equal(storage.getItem(CLAVE_ACCESS), 'access-nuevo')
  assert.equal(estado.llamadasRefresh, 1)
  assert.equal(estado.peticiones.at(-1).auth, 'Bearer access-nuevo')
  assert.equal(expiraciones(), 0)
})

test('2. refresh vencido: limpia la sesión y avisa para volver al login', async () => {
  const storage = crearStorage({
    [CLAVE_ACCESS]: 'access-viejo',
    [CLAVE_REFRESH]: 'refresh-vencido',
    rol_nombre: 'ejecutor operativo',
    debe_cambiar_password: 'false',
  })
  const { api, expiraciones } = crearEntorno({ storage, refreshResponde: refreshVencido })

  await assert.rejects(api.get('notificaciones/'), (error) => error.response.status === 401)

  assert.equal(storage.datos.size, 0)
  assert.equal(expiraciones(), 1)
})

test('2b. sin refresh token: no intenta renovar y expira la sesión', async () => {
  const storage = crearStorage({ [CLAVE_ACCESS]: 'access-viejo' })
  const { api, estado, expiraciones } = crearEntorno({ storage, refreshResponde: refreshValido })

  await assert.rejects(api.get('indicadores-kpi/'))

  assert.equal(estado.llamadasRefresh, 0)
  assert.equal(storage.getItem(CLAVE_ACCESS), null)
  assert.equal(expiraciones(), 1)
})

test('3. varias peticiones 401 simultáneas comparten una sola renovación', async () => {
  const storage = crearStorage({ [CLAVE_ACCESS]: 'access-viejo', [CLAVE_REFRESH]: 'refresh-valido' })
  const { api, estado } = crearEntorno({ storage, refreshResponde: refreshValido })

  const resultados = await Promise.all([
    api.get('planes-estrategicos/'),
    api.get('indicadores-kpi/'),
    api.get('mediciones/'),
    api.get('alertas/'),
  ])

  assert.equal(estado.llamadasRefresh, 1)
  assert.deepEqual(resultados.map((r) => r.data.ok), [true, true, true, true])
})

test('3b. varias peticiones simultáneas con refresh vencido avisan una sola vez', async () => {
  const storage = crearStorage({ [CLAVE_ACCESS]: 'access-viejo', [CLAVE_REFRESH]: 'refresh-vencido' })
  const { api, estado, expiraciones } = crearEntorno({ storage, refreshResponde: refreshVencido })

  const resultados = await Promise.allSettled([
    api.get('planes-estrategicos/'),
    api.get('indicadores-kpi/'),
    api.get('mediciones/'),
  ])

  assert.ok(resultados.every((r) => r.status === 'rejected'))
  assert.equal(estado.llamadasRefresh, 1)
  assert.equal(expiraciones(), 1)
})

test('4. un 401 en el login no dispara renovación (sin bucles)', async () => {
  const storage = crearStorage({ [CLAVE_REFRESH]: 'refresh-valido' })
  const { api, estado, expiraciones } = crearEntorno({ storage, refreshResponde: refreshValido })

  await assert.rejects(api.post('auth/login/', { username: 'x', password: 'y' }))

  assert.equal(estado.llamadasRefresh, 0)
  assert.equal(expiraciones(), 0)
  assert.equal(storage.getItem(CLAVE_REFRESH), 'refresh-valido')
})

test('4a. un 401 al cerrar sesión no dispara renovación (Etapa 4)', async () => {
  const storage = crearStorage({ [CLAVE_ACCESS]: 'access-viejo', [CLAVE_REFRESH]: 'refresh-valido' })
  const { api, estado, expiraciones } = crearEntorno({ storage, refreshResponde: refreshValido })

  await assert.rejects(api.post('auth/logout/'))

  assert.equal(estado.llamadasRefresh, 0)
  assert.equal(expiraciones(), 0)
})

test('4b. si la petición reintentada vuelve a dar 401, no renueva otra vez', async () => {
  const storage = crearStorage({ [CLAVE_ACCESS]: 'access-viejo', [CLAVE_REFRESH]: 'refresh-valido' })
  // El refresh "funciona" pero entrega un token que el backend rechaza
  // (p. ej. usuario desactivado entre ambas llamadas).
  const { api, estado, expiraciones } = crearEntorno({
    storage,
    refreshResponde: async () => ({ data: { access: 'access-rechazado' } }),
  })

  await assert.rejects(api.get('usuarios/me/'))

  assert.equal(estado.llamadasRefresh, 1)
  assert.equal(expiraciones(), 1)
  assert.equal(storage.getItem(CLAVE_ACCESS), null)
})

test('4c. después de expirar, un nuevo inicio de sesión vuelve a habilitar el aviso', async () => {
  const storage = crearStorage({ [CLAVE_ACCESS]: 'access-viejo' })
  const { api, expiraciones } = crearEntorno({ storage, refreshResponde: refreshValido })

  await assert.rejects(api.get('alertas/'))
  storage.setItem(CLAVE_ACCESS, 'access-viejo-2')
  await assert.rejects(api.get('alertas/'))

  assert.equal(expiraciones(), 2)
})

test('5. ruta de retorno: solo rutas internas seguras', () => {
  assert.equal(esRutaRetornoSegura('/indicadores?resaltar=4'), true)
  assert.equal(esRutaRetornoSegura('/mediciones'), true)

  for (const ruta of [
    undefined,
    '',
    'indicadores',
    '//sitio-externo.com',
    'https://sitio-externo.com',
    '/\\sitio-externo.com',
    '/login',
    '/login?redirect=/dashboard',
    '/cambio-password-obligatorio',
  ]) {
    assert.equal(esRutaRetornoSegura(ruta), false, String(ruta))
  }
})
