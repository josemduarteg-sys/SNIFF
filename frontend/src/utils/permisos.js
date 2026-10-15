// Bloque 2 (correcciones Hernán): los 4 roles definitivos. Los nombres
// deben coincidir EXACTAMENTE (en minúsculas, comparados tras
// obtenerRolUsuario) con los que crea/renombra la migración de backend
// usuarios.0003_adaptar_roles_bloque2_hernan — ver también
// backend/apps/usuarios/permissions.py, que usa los mismos 4 nombres.
const ROL_ADMIN_SISTEMA = 'administrador del sistema'
const ROL_ADMIN_PLANIFICACION = 'administrador de planificación'
const ROL_EJECUTOR_OPERATIVO = 'ejecutor operativo'
const ROL_USUARIO_CONSULTA = 'usuario de consulta'

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

export function esAdministradorSistema(usuario) {
  return obtenerRolUsuario(usuario) === ROL_ADMIN_SISTEMA
}

export function esAdministradorPlanificacion(usuario) {
  return obtenerRolUsuario(usuario) === ROL_ADMIN_PLANIFICACION
}

export function esEjecutorOperativo(usuario) {
  return obtenerRolUsuario(usuario) === ROL_EJECUTOR_OPERATIVO
}

export function esUsuarioConsulta(usuario) {
  return obtenerRolUsuario(usuario) === ROL_USUARIO_CONSULTA
}

// Alias de compatibilidad: antes del Bloque 2, "administrador" conflaba
// sistema+planificación. Ahora apunta explícitamente a Administrador del
// sistema (nunca a planificación) para no reabrir esa conflación por
// accidente — mismo criterio que el alias equivalente en el backend
// (apps/usuarios/permissions.py). No queda ningún uso real tras el
// Bloque 2 (se auditaron los 11 archivos que importan de este módulo).
export function esAdministrador(usuario) {
  return esAdministradorSistema(usuario)
}

export function puedeGestionarUsuarios(usuario) {
  return esAdministradorSistema(usuario)
}

export function puedeVerBitacora(usuario) {
  return esAdministradorSistema(usuario)
}

export function puedeGestionarAreas(usuario) {
  return esAdministradorPlanificacion(usuario)
}

export function puedeAutorizarKpi(usuario) {
  return esAdministradorPlanificacion(usuario)
}

export function puedeAnularKpi(usuario) {
  return esAdministradorPlanificacion(usuario)
}

export function puedeCrearKpi(usuario) {
  return esAdministradorPlanificacion(usuario)
}

export function puedeEditarKpi(usuario, indicador = null) {
  if (!esAdministradorPlanificacion(usuario)) {
    return false
  }

  if (!indicador) {
    return true
  }

  return indicador.puede_modificarse === true || indicador.estado === 'borrador'
}

export function puedeRegistrarMedicion(usuario) {
  return esEjecutorOperativo(usuario)
}

export function puedeEditarMedicion(usuario, medicion = null) {
  if (!esEjecutorOperativo(usuario)) {
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
  return esUsuarioConsulta(usuario)
}

export function puedeGestionarPlaneacion(usuario) {
  return esAdministradorPlanificacion(usuario)
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
