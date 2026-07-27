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
    return response.data
}

export function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
}

export function estaAutenticado() {
    return !!localStorage.getItem('access_token')
}

