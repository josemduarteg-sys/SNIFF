// Acciones de una solicitud de restablecimiento según su estado real. La
// aprobación y la asignación de la contraseña temporal son operaciones
// independientes; el backend aplica las mismas reglas (ver
// SolicitudRestablecimientoPasswordViewSet).
//   Pendiente  -> Aprobar y Rechazar.
//   Aprobada   -> Asignar contraseña temporal (una sola vez).
//   Atendida   -> ya tiene contraseña temporal: sin acciones.
//   Rechazada  -> sin acciones.
export function accionesSolicitud(estado) {
  return {
    aprobar: estado === 'pendiente',
    rechazar: estado === 'pendiente',
    asignarPassword: estado === 'aprobada',
  }
}

export function tieneAcciones(estado) {
  return Object.values(accionesSolicitud(estado)).some(Boolean)
}
