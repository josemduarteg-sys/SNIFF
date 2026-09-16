<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import api from '../services/api'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const cargando = ref(false)
const guardandoPerfil = ref(false)
const cambiandoPassword = ref(false)

const mensaje = ref('')
const error = ref('')

const perfil = reactive({
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  correo: '',
  rol: '',
  estado: true,
})

const password = reactive({
  password_actual: '',
  nueva_password: '',
  confirmar_password: '',
})

const mostrarPasswordActual = ref(false)
const mostrarNuevaPassword = ref(false)
const mostrarConfirmarPassword = ref(false)

const roles = ref([])

const nombreCompleto = computed(() => {
  const nombre = `${perfil.first_name || ''} ${perfil.last_name || ''}`.trim()
  return nombre || perfil.username || 'Usuario'
})

function cerrarSesion() {
  emit('logout')
}

function limpiarMensajes() {
  mensaje.value = ''
  error.value = ''
}

function normalizarRespuesta(response) {
  if (Array.isArray(response.data)) {
    return response.data
  }

  if (Array.isArray(response.data?.results)) {
    return response.data.results
  }

  return []
}

function asignarPerfil(data) {
  perfil.username = data.username || ''
  perfil.first_name = data.first_name || ''
  perfil.last_name = data.last_name || ''
  perfil.email = data.email || ''
  perfil.correo = data.correo || data.email || ''
  perfil.rol = data.rol || ''
  perfil.estado = data.estado ?? true
}

async function cargarConfiguracion() {
  cargando.value = true
  limpiarMensajes()

  try {
    const responsePerfil = await api.get('usuarios/me/')
    asignarPerfil(responsePerfil.data)

    const responseRoles = await api.get('roles/')
    roles.value = normalizarRespuesta(responseRoles)
  } catch (e) {
    error.value = 'No se pudo cargar la configuración.'
  } finally {
    cargando.value = false
  }
}

function validarPerfil() {
  if (!perfil.first_name.trim()) {
    error.value = 'Ingresá tu nombre.'
    return false
  }

  if (!perfil.last_name.trim()) {
    error.value = 'Ingresá tu apellido.'
    return false
  }

  if (!perfil.correo.trim()) {
    error.value = 'Ingresá tu correo electrónico.'
    return false
  }

  return true
}

async function guardarPerfil() {
  limpiarMensajes()

  if (!validarPerfil()) {
    return
  }

  guardandoPerfil.value = true

  try {
    const payload = {
      first_name: perfil.first_name.trim(),
      last_name: perfil.last_name.trim(),
      email: perfil.correo.trim(),
      correo: perfil.correo.trim(),
    }

    const response = await api.patch('usuarios/me/', payload)
    asignarPerfil(response.data)

    mensaje.value = 'Perfil actualizado correctamente.'
  } catch (e) {
    const data = e.response?.data

    if (typeof data === 'object' && data !== null) {
      const primerCampo = Object.keys(data)[0]
      const mensajeCampo = data[primerCampo]
      error.value = Array.isArray(mensajeCampo)
        ? mensajeCampo.join(' ')
        : String(mensajeCampo)
    } else {
      error.value = 'No se pudo actualizar el perfil.'
    }
  } finally {
    guardandoPerfil.value = false
  }
}

function validarPassword() {
  if (!password.password_actual) {
    error.value = 'Ingresá tu contraseña actual.'
    return false
  }

  if (!password.nueva_password) {
    error.value = 'Ingresá la nueva contraseña.'
    return false
  }

  if (password.nueva_password.length < 8) {
    error.value = 'La nueva contraseña debe tener al menos 8 caracteres.'
    return false
  }

  if (password.nueva_password !== password.confirmar_password) {
    error.value = 'La confirmación no coincide con la nueva contraseña.'
    return false
  }

  return true
}

async function cambiarPassword() {
  limpiarMensajes()

  if (!validarPassword()) {
    return
  }

  cambiandoPassword.value = true

  try {
    await api.post('usuarios/cambiar-password/', {
      password_actual: password.password_actual,
      password_nuevo: password.nueva_password,
      password_confirmacion: password.confirmar_password,
    })

    password.password_actual = ''
    password.nueva_password = ''
    password.confirmar_password = ''

    mensaje.value = 'Contraseña actualizada correctamente.'
  } catch (e) {
    const data = e.response?.data

    if (data?.detail) {
      error.value = data.detail
    } else if (typeof data === 'object' && data !== null) {
      const primerCampo = Object.keys(data)[0]
      const mensajeCampo = data[primerCampo]
      error.value = Array.isArray(mensajeCampo)
        ? mensajeCampo.join(' ')
        : String(mensajeCampo)
    } else {
      error.value = 'No se pudo cambiar la contraseña.'
    }
  } finally {
    cambiandoPassword.value = false
  }
}

function rolNombre(rolId) {
  const rol = roles.value.find((item) => Number(item.id) === Number(rolId))
  return rol?.nombre || rolId || 'Sin rol'
}

