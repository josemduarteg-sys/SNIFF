import api from './api'
import { limpiarSesion } from './sesion'

export async function login(username, password) {
    const response = await api.post('auth/login/', {
        username,
        password,
    })

    const { access, refresh } = response.data

    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)

    return response.data
}

export async function obtenerUsuarioActual() {
    const response = await api.get('usuarios/me/')

    localStorage.setItem(
        'debe_cambiar_password',
        response.data.debe_cambiar_password ? 'true' : 'false'
    )

    // Bloque 2: se guarda el nombre de rol para que el guard de rutas
    // (router/index.js) pueda protegerlas de forma síncrona, sin esperar
    // una llamada a la API en cada navegación — mismo patrón ya usado acá
    // para debe_cambiar_password. La autorización real sigue siendo la
    // del backend (ver apps/usuarios/permissions.py); esto es solo para
    // no exponer una pantalla restringida en la navegación.
    localStorage.setItem('rol_nombre', response.data.rol_nombre || '')

    return response.data
}

// Etapa 4 (M7): deja constancia del cierre de sesión explícito en la
// bitácora. Si falla (sin red, token ya vencido), se cierra la sesión igual.
export async function registrarCierreSesion() {
    try {
        await api.post('auth/logout/')
    } catch {
        // El cierre local no depende del servidor.
    }
}

export function logout() {
    // Etapa 2 (A3): mismas claves que limpia la expiración automática.
    limpiarSesion(localStorage)
}

export function estaAutenticado() {
    return !!localStorage.getItem('access_token')
}

export function debeCambiarPassword() {
    return localStorage.getItem('debe_cambiar_password') === 'true'
}

export function obtenerRolAlmacenado() {
    return localStorage.getItem('rol_nombre') || ''
}

export async function solicitarRestablecimientoPassword(payload) {
    const { data } = await api.post('usuarios/solicitar-restablecimiento/', payload)
    return data
}

