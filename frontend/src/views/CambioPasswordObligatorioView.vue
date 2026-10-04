<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import sniffLogo from '../assets/images/sniff-logo.png'
import { obtenerUsuarioActual } from '../services/authService'
import { cambiarPassword } from '../services/usuarioService'

defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout', 'usuario-actualizado'])

const router = useRouter()

const passwordActual = ref('')
const passwordNuevo = ref('')
const passwordConfirmacion = ref('')

const mostrarActual = ref(false)
const mostrarNuevo = ref(false)
const mostrarConfirmacion = ref(false)

const error = ref('')
const guardando = ref(false)

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

function validarFormulario() {
  if (!passwordActual.value) {
    error.value = 'Ingresá tu contraseña actual.'
    return false
  }

  if (!passwordNuevo.value) {
    error.value = 'Ingresá la nueva contraseña.'
    return false
  }

  if (passwordNuevo.value.length < 8) {
    error.value = 'La nueva contraseña debe tener al menos 8 caracteres.'
    return false
  }

  if (passwordNuevo.value !== passwordConfirmacion.value) {
    error.value = 'La confirmación no coincide con la nueva contraseña.'
    return false
  }

  if (passwordNuevo.value === passwordActual.value) {
    error.value = 'La nueva contraseña no puede ser igual a la actual.'
    return false
  }

  return true
}

async function actualizarPassword() {
  error.value = ''

  if (!validarFormulario()) {
    return
  }

  guardando.value = true

  try {
    await cambiarPassword({
      password_actual: passwordActual.value,
      password_nuevo: passwordNuevo.value,
      password_confirmacion: passwordConfirmacion.value,
    })

    const usuarioActualizado = await obtenerUsuarioActual()
    emit('usuario-actualizado', usuarioActualizado)

    router.replace('/dashboard')
  } catch (e) {
    error.value = obtenerMensajeError(
      e,
      'No se pudo actualizar la contraseña. Intentá nuevamente o comunícate con administración.'
    )
  } finally {
    guardando.value = false
  }
}

function cerrarSesion() {
  emit('logout')
}
</script>

<template>
  <div class="obligatorio-page">
    <div class="bg-blob one"></div>
    <div class="bg-blob two"></div>

    <div class="scene">
      <div class="card">
        <div class="stage"></div>

        <div class="brand">
          <div class="mascot">
            <img :src="sniffLogo" alt="Sniff" />
          </div>

          <div class="wordmark">
            Sniff<span class="dot">.</span>
          </div>
        </div>

        <form @submit.prevent="actualizarPassword">
          <div class="heading">
            <h2>Cambio obligatorio de contraseña</h2>
            <p>La contraseña que te asignó el administrador debe reemplazarse. Para continuar, creá una contraseña nueva.</p>
          </div>

          <div class="field">
            <label for="password-actual">Contraseña actual</label>

            <div class="input-wrap">
              <input
                id="password-actual"
                v-model="passwordActual"
                :type="mostrarActual ? 'text' : 'password'"
                placeholder="••••••••"
                autocomplete="current-password"
                :disabled="guardando"
              />

              <button
                type="button"
                class="toggle-visibility"
                aria-label="Mostrar u ocultar contraseña actual"
                @click="mostrarActual = !mostrarActual"
              >
                {{ mostrarActual ? 'Ocultar' : 'Ver' }}
              </button>
            </div>
          </div>

          <div class="field">
            <label for="password-nuevo">Nueva contraseña</label>

            <div class="input-wrap">
              <input
                id="password-nuevo"
                v-model="passwordNuevo"
                :type="mostrarNuevo ? 'text' : 'password'"
                placeholder="Mínimo 8 caracteres"
                autocomplete="new-password"
                :disabled="guardando"
              />

              <button
                type="button"
                class="toggle-visibility"
                aria-label="Mostrar u ocultar nueva contraseña"
                @click="mostrarNuevo = !mostrarNuevo"
              >
                {{ mostrarNuevo ? 'Ocultar' : 'Ver' }}
              </button>
            </div>
          </div>

          <div class="field">
            <label for="password-confirmacion">Confirmar nueva contraseña</label>

            <div class="input-wrap">
              <input
                id="password-confirmacion"
                v-model="passwordConfirmacion"
                :type="mostrarConfirmacion ? 'text' : 'password'"
                placeholder="Repetí la nueva contraseña"
                autocomplete="new-password"
                :disabled="guardando"
              />

              <button
                type="button"
                class="toggle-visibility"
                aria-label="Mostrar u ocultar confirmación"
                @click="mostrarConfirmacion = !mostrarConfirmacion"
              >
                {{ mostrarConfirmacion ? 'Ocultar' : 'Ver' }}
              </button>
            </div>
          </div>

          <p v-if="error" class="error">
            {{ error }}
          </p>

          <button type="submit" class="btn-primary" :disabled="guardando">
            {{ guardando ? 'Actualizando...' : 'Actualizar contraseña' }}
          </button>

          <button type="button" class="btn-logout" :disabled="guardando" @click="cerrarSesion">
            Cerrar sesión
          </button>
        </form>
      </div>

      <div class="footer-note">
        Por seguridad, no podés continuar sin actualizar tu contraseña.
      </div>
    </div>
  </div>
