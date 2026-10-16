import api from './api'

// Bloque 4 (periodos y plazos): plazo adicional (días calendario) para
// registrar una medición después del cierre de su periodo — singleton.

export async function obtenerConfiguracionMediciones() {
  const response = await api.get('configuracion-mediciones/')
  return response.data
}

export async function actualizarConfiguracionMediciones(diasPlazoRegistro) {
  const response = await api.patch('configuracion-mediciones/', {
    dias_plazo_registro: diasPlazoRegistro,
  })
  return response.data
}
