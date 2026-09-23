<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import ConfirmacionModal from '../components/common/ConfirmacionModal.vue'
import UserModal from '../components/configuracion/UserModal.vue'
import {
  actualizarUsuario,
  crearUsuario,
  inactivarUsuario as inactivarUsuarioService,
  obtenerRoles,
  obtenerUsuarios,
} from '../services/usuarioService'
import {
  aprobarSolicitudRestablecimiento,
  asignarPasswordTemporal,
  obtenerSolicitudesRestablecimiento,
  rechazarSolicitudRestablecimiento,
} from '../services/solicitudRestablecimientoService'
import { puedeGestionarUsuarios } from '../utils/permisos'
import { useConfirmacion } from '../composables/useConfirmacion'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const route = useRoute()
const router = useRouter()

const puedeGestionar = computed(() => puedeGestionarUsuarios(props.usuario))

const tabActiva = ref('usuarios')

const usuarios = ref([])
const roles = ref([])
const cargando = ref(false)
const error = ref('')
const mensaje = ref('')

const {
  solicitud: confirmacion,
  solicitar: solicitarConfirmacion,
  cancelar: cancelarConfirmacion,
  confirmar: confirmarAccionPendiente,
} = useConfirmacion()

const busquedaUsuarios = ref('')

const modalUsuarioAbierto = ref(false)
const usuarioSeleccionado = ref(null)
const guardandoUsuario = ref(false)
const errorModalUsuario = ref('')

const solicitudes = ref([])
const cargandoSolicitudes = ref(false)
const errorSolicitudes = ref('')
const solicitudResaltada = ref(null)
let timeoutSolicitudResaltada = null

const busquedaSolicitudes = ref('')

const totalUsuarios = computed(() => usuarios.value.length)

const usuariosActivos = computed(() => {
  return usuarios.value.filter(
    (item) => item.estado === true || item.is_active === true
  ).length
})

const usuariosInactivos = computed(() => {
  return usuarios.value.filter(
    (item) => item.estado === false || item.is_active === false
  ).length
})

const usuariosFiltrados = computed(() => {
  const termino = busquedaUsuarios.value.trim().toLowerCase()

  if (!termino) {
    return usuarios.value
  }

  return usuarios.value.filter((item) => {
    const nombreCompleto = `${item.first_name || ''} ${item.last_name || ''}`.toLowerCase()
    const username = String(item.username || '').toLowerCase()
    const correo = String(item.email || item.correo || '').toLowerCase()
    const rol = String(rolNombre(item.rol) || item.rol_nombre || item.nombre_rol || '').toLowerCase()
    const estado = textoEstadoUsuario(item).toLowerCase()

    return (
      username.includes(termino) ||
      nombreCompleto.includes(termino) ||
      correo.includes(termino) ||
      rol.includes(termino) ||
      estado.includes(termino)
    )
  })
})

const solicitudesPendientes = computed(() => {
  return solicitudes.value.filter((s) => s.estado === 'pendiente').length
})

const solicitudesAprobadas = computed(() => {
  return solicitudes.value.filter((s) => s.estado === 'aprobada').length
})

const solicitudesRechazadas = computed(() => {
  return solicitudes.value.filter((s) => s.estado === 'rechazada').length
})

const solicitudesAtendidas = computed(() => {
  return solicitudes.value.filter((s) => s.estado === 'atendida').length
})

const solicitudesFiltradas = computed(() => {
  const termino = busquedaSolicitudes.value.trim().toLowerCase()

  if (!termino) {
    return solicitudes.value
  }

  return solicitudes.value.filter((item) => {
    const username = String(item.usuario_username || '').toLowerCase()
    const nombre = String(item.usuario_nombre || '').toLowerCase()
    const correo = String(item.usuario_correo || '').toLowerCase()
    const identificador = String(item.identificador_ingresado || '').toLowerCase()
    const motivo = String(item.motivo || '').toLowerCase()
    const estado = String(item.estado || '').toLowerCase()

    return (
      username.includes(termino) ||
      nombre.includes(termino) ||
      correo.includes(termino) ||
      identificador.includes(termino) ||
      motivo.includes(termino) ||
      estado.includes(termino)
    )
  })
})