</template>

<style scoped>
.obligatorio-page {
  --navy: #1D3557;
  --navy-dark: #152840;
  --steel: #457B9D;
  --aqua: #A8DADC;
  --aqua-soft: #EAF5F5;
  --orange: #F4A261;
  --bg: #F6F9FA;
  --white: #FFFFFF;
  --text-secondary: #6B7A8F;
  --text-muted: #9AA8B8;
  --border: #E4EAEF;
  --radius-lg: 24px;
  --radius-md: 14px;
  --shadow-card: 0 24px 60px rgba(29, 53, 87, 0.10),
    0 4px 14px rgba(29, 53, 87, 0.05);

  font-family: 'Montserrat', Arial, sans-serif;
  background: var(--bg);
  min-height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  color: var(--navy);
}

* {
  box-sizing: border-box;
}

.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.3;
  z-index: 0;
}

.bg-blob.one {
  width: 460px;
  height: 460px;
  background: var(--orange);
  opacity: 0.16;
  top: -160px;
  left: -140px;
}

.bg-blob.two {
  width: 420px;
  height: 420px;
  background: var(--steel);
  opacity: 0.14;
  bottom: -160px;
  right: -140px;
}

.scene {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding: 24px;
}

.card {
  background: var(--white);
  width: 440px;
  max-width: 100%;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  border: 1px solid rgba(29, 53, 87, 0.04);
}

.stage {
  height: 90px;
  background:
    radial-gradient(120px 90px at 50% 15%, rgba(244, 162, 97, 0.16), transparent 70%),
    linear-gradient(180deg, var(--aqua-soft) 0%, #F3FAFA 100%);
  border-bottom: 1px solid rgba(168, 218, 220, 0.5);
}

.brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: -32px;
  padding: 0 40px;
  position: relative;
  z-index: 2;
}

.mascot {
  width: 64px;
  height: 64px;
  border-radius: 16px;
}

.mascot img {
  width: 100%;
  height: 100%;
  border-radius: 16px;
  display: block;
}

.wordmark {
  margin-top: 10px;
  font-weight: 800;
  font-size: 22px;
  letter-spacing: -0.4px;
  color: var(--navy);
  line-height: 1;
}

.wordmark .dot {
  color: var(--steel);
}

form {
  padding: 20px 40px 36px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.heading {
  text-align: center;
  margin-bottom: 4px;
}

.heading h2 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 800;
  color: var(--navy);
}

.heading p {
  margin: 0;
  font-size: 12.5px;
  color: var(--text-secondary);
  font-weight: 500;
  line-height: 1.5;
}

.field label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--navy);
  margin-bottom: 7px;
  letter-spacing: 0.2px;
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrap input {
  width: 100%;
  height: 46px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--border);
  background: #FBFCFD;
  padding: 0 72px 0 14px;
  font-family: 'Montserrat', Arial, sans-serif;
  font-size: 14px;
  color: var(--navy);
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.input-wrap input::placeholder {
  color: var(--text-muted);
  font-weight: 400;
}

.input-wrap input:focus {
  border-color: var(--steel);
  background: var(--white);
  box-shadow: 0 0 0 4px rgba(69, 123, 157, 0.12);
}

.input-wrap input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.toggle-visibility {
  position: absolute;
  right: 8px;
  height: 30px;
  padding: 0 10px;
  border: none;
  border-radius: 8px;
  background: var(--aqua-soft);
  color: var(--steel);
  font-family: inherit;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.toggle-visibility:hover {
  background: #dceff0;
  color: var(--navy);
}

.error {
  background: rgba(244, 162, 97, 0.13);
  color: #9C3D13;
  border: 1px solid rgba(244, 162, 97, 0.35);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 12.5px;
  font-weight: 600;
}

.btn-primary {
  margin-top: 4px;
  height: 48px;
  border-radius: var(--radius-md);
  border: none;
  background: var(--navy);
  color: var(--white);
  font-family: 'Montserrat', Arial, sans-serif;
  font-weight: 700;
  font-size: 14.5px;
  letter-spacing: 0.2px;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(29, 53, 87, 0.22);
  transition: background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  background: var(--navy-dark);
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(29, 53, 87, 0.28);
}

.btn-primary:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.btn-logout {
  height: 40px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--border);
  background: var(--white);
  color: var(--text-secondary);
  font-family: 'Montserrat', Arial, sans-serif;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.btn-logout:hover:not(:disabled) {
  background: #F4F7F9;
  color: var(--navy);
}

.btn-logout:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.footer-note {
  margin-top: 18px;
  text-align: center;
  max-width: 380px;
  font-size: 11.5px;
  color: var(--text-muted);
  font-weight: 500;
  letter-spacing: 0.2px;
}
</style>
