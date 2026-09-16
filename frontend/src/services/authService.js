import api from './api'

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

    return response.data
}

export function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('debe_cambiar_password')
}

export function estaAutenticado() {
    return !!localStorage.getItem('access_token')
}

export function debeCambiarPassword() {
    return localStorage.getItem('debe_cambiar_password') === 'true'
}

export async function solicitarRestablecimientoPassword(payload) {
    const { data } = await api.post('usuarios/solicitar-restablecimiento/', payload)
    return data
}