async function cargarUsuariosYRoles() {
  if (!puedeGestionar.value) {
    return
  }

  cargando.value = true
  error.value = ''

  try {
    const [usuariosData, rolesData] = await Promise.all([
      obtenerUsuarios(),
      obtenerRoles(),
    ])

    usuarios.value = usuariosData
    roles.value = rolesData
  } catch (e) {
    error.value = 'No se pudieron cargar los usuarios.'
  } finally {
    cargando.value = false
  }
}

async function cargarSolicitudesRestablecimiento() {
  if (!puedeGestionar.value) {
    return
  }

  cargandoSolicitudes.value = true
  errorSolicitudes.value = ''

  try {
    solicitudes.value = await obtenerSolicitudesRestablecimiento()
  } catch (e) {
    errorSolicitudes.value = obtenerMensajeError(
      e,
      'No se pudieron cargar las solicitudes de restablecimiento.'
    )
  } finally {
    cargandoSolicitudes.value = false
  }
}

async function cambiarTab(tab) {
  tabActiva.value = tab

  await router.replace({
    path: '/usuarios',
    query: tab === 'solicitudes' ? { tab: 'solicitudes' } : {},
  })

  if (tab === 'solicitudes') {
    await cargarSolicitudesRestablecimiento()
  }
}

async function aplicarResaltadoSolicitudDesdeRuta() {
  const idQuery = Number(route.query.resaltarSolicitud)

  if (!idQuery) {
    return
  }

  tabActiva.value = 'solicitudes'

  await cargarSolicitudesRestablecimiento()

  solicitudResaltada.value = idQuery

  await nextTick()

  const fila = document.getElementById(`fila-solicitud-${idQuery}`)

  if (fila) {
    fila.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    })
  }

  if (timeoutSolicitudResaltada) {
    window.clearTimeout(timeoutSolicitudResaltada)
  }

  timeoutSolicitudResaltada = window.setTimeout(() => {
    if (solicitudResaltada.value === idQuery) {
      solicitudResaltada.value = null
    }
  }, 3500)
}

watch(
  () => route.query.tab,
  async (tab) => {
    tabActiva.value = tab === 'solicitudes' ? 'solicitudes' : 'usuarios'

    if (tabActiva.value === 'solicitudes' && puedeGestionar.value) {
      await cargarSolicitudesRestablecimiento()
    }
  },
  { immediate: true }
)

watch(
  () => route.query.resaltarSolicitud,
  () => {
    aplicarResaltadoSolicitudDesdeRuta()
  }
)

function textoEstadoSolicitud(estado) {
  const mapa = {
    pendiente: 'Pendiente',
    aprobada: 'Aprobada',
    rechazada: 'Rechazada',
    atendida: 'Atendida',
  }

  return mapa[estado] || estado || 'Sin estado'
}

function claseEstadoSolicitud(estado) {
  return {
    'status-pending': estado === 'pendiente',
    'status-active': estado === 'aprobada',
    'status-inactive': estado === 'rechazada',
    'status-done': estado === 'atendida',
  }
}

function manejarAprobarSolicitud(solicitud) {
  solicitarConfirmacion({
    titulo: 'Aprobar solicitud',
    mensaje: `¿Confirmás aprobar la solicitud de "${solicitud.usuario_username}"?`,
    textoConfirmar: 'Aprobar',
    variante: 'normal',
    accion: () => ejecutarAprobarSolicitud(solicitud),
  })
}

async function ejecutarAprobarSolicitud(solicitud) {
  const observacion = window.prompt('Observación administrativa opcional:', '')

  error.value = ''
  mensaje.value = ''

  try {
    await aprobarSolicitudRestablecimiento(solicitud.id, { observacion_admin: observacion || '' })
    mensaje.value = 'Solicitud aprobada correctamente.'
    await cargarSolicitudesRestablecimiento()
  } catch (e) {
    error.value = obtenerMensajeError(e, 'No se pudo aprobar la solicitud.')
  }
}

