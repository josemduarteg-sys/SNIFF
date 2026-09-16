<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import UserModal from '../components/configuracion/UserModal.vue'
import {
  actualizarUsuario,
  crearUsuario,
  inactivarUsuario as inactivarUsuarioService,
  obtenerRoles,
  obtenerUsuarios,
} from '../services/usuarioService'
import { puedeGestionarUsuarios } from '../utils/permisos'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const puedeGestionar = computed(() => puedeGestionarUsuarios(props.usuario))

const usuarios = ref([])
const roles = ref([])
const cargando = ref(false)
const error = ref('')
const mensaje = ref('')

const modalUsuarioAbierto = ref(false)
const usuarioSeleccionado = ref(null)
const guardandoUsuario = ref(false)
const errorModalUsuario = ref('')

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

async function manejarInactivarUsuario(usuario) {
  if (Number(usuario.id) === Number(props.usuario?.id)) {
    mensaje.value = 'No podés inactivar tu propia cuenta.'
    return
  }

  const confirmar = window.confirm(
    `¿Seguro que querés inactivar al usuario "${usuario.username}"?`
  )

  if (!confirmar) return

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

onMounted(() => {
  cargarUsuariosYRoles()
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
    <template v-if="puedeGestionar" #actions>
      <button class="btn-primary" type="button" @click="abrirNuevoUsuario">
        + Nuevo usuario
      </button>
    </template>

    <div v-if="!puedeGestionar" class="card-panel restricted-panel">
      <h2>No tenés permisos para gestionar usuarios.</h2>
      <p>Esta sección está disponible únicamente para administración del sistema.</p>
    </div>

    <template v-else>
      <div v-if="mensaje" class="alert success">
        {{ mensaje }}
      </div>

      <div v-if="error" class="alert error">
        {{ error }}
      </div>

      <section class="summary-grid">
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

      <section class="card-panel">
        <div class="panel-head">
          <div>
            <h2>Listado de usuarios</h2>
            <p>Consulta general de cuentas registradas.</p>
          </div>
        </div>

        <div v-if="cargando" class="message">
          Cargando usuarios...
        </div>

        <div v-else-if="!usuarios.length" class="empty-state">
          No hay usuarios registrados todavía.
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
              v-for="item in usuarios"
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
                    class="action-btn"
                    type="button"
                    @click="abrirEditarUsuario(item)"
                  >
                    Editar
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
