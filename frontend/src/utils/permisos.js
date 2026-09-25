export function obtenerRolUsuario(usuario) {
  const rol =
    usuario?.nombre_rol ||
    usuario?.rol_nombre ||
    usuario?.rol?.nombre ||
    usuario?.rol ||
    usuario?.role ||
    ''

  return String(rol).toLowerCase().trim()
}

export function esAdministrador(usuario) {
  const rol = obtenerRolUsuario(usuario)

  return (
    rol.includes('admin') ||
    rol.includes('administrador')
  )
}

export function esOperativo(usuario) {
  const rol = obtenerRolUsuario(usuario)

  return (
    rol.includes('operativo') ||
    rol.includes('responsable') ||
    rol.includes('supervisor')
  )
}

export function esVisualizador(usuario) {
  const rol = obtenerRolUsuario(usuario)

  return (
    rol.includes('visualizador') ||
    rol.includes('gerencia') ||
    rol.includes('gerente') ||
    rol.includes('consulta')
  )
}

export function puedeGestionarUsuarios(usuario) {
  return esAdministrador(usuario)
}

export function puedeVerBitacora(usuario) {
  return esAdministrador(usuario)
}

export function puedeAutorizarKpi(usuario) {
  return esAdministrador(usuario)
}

export function puedeAnularKpi(usuario) {
  return esAdministrador(usuario)
}

export function puedeCrearKpi(usuario) {
  return esAdministrador(usuario) || esOperativo(usuario)
}

export function puedeEditarKpi(usuario, indicador = null) {
  if (esVisualizador(usuario)) {
    return false
  }

  if (!esAdministrador(usuario) && !esOperativo(usuario)) {
    return false
  }

  if (!indicador) {
    return true
  }

  return indicador.puede_modificarse === true || indicador.estado === 'borrador'
}

export function puedeRegistrarMedicion(usuario) {
  return esAdministrador(usuario) || esOperativo(usuario)
}

export function puedeEditarMedicion(usuario, medicion = null) {
  if (!esAdministrador(usuario) && !esOperativo(usuario)) {
    return false
  }

  if (!medicion) {
    return true
  }

  // Bloque 4: una medición de cierre automático, o una cuyo Plan
  // anual/Plan estratégico esté Cerrado, no puede modificarse. El backend
  // ya aplica esta regla de verdad (ver MedicionSerializer.validate); acá
  // solo se refleja para no mostrar un botón que el backend rechazaría.
  return medicion.puede_modificarse !== false
}

export function puedeSoloConsultar(usuario) {
  return esVisualizador(usuario)
}

export function puedeGestionarPlaneacion(usuario) {
  return esAdministrador(usuario) || esOperativo(usuario)
}

export function puedeGestionarPlanesEstrategicos(usuario) {
  return puedeGestionarPlaneacion(usuario)
}

export function puedeGestionarObjetivosGenerales(usuario) {
  return puedeGestionarPlaneacion(usuario)
}

export function puedeGestionarPlanesAnuales(usuario) {
  return puedeGestionarPlaneacion(usuario)
}

export function puedeGestionarObjetivosEspecificos(usuario) {
  return puedeGestionarPlaneacion(usuario)
}

export function puedeVerAccionesLectura(usuario) {
  return true
}

export function puedeGestionarAreas(usuario) {
  return esAdministrador(usuario)
}