function manejarRechazarSolicitud(solicitud) {
  solicitarConfirmacion({
    titulo: 'Rechazar solicitud',
    mensaje: `¿Confirmás rechazar la solicitud de "${solicitud.usuario_username}"?`,
    textoConfirmar: 'Rechazar',
    variante: 'advertencia',
    accion: () => ejecutarRechazarSolicitud(solicitud),
  })
}

async function ejecutarRechazarSolicitud(solicitud) {
  const observacion = window.prompt('Motivo del rechazo:', '')

  error.value = ''
  mensaje.value = ''

  try {
    await rechazarSolicitudRestablecimiento(solicitud.id, { observacion_admin: observacion || '' })
    mensaje.value = 'Solicitud rechazada correctamente.'
    await cargarSolicitudesRestablecimiento()
  } catch (e) {
    error.value = obtenerMensajeError(e, 'No se pudo rechazar la solicitud.')
  }
}

function manejarAsignarPasswordTemporal(solicitud) {
  const passwordTemporal = window.prompt('Ingrese la contraseña temporal:', '')

  if (!passwordTemporal || !passwordTemporal.trim()) {
    return
  }

  solicitarConfirmacion({
    titulo: 'Asignar contraseña temporal',
    mensaje: '¿Confirmás asignar esta contraseña temporal?',
    textoSecundario: 'El usuario deberá cambiarla al iniciar sesión.',
    textoConfirmar: 'Asignar',
    variante: 'advertencia',
    accion: () => ejecutarAsignarPasswordTemporal(solicitud, passwordTemporal),
  })
}

async function ejecutarAsignarPasswordTemporal(solicitud, passwordTemporal) {
  error.value = ''
  mensaje.value = ''

  try {
    await asignarPasswordTemporal(solicitud.id, { password_temporal: passwordTemporal })
    mensaje.value = 'Contraseña temporal asignada correctamente.'
    await cargarSolicitudesRestablecimiento()
  } catch (e) {
    error.value = obtenerMensajeError(e, 'No se pudo asignar la contraseña temporal.')
  }
}

function abrirNuevoUsuario() {
  usuarioSeleccionado.value = null
  modalUsuarioAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalUsuario.value = ''
}

function abrirEditarUsuario(usuario) {
  usuarioSeleccionado.value = usuario
  modalUsuarioAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalUsuario.value = ''
}

function cerrarModalUsuario() {
  modalUsuarioAbierto.value = false
  usuarioSeleccionado.value = null
  guardandoUsuario.value = false
  errorModalUsuario.value = ''
}

function obtenerMensajeError(e, mensajeDefault) {
  const data = e.response?.data

  if (data?.detail) {
    return data.detail
  }

  if (typeof data === 'object' && data !== null) {
    const primerCampo = Object.keys(data)[0]
    const mensajeCampo = data[primerCampo]

    return Array.isArray(mensajeCampo)
      ? mensajeCampo.join(' ')
      : String(mensajeCampo)
  }

  return mensajeDefault
}

async function guardarUsuario(payload) {
  guardandoUsuario.value = true
  errorModalUsuario.value = ''
  mensaje.value = ''

  try {
    if (usuarioSeleccionado.value?.id) {
      await actualizarUsuario(usuarioSeleccionado.value.id, payload)
      mensaje.value = 'Usuario actualizado correctamente.'
    } else {
      await crearUsuario(payload)
      mensaje.value = 'Usuario creado correctamente.'
    }

    cerrarModalUsuario()
    await cargarUsuariosYRoles()
  } catch (e) {
    errorModalUsuario.value = obtenerMensajeError(
      e,
      usuarioSeleccionado.value?.id
        ? 'No se pudo actualizar el usuario.'
        : 'No se pudo crear el usuario.'
    )
  } finally {
    guardandoUsuario.value = false
  }
}

function esUsuarioActual(item) {
  return Number(item.id) === Number(props.usuario?.id)
}

