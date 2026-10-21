import axios from 'axios'

// Etapa 2 (auditoría A3): manejo centralizado del vencimiento del access
// token. Este módulo no depende del navegador ni del router: recibe el
// almacenamiento y la reacción ante una sesión vencida, para poder
// probarse con `node --test` (ver frontend/tests/sesion.test.js).
//
// Flujo ante un 401:
//   1. Si la petición es de autenticación/recuperación, o ya fue
//      reintentada, no se renueva (evita bucles).
//   2. Si hay refresh token, se renueva UNA sola vez aunque varias
//      peticiones fallen a la vez (todas esperan la misma promesa).
//   3. Con el nuevo access token, se reintenta la petición original.
//   4. Si no hay refresh token o la renovación falla, se limpian los datos
//      de sesión y se avisa (una sola vez) para redirigir al login.
//
// La renovación usa el endpoint ya existente /api/auth/refresh/ sin
// cambiar la duración de los tokens. El backend vuelve a validar al
// usuario al renovar (activo y estado vigente) y en cada petición, así que
// renovar nunca devuelve acceso ni permisos que el usuario ya no tiene.

export const CLAVE_ACCESS = 'access_token'
export const CLAVE_REFRESH = 'refresh_token'
export const CLAVES_SESION = [CLAVE_ACCESS, CLAVE_REFRESH, 'debe_cambiar_password', 'rol_nombre']

export const RUTAS_SIN_RENOVACION = [
  'auth/login/',
  'auth/refresh/',
  // Etapa 4: si al cerrar sesión el token ya venció, no tiene sentido renovarlo.
  'auth/logout/',
  'usuarios/solicitar-restablecimiento/',
]

export function limpiarSesion(storage) {
  CLAVES_SESION.forEach((clave) => storage.removeItem(clave))
}

function esRutaSinRenovacion(url = '') {
  return RUTAS_SIN_RENOVACION.some((ruta) => url.includes(ruta))
}

// Ruta interna a la que volver después de iniciar sesión. Solo se aceptan
// rutas relativas del propio sitio ("/algo"), nunca URLs externas
// ("//dominio", "https://...") ni el propio login.
export function esRutaRetornoSegura(ruta) {
  if (typeof ruta !== 'string' || !ruta.startsWith('/') || ruta.startsWith('//')) {
    return false
  }

  if (ruta.includes('\\') || ruta.startsWith('/login') || ruta.startsWith('/cambio-password-obligatorio')) {
    return false
  }

  return true
}

export function configurarRenovacionSesion(api, { storage, alExpirarSesion = () => {}, clienteRenovacion = null }) {
  // Cliente sin interceptores: la llamada de renovación nunca entra al
  // interceptor de 401 de `api`.
  const cliente = clienteRenovacion || axios.create({ baseURL: api.defaults.baseURL })

  let renovacionEnCurso = null
  let sesionExpirada = false

  function expirarSesion() {
    limpiarSesion(storage)

    if (!sesionExpirada) {
      sesionExpirada = true
      alExpirarSesion()
    }
  }

  async function renovarAccessToken() {
    const refresh = storage.getItem(CLAVE_REFRESH)

    if (!refresh) {
      throw new Error('Sin refresh token')
    }

    const { data } = await cliente.post('auth/refresh/', { refresh })

    storage.setItem(CLAVE_ACCESS, data.access)

    // Solo llega si algún día se activa ROTATE_REFRESH_TOKENS.
    if (data.refresh) {
      storage.setItem(CLAVE_REFRESH, data.refresh)
    }

    return data.access
  }

  api.interceptors.request.use((config) => {
    const token = storage.getItem(CLAVE_ACCESS)

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      // Hay sesión de nuevo (inicio de sesión posterior a una expiración):
      // se vuelve a habilitar el aviso de expiración.
      sesionExpirada = false
    }

    return config
  })

  api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const config = error.config
      const status = error.response?.status

      if (status !== 401 || !config || esRutaSinRenovacion(config.url)) {
        return Promise.reject(error)
      }

      if (config._reintentoSesion) {
        expirarSesion()
        return Promise.reject(error)
      }

      try {
        if (!renovacionEnCurso) {
          renovacionEnCurso = renovarAccessToken().finally(() => {
            renovacionEnCurso = null
          })
        }

        const nuevoAccess = await renovacionEnCurso

        config._reintentoSesion = true
        config.headers.Authorization = `Bearer ${nuevoAccess}`

        return api.request(config)
      } catch {
        expirarSesion()
        return Promise.reject(error)
      }
    }
  )

  return api
}
