import axios from 'axios'
import { configurarRenovacionSesion } from './sesion'

const api = axios.create({
    baseURL: 'http://127.0.0.1:8000/api/',
    headers: {
        'Content-Type': 'application/json',
    },
})

// Etapa 2 (A3): token en cada petición + renovación centralizada ante 401.
// La reacción visible (volver al login) la registra App.vue con
// registrarAlExpirarSesion, porque es quien conoce el router y el usuario.
let alExpirarSesion = () => {}

export function registrarAlExpirarSesion(callback) {
    alExpirarSesion = callback
}

configurarRenovacionSesion(api, {
    storage: localStorage,
    alExpirarSesion: () => alExpirarSesion(),
})

export default api
