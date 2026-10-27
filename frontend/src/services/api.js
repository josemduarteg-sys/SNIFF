import axios from 'axios'
import { obtenerApiBaseUrl } from '../utils/apiBaseUrl'
import { configurarRenovacionSesion } from './sesion'

const api = axios.create({
    baseURL: obtenerApiBaseUrl(import.meta.env.VITE_API_BASE_URL, import.meta.env.DEV),
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