function manejarInactivarUsuario(usuario) {
  if (Number(usuario.id) === Number(props.usuario?.id)) {
    mensaje.value = 'No podés inactivar tu propia cuenta.'
    return
  }

  solicitarConfirmacion({
    titulo: 'Inactivar usuario',
    mensaje: `¿Deseás inactivar al usuario "${usuario.username}"?`,
    textoSecundario: 'El usuario dejará de poder iniciar sesión en el sistema.',
    textoConfirmar: 'Inactivar',
    variante: 'peligrosa',
    accion: () => ejecutarInactivarUsuario(usuario),
  })
}

async function ejecutarInactivarUsuario(usuario) {
  error.value = ''
  mensaje.value = ''

  try {
    await inactivarUsuarioService(usuario.id)
    mensaje.value = 'Usuario inactivado correctamente.'
    await cargarUsuariosYRoles()
  } catch (e) {
    error.value = obtenerMensajeError(e, 'No se pudo inactivar el usuario.')
  }
}

async function manejarReactivarUsuario(usuario) {
  error.value = ''
  mensaje.value = ''

  try {
    await actualizarUsuario(usuario.id, { estado: true, is_active: true })
    mensaje.value = 'Usuario reactivado correctamente.'
    await cargarUsuariosYRoles()
  } catch (e) {
    error.value = obtenerMensajeError(e, 'No se pudo reactivar el usuario.')
  }
}

function rolNombre(rolId) {
  const rol = roles.value.find((item) => Number(item.id) === Number(rolId))
  return rol?.nombre || 'Sin rol'
}

function textoEstadoUsuario(usuario) {
  return usuario.estado === false || usuario.is_active === false ? 'Inactivo' : 'Activo'
}

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

function cerrarSesion() {
  emit('logout')
}

onMounted(async () => {
  await Promise.all([
    cargarUsuariosYRoles(),
    cargarSolicitudesRestablecimiento(),
  ])

  await aplicarResaltadoSolicitudDesdeRuta()
})

