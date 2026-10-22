// D2: evidencias múltiples por medición. Mismas reglas que el backend
// (que es quien decide): PDF/JPG/JPEG, hasta 10 MB cada archivo y hasta 10
// archivos por operación; sin límite acumulado.

export const EXTENSIONES_EVIDENCIA = ['pdf', 'jpg', 'jpeg']
export const TAMANO_MAXIMO_EVIDENCIA = 10 * 1024 * 1024
export const MAXIMO_EVIDENCIAS_POR_CARGA = 10

// Devuelve '' si la selección es válida; si no, el motivo.
export function validarArchivosEvidencia(archivos) {
  if (archivos.length > MAXIMO_EVIDENCIAS_POR_CARGA) {
    return `Se pueden adjuntar como máximo ${MAXIMO_EVIDENCIAS_POR_CARGA} archivos por operación.`
  }

  for (const archivo of archivos) {
    const extension = archivo.name.split('.').pop()?.toLowerCase()

    if (!EXTENSIONES_EVIDENCIA.includes(extension)) {
      return `"${archivo.name}": solo se permiten archivos PDF, JPG o JPEG.`
    }

    if (archivo.size > TAMANO_MAXIMO_EVIDENCIA) {
      return `"${archivo.name}": el archivo no puede superar los 10 MB.`
    }
  }

  return ''
}

export function formatearTamano(bytes) {
  const kb = (bytes || 0) / 1024

  if (kb < 1024) return `${kb.toFixed(1)} KB`

  return `${(kb / 1024).toFixed(2)} MB`
}

export function extensionDe(nombre) {
  const partes = (nombre || '').split('.')
  return partes.length > 1 ? partes.pop().toUpperCase() : ''
}

// Primer mensaje legible de un error de la API (DRF anida listas y
// diccionarios: por campo y, en listas de archivos, por posición).
export function mensajeErrorEvidencias(error, porDefecto = 'No se pudieron adjuntar las evidencias.') {
  const datos = error?.response?.data

  if (!datos || typeof datos === 'string') return porDefecto

  return primerMensaje(datos) || porDefecto
}

function primerMensaje(valor) {
  if (typeof valor === 'string') return valor
  if (!valor || typeof valor !== 'object') return ''

  for (const interno of Object.values(valor)) {
    const mensaje = primerMensaje(interno)
    if (mensaje) return mensaje
  }

  return ''
}
