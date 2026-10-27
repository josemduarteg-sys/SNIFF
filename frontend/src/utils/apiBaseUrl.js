// Vite sustituye esta configuración al compilar. No incluir secretos.
export function obtenerApiBaseUrl(valor, desarrollo = false) {
  const url = String(valor || '').trim()
  if (!url) return desarrollo ? 'http://127.0.0.1:8000/api/' : '/api/'
  // Evita que rutas como "api/" dependan de la pantalla SPA actual.
  if (!url.startsWith('/') && !/^https?:\/\//i.test(url)) {
    throw new Error('VITE_API_BASE_URL debe ser una URL HTTP(S) o una ruta desde /')
  }
  if (url.startsWith('//') || /[?#]/.test(url)) {
    throw new Error('VITE_API_BASE_URL no admite URL sin esquema, query ni fragmento')
  }
  return url.replace(/\/+$/, '') + '/'
}