onMounted(() => {
  cargarConfiguracion()
})
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Configuración"
    subtitulo="Administra tu perfil y contraseña."
    breadcrumb-actual="Configuración"
    @logout="cerrarSesion"
  >
    <div v-if="mensaje" class="alert success">
      {{ mensaje }}
    </div>

    <div v-if="error" class="alert error">
      {{ error }}
    </div>

    <div v-if="cargando" class="message">
      Cargando configuración...
    </div>

    <template v-else>
      <section class="settings-grid">
        <article class="settings-card profile-card">
          <div class="card-header">
            <div>
              <h3>Mi perfil</h3>
              <p>Actualiza tus datos principales de usuario.</p>
            </div>

            <div class="avatar">
              {{ nombreCompleto.charAt(0).toUpperCase() }}
            </div>
          </div>

          <form class="form-grid" @submit.prevent="guardarPerfil">
            <label class="field">
              <span>Usuario</span>
              <input v-model="perfil.username" type="text" disabled />
            </label>

            <label class="field">
              <span>Rol</span>
              <input :value="rolNombre(perfil.rol)" type="text" disabled />
            </label>

            <label class="field">
              <span>Nombre</span>
              <input v-model="perfil.first_name" type="text" placeholder="Nombre" />
            </label>

            <label class="field">
              <span>Apellido</span>
              <input v-model="perfil.last_name" type="text" placeholder="Apellido" />
            </label>

            <label class="field field-full">
              <span>Correo electrónico</span>
              <input v-model="perfil.correo" type="email" placeholder="correo@ejemplo.com" />
            </label>

            <div class="form-actions field-full">
              <button class="btn-primary" type="submit" :disabled="guardandoPerfil">
                {{ guardandoPerfil ? 'Guardando...' : 'Guardar perfil' }}
              </button>
            </div>
          </form>
        </article>

        <article class="settings-card">
          <div class="card-header">
            <div>
              <h3>Cambiar contraseña</h3>
              <p>Actualiza tu contraseña de acceso al sistema.</p>
            </div>
          </div>

          <form class="form-grid" @submit.prevent="cambiarPassword">
            <label class="field field-full">
              <span>Contraseña actual</span>

              <div class="password-wrapper">
                <input
                  v-model="password.password_actual"
                  :type="mostrarPasswordActual ? 'text' : 'password'"
                  placeholder="Ingresá tu contraseña actual"
                />

                <button
                  class="password-toggle"
                  type="button"
                  @click="mostrarPasswordActual = !mostrarPasswordActual"
                >
                  {{ mostrarPasswordActual ? 'Ocultar' : 'Ver' }}
                </button>
              </div>
            </label>

            <label class="field">
              <span>Nueva contraseña</span>

              <div class="password-wrapper">
                <input
                  v-model="password.nueva_password"
                  :type="mostrarNuevaPassword ? 'text' : 'password'"
                  placeholder="Mínimo 8 caracteres"
                />

                <button
                  class="password-toggle"
                  type="button"
                  @click="mostrarNuevaPassword = !mostrarNuevaPassword"
                >
                  {{ mostrarNuevaPassword ? 'Ocultar' : 'Ver' }}
                </button>
              </div>
            </label>

            <label class="field">
              <span>Confirmar contraseña</span>

              <div class="password-wrapper">
                <input
                  v-model="password.confirmar_password"
                  :type="mostrarConfirmarPassword ? 'text' : 'password'"
                  placeholder="Repetí la nueva contraseña"
                />

                <button
                  class="password-toggle"
                  type="button"
                  @click="mostrarConfirmarPassword = !mostrarConfirmarPassword"
                >
                  {{ mostrarConfirmarPassword ? 'Ocultar' : 'Ver' }}
                </button>
              </div>
            </label>

            <div class="help-box field-full">
              Usá una contraseña segura. Este cambio aplica al próximo inicio de sesión.
            </div>

            <div class="form-actions field-full">
              <button class="btn-primary" type="submit" :disabled="cambiandoPassword">
                {{ cambiandoPassword ? 'Actualizando...' : 'Cambiar contraseña' }}
              </button>
            </div>
          </form>
        </article>
      </section>
    </template>
  </AppLayout>
</template>

<style scoped>
.settings-card,
.settings-card * {
  box-sizing: border-box;
}

.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 18px;
  margin-bottom: 18px;
}

.settings-card {
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(29, 53, 87, 0.05), 0 1px 2px rgba(29, 53, 87, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
}

.card-header h3 {
  margin: 0 0 5px;
  color: #1d3557;
  font-size: 18px;
  font-weight: 850;
}

.card-header p {
  margin: 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 600;
}

.avatar {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: #1d3557;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 850;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.field-full {
  grid-column: 1 / -1;
}

.field span {
  font-size: 12px;
  font-weight: 800;
  color: #1d3557;
}

.field input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  border: 1.5px solid #e4eaef;
  border-radius: 11px;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 13px;
  font-weight: 650;
  outline: none;
  padding: 11px 12px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.field input:focus {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
}

.field input:disabled {
  background: #f4f7f9;
  color: #9aa8b8;
  cursor: not-allowed;
}

.password-wrapper {
  position: relative;
  width: 100%;
}

.password-wrapper input {
  padding-right: 72px;
}

.password-toggle {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  height: 28px;
  padding: 0 10px;
  border: none;
  border-radius: 8px;
  background: #eaf5f5;
  color: #457b9d;
  font-family: inherit;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.password-toggle:hover {
  background: #dceff0;
  color: #1d3557;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  border: none;
  background: #1d3557;
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(29, 53, 87, 0.14);
}

.btn-primary:hover:not(:disabled) {
  background: #152840;
}

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.alert,
.message,
.help-box {
  padding: 13px 15px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 700;
}

.alert {
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
.help-box {
  background: #eaf5f5;
  color: #457b9d;
}

.help-box {
  line-height: 1.45;
  margin-top: 14px;
}

@media (max-width: 980px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .card-header {
    flex-direction: column;
  }

  .form-actions {
    justify-content: stretch;
  }

  .btn-primary {
    width: 100%;
  }
}
</style>