onBeforeUnmount(() => {
  if (timeoutSolicitudResaltada) {
    window.clearTimeout(timeoutSolicitudResaltada)
  }
})
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Gestión de usuarios"
    subtitulo="Administra las cuentas de acceso al sistema y su rol dentro de la cooperativa."
    breadcrumb-actual="Usuarios"
    @logout="cerrarSesion"
  >
    <template v-if="puedeGestionar && tabActiva === 'usuarios'" #actions>
      <button class="btn-primary" type="button" @click="abrirNuevoUsuario">
        + Nuevo usuario
      </button>
    </template>

    <div v-if="!puedeGestionar" class="card-panel restricted-panel">
      <h2>No tenés permisos para gestionar usuarios.</h2>
      <p>Esta sección está disponible únicamente para administración del sistema.</p>
    </div>

    <template v-else>
      <div class="tabs">
        <button
          class="tab-btn"
          type="button"
          :class="{ active: tabActiva === 'usuarios' }"
          @click="cambiarTab('usuarios')"
        >
          Usuarios
        </button>

        <button
          class="tab-btn"
          type="button"
          :class="{ active: tabActiva === 'solicitudes' }"
          @click="cambiarTab('solicitudes')"
        >
          Solicitudes de restablecimiento
        </button>
      </div>

      <div v-if="mensaje" class="alert success">
        {{ mensaje }}
      </div>

      <div v-if="error" class="alert error">
        {{ error }}
      </div>

      <section v-if="tabActiva === 'usuarios'" class="summary-grid">
        <article class="summary-card">
          <span>Total de usuarios</span>
          <strong>{{ totalUsuarios }}</strong>
          <p>Cuentas registradas en el sistema</p>
        </article>

        <article class="summary-card">
          <span>Activos</span>
          <strong>{{ usuariosActivos }}</strong>
          <p>Pueden iniciar sesión actualmente</p>
        </article>

        <article class="summary-card">
          <span>Inactivos</span>
          <strong>{{ usuariosInactivos }}</strong>
          <p>Conservados para historial</p>
        </article>
      </section>

      <section v-if="tabActiva === 'usuarios'" class="card-panel">
        <div class="panel-head">
          <div>
            <h2>Listado de usuarios</h2>
            <p>Consulta general de cuentas registradas.</p>
          </div>
        </div>

        <div class="search-box">
          <input
            v-model="busquedaUsuarios"
            type="text"
            placeholder="Buscar por usuario, nombre, correo, rol o estado..."
          />
        </div>

        <div v-if="cargando" class="message">
          Cargando usuarios...
        </div>

        <div v-else-if="!usuariosFiltrados.length" class="empty-state">
          No hay usuarios para mostrar.
        </div>

        <table v-else>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Nombre completo</th>
              <th>Rol</th>
              <th>Correo</th>
              <th>Registrado</th>
              <th>Estado</th>
              <th style="text-align: right;">Acciones</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="item in usuariosFiltrados"
              :key="item.id"
            >
              <td>
                <div class="cell-main">{{ item.username }}</div>
              </td>

              <td>
                <div class="cell-main">
                  {{ `${item.first_name || ''} ${item.last_name || ''}`.trim() || 'Sin nombre' }}
                </div>
              </td>

              <td>
                <span class="role-chip">
                  {{ rolNombre(item.rol) }}
                </span>
              </td>

              <td>
                <div class="cell-sub">{{ item.correo || item.email || 'Sin correo' }}</div>
              </td>

              <td>{{ formatearFecha(item.date_joined) }}</td>

              <td>
                <span
                  class="status-chip"
                  :class="{ inactive: item.estado === false || item.is_active === false }"
                >
                  {{ textoEstadoUsuario(item) }}
                </span>
              </td>

              <td>
                <div class="actions-cell">
                  <button
                    class="action-icon-btn"
                    type="button"
                    title="Editar"
                    aria-label="Editar"
                    @click="abrirEditarUsuario(item)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" />
                    </svg>
                  </button>

                  <div v-if="esUsuarioActual(item)" class="current-user-info">
                    <span class="current-user-chip">Usuario actual</span>
                    <small class="current-user-note">No podés inactivar tu propia cuenta.</small>
                  </div>

                  <button
                    v-else-if="item.estado !== false"
                    class="action-btn danger"
                    type="button"
                    @click="manejarInactivarUsuario(item)"
                  >
                    Inactivar
                  </button>

                  <button
                    v-else
                    class="action-btn"
                    type="button"
                    @click="manejarReactivarUsuario(item)"
                  >
                    Reactivar
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="tabActiva === 'solicitudes'" class="summary-grid">
        <article class="summary-card">
          <span>Pendientes</span>
          <strong>{{ solicitudesPendientes }}</strong>
          <p>Esperando revisión administrativa</p>
        </article>

        <article class="summary-card">
          <span>Aprobadas</span>
          <strong>{{ solicitudesAprobadas }}</strong>
          <p>Falta asignar contraseña temporal</p>
        </article>

        <article class="summary-card">
          <span>Rechazadas</span>
          <strong>{{ solicitudesRechazadas }}</strong>
          <p>No autorizadas por administración</p>
        </article>

        <article class="summary-card">
          <span>Atendidas</span>
          <strong>{{ solicitudesAtendidas }}</strong>
          <p>Con contraseña temporal asignada</p>
        </article>
      </section>

      <section v-if="tabActiva === 'solicitudes'" class="card-panel">
        <div class="panel-head">
          <div>
            <h2>Solicitudes de restablecimiento</h2>
            <p>Usuarios que solicitaron restablecer su contraseña por no poder iniciar sesión.</p>
          </div>

          <button
            class="action-btn"
            type="button"
            :disabled="cargandoSolicitudes"
            @click="cargarSolicitudesRestablecimiento"
          >
            Actualizar
          </button>
        </div>

        <div class="search-box">
          <input
            v-model="busquedaSolicitudes"
            type="text"
            placeholder="Buscar por usuario, correo, motivo o estado..."
          />
        </div>

        <div v-if="cargandoSolicitudes" class="message">
          Cargando solicitudes...
        </div>

        <div v-else-if="errorSolicitudes" class="alert error">
          {{ errorSolicitudes }}
        </div>

        <div v-else-if="!solicitudesFiltradas.length" class="empty-state">
          No hay solicitudes de restablecimiento para mostrar.
        </div>

        <table v-else>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Identificador ingresado</th>
              <th>Motivo</th>
              <th>Estado</th>
              <th>Fecha solicitud</th>
              <th>Revisado por</th>
              <th>Atendido por</th>
              <th style="text-align: right;">Acciones</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="solicitud in solicitudesFiltradas"
              :key="solicitud.id"
              :id="`fila-solicitud-${solicitud.id}`"
              :class="{ 'highlight-row': solicitudResaltada === Number(solicitud.id) }"
            >
              <td>
                <div class="cell-main">{{ solicitud.usuario_username }}</div>
                <div class="cell-sub">{{ solicitud.usuario_nombre }}</div>
                <div class="cell-sub">{{ solicitud.usuario_correo }}</div>
              </td>

              <td>
                <div class="cell-sub">{{ solicitud.identificador_ingresado }}</div>
              </td>

              <td>
                <div class="cell-sub">{{ solicitud.motivo || 'Sin motivo' }}</div>
              </td>

              <td>
                <span class="status-chip" :class="claseEstadoSolicitud(solicitud.estado)">
                  {{ textoEstadoSolicitud(solicitud.estado) }}
                </span>
              </td>

              <td>{{ formatearFecha(solicitud.fecha_solicitud) }}</td>

              <td>
                <div class="cell-sub">{{ solicitud.revisado_por_nombre || 'Sin revisar' }}</div>
              </td>

              <td>
                <div class="cell-sub">{{ solicitud.atendido_por_nombre || 'Sin atender' }}</div>
              </td>

              <td>
                <div class="actions-cell">
                  <template v-if="solicitud.estado === 'pendiente'">
                    <button
                      class="action-btn"
                      type="button"
                      @click="manejarAprobarSolicitud(solicitud)"
                    >
                      Aprobar
                    </button>

                    <button
                      class="action-btn danger"
                      type="button"
                      @click="manejarRechazarSolicitud(solicitud)"
                    >
                      Rechazar
                    </button>

                    <button
                      class="action-btn"
                      type="button"
                      @click="manejarAsignarPasswordTemporal(solicitud)"
                    >
                      Asignar contraseña temporal
                    </button>
                  </template>

                  <button
                    v-else-if="solicitud.estado === 'aprobada'"
                    class="action-btn"
                    type="button"
                    @click="manejarAsignarPasswordTemporal(solicitud)"
                  >
                    Asignar contraseña temporal
                  </button>

                  <span v-else class="cell-sub">Sin acciones disponibles</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <ModalBase
        :abierto="modalUsuarioAbierto"
        :titulo="usuarioSeleccionado ? 'Editar usuario' : 'Nuevo usuario'"
        :subtitulo="
          usuarioSeleccionado
            ? 'Actualiza los datos generales del usuario.'
            : 'Registra un usuario para acceder al sistema.'
        "
        @cerrar="cerrarModalUsuario"
      >
        <div v-if="errorModalUsuario" class="alert error">
          {{ errorModalUsuario }}
        </div>

        <UserModal
          :usuario="usuarioSeleccionado"
          :roles="roles"
          @guardar="guardarUsuario"
          @cancelar="cerrarModalUsuario"
        />

        <div v-if="guardandoUsuario" class="saving-message">
          Guardando usuario...
        </div>
      </ModalBase>

      <ConfirmacionModal
        :abierto="!!confirmacion"
        :titulo="confirmacion?.titulo"
        :mensaje="confirmacion?.mensaje"
        :texto-secundario="confirmacion?.textoSecundario"
        :texto-confirmar="confirmacion?.textoConfirmar"
        :texto-cancelar="confirmacion?.textoCancelar"
        :variante="confirmacion?.variante"
        @confirmar="confirmarAccionPendiente"
        @cancelar="cancelarConfirmacion"
      />
    </template>
  </AppLayout>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card,
.card-panel {
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 14px;
  box-shadow: 0 8px 22px rgba(29, 53, 87, 0.07);
}

.summary-card {
  padding: 20px;
}

.summary-card span {
  color: #457b9d;
  font-size: 13px;
  font-weight: 800;
}

.summary-card strong {
  display: block;
  color: #1d3557;
  font-size: 34px;
  margin-top: 10px;
}

.summary-card p {
  margin: 6px 0 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 600;
}

.card-panel {
  padding: 22px;
}

.restricted-panel {
  text-align: center;
  padding: 40px 22px;
}

.restricted-panel h2 {
  margin: 0 0 8px;
  color: #1d3557;
  font-size: 17px;
  font-weight: 800;
}

.restricted-panel p {
  margin: 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 600;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.panel-head h2 {
  margin: 0;
  color: #1d3557;
  font-size: 17px;
  font-weight: 800;
}

.panel-head p {
  margin: 4px 0 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 500;
}

.btn-primary {
  height: 40px;
  padding: 0 16px;
  border: none;
  border-radius: 10px;
  background: #1d3557;
  color: #ffffff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.btn-primary:hover {
  background: #152840;
}

.alert {
  padding: 13px 15px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 750;
  margin-bottom: 18px;
}

.alert.success {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.alert.error {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

.message,
.empty-state {
  padding: 16px;
  border-radius: 12px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 13px;
  font-weight: 700;
}

.actions-cell {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.action-btn {
  height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  color: #457b9d;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 800;
  cursor: pointer;
}

.action-btn:hover {
  background: #eaf5f5;
  border-color: #a8dadc;
}

.action-btn.danger {
  color: #e76f51;
}

.action-btn.danger:hover {
  background: rgba(231, 111, 81, 0.10);
  border-color: rgba(231, 111, 81, 0.25);
}

.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.action-icon-btn {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.action-icon-btn svg {
  stroke: currentColor;
}

.action-icon-btn:hover {
  background: #eaf5f5;
  color: #457b9d;
  border-color: #a8dadc;
}

.current-user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.current-user-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 9px;
  border-radius: 999px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 10.5px;
  font-weight: 850;
}

.current-user-note {
  color: #9aa8b8;
  font-size: 10.5px;
  font-weight: 600;
}

.saving-message {
  margin-top: 12px;
  padding: 11px 13px;
  border-radius: 11px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 12.5px;
  font-weight: 800;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  text-align: left;
  color: #9aa8b8;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 12px 10px;
  border-bottom: 1px solid #e4eaef;
}

td {
  padding: 13px 10px;
  border-bottom: 1px solid #eef2f5;
  color: #1d3557;
  font-size: 13px;
  font-weight: 600;
  vertical-align: top;
}

.cell-main {
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
}

.cell-sub {
  color: #9aa8b8;
  font-size: 12px;
  font-weight: 500;
  max-width: 320px;
}

.role-chip,
.status-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 850;
}

.role-chip {
  background: #eaf5f5;
  color: #457b9d;
}

.status-chip {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.status-chip.inactive {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

.status-chip.status-pending {
  background: rgba(244, 162, 97, 0.16);
  color: #b9701e;
}

.status-chip.status-active {
  background: rgba(69, 123, 157, 0.12);
  color: #457b9d;
}

.status-chip.status-inactive {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

.status-chip.status-done {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 18px;
  border-bottom: 1px solid #e4eaef;
}

.tab-btn {
  height: 40px;
  padding: 0 4px;
  margin-bottom: -1px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: #9aa8b8;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.tab-btn:hover {
  color: #457b9d;
}

.tab-btn.active {
  color: #1d3557;
  border-bottom-color: #1d3557;
}

.search-box {
  margin-bottom: 16px;
}

.search-box input {
  width: 100%;
  max-width: 420px;
  height: 38px;
  padding: 0 12px;
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.search-box input::placeholder {
  color: #9aa8b8;
}

.search-box input:focus {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
}

.highlight-row {
  animation: highlightPulse 3.5s ease;
}

@keyframes highlightPulse {
  0% {
    background: rgba(244, 162, 97, 0.24);
    box-shadow: inset 4px 0 0 #f4a261;
  }

  45% {
    background: rgba(244, 162, 97, 0.18);
    box-shadow: inset 4px 0 0 #f4a261;
  }

  100% {
    background: transparent;
    box-shadow: inset 0 0 0 transparent;
  }
}

@media (max-width: 800px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  table {
    display: block;
    overflow-x: auto;
  }
}
</style>
