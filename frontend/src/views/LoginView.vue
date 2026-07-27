<script setup>
import { ref } from 'vue'
import sniffLogo from '../assets/images/sniff-logo.png'
import { login, logout, obtenerUsuarioActual } from '../services/authService'

const emit = defineEmits(['login-success'])

const username = ref('')
const password = ref('')
const mostrarPassword = ref(false)
const error = ref('')
const cargando = ref(false)

async function iniciarSesion() {
  error.value = ''

  if (!username.value || !password.value) {
    error.value = 'Ingrese usuario y contraseña.'
    return
  }

  cargando.value = true

  try {
    await login(username.value, password.value)
    const usuario = await obtenerUsuarioActual()

    emit('login-success', usuario)
  } catch (e) {
    logout()
    error.value = 'Usuario o contraseña incorrectos.'
  } finally {
    cargando.value = false
  }
}

function togglePassword() {
  mostrarPassword.value = !mostrarPassword.value
}
</script>

<template>
  <div class="login-page">
    <div class="bg-blob one"></div>
    <div class="bg-blob two"></div>
    <div class="bg-grid"></div>

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

          <div class="tagline">
            Monitoreo Estratégico &amp; KPIs
          </div>
        </div>

        <form @submit.prevent="iniciarSesion">
          <div class="field">
            <label for="usuario">Usuario</label>

            <div class="input-wrap">
              <svg
                class="icon-left"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>

              <input
                id="usuario"
                v-model="username"
                type="text"
                placeholder="nombre.apellido"
                autocomplete="username"
              />
            </div>
          </div>

          <div class="field">
            <label for="password">Contraseña</label>

            <div class="input-wrap">
              <svg
                class="icon-left"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <rect x="3" y="11" width="18" height="10" rx="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>

              <input
                id="password"
                v-model="password"
                :type="mostrarPassword ? 'text' : 'password'"
                placeholder="••••••••"
                autocomplete="current-password"
              />

              <button
                type="button"
                class="toggle-visibility"
                aria-label="Mostrar u ocultar contraseña"
                @click="togglePassword"
              >
                <svg
                  v-if="!mostrarPassword"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>

                <svg
                  v-else
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M17.94 17.94A10.94 10.94 0 0 1 12 19c-7 0-11-7-11-7a21.6 21.6 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 7 11 7a21.6 21.6 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              </button>
            </div>
          </div>

          <div class="row-end">
            <a href="#" class="link">¿Olvidaste tu contraseña?</a>
          </div>

          <p v-if="error" class="error">
            {{ error }}
          </p>

          <button type="submit" class="btn-primary" :disabled="cargando">
            {{ cargando ? 'Iniciando sesión...' : 'Iniciar sesión' }}
          </button>
        </form>
      </div>

      <div class="footer-note">
        Sistema de Monitoreo Estratégico y KPIs
      </div>

      <div class="badge-secure">
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="3" y="11" width="18" height="10" rx="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>

        Acceso protegido — Cooperativa Financiera
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
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
  opacity: 0.35;
  z-index: 0;
}

.bg-blob.one {
  width: 520px;
  height: 520px;
  background: var(--aqua);
  top: -180px;
  left: -160px;
}

.bg-blob.two {
  width: 420px;
  height: 420px;
  background: var(--steel);
  opacity: 0.14;
  bottom: -160px;
  right: -140px;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(29, 53, 87, 0.05) 1px, transparent 1px);
  background-size: 26px 26px;
  mask-image: radial-gradient(
    ellipse 900px 700px at 50% 40%,
    black 10%,
    transparent 70%
  );
  z-index: 0;
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
  width: 420px;
  max-width: 100%;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  border: 1px solid rgba(29, 53, 87, 0.04);
}

.stage {
  height: 132px;
  background:
    radial-gradient(120px 90px at 50% 15%, rgba(69, 123, 157, 0.14), transparent 70%),
    linear-gradient(180deg, var(--aqua-soft) 0%, #F3FAFA 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border-bottom: 1px solid rgba(168, 218, 220, 0.5);
}

.brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: -42px;
  padding: 0 40px;
  position: relative;
  z-index: 2;
}

.mascot {
  width: 84px;
  height: 84px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mascot img {
  width: 100%;
  height: 100%;
  border-radius: 20px;
  display: block;
}

.wordmark {
  margin-top: 14px;
  font-weight: 800;
  font-size: 30px;
  letter-spacing: -0.5px;
  color: var(--navy);
  line-height: 1;
}

.wordmark .dot {
  color: var(--steel);
}

.tagline {
  margin-top: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--steel);
}

form {
  padding: 32px 40px 36px;
  display: flex;
  flex-direction: column;
  gap: 18px;
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

.input-wrap svg.icon-left {
  position: absolute;
  left: 14px;
  color: var(--text-muted);
}

.input-wrap input {
  width: 100%;
  height: 46px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--border);
  background: #FBFCFD;
  padding: 0 44px 0 42px;
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

.toggle-visibility {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  padding: 6px;
  border-radius: 8px;
  transition: color 0.15s ease, background 0.15s ease;
}

.toggle-visibility:hover {
  color: var(--steel);
  background: rgba(69, 123, 157, 0.08);
}

.row-end {
  display: flex;
  justify-content: flex-end;
  margin-top: -6px;
}

.link {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--steel);
  text-decoration: none;
  transition: color 0.15s ease;
}

.link:hover {
  color: var(--navy);
  text-decoration: underline;
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
  margin-top: 6px;
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

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.footer-note {
  margin-top: 22px;
  text-align: center;
  font-size: 11.5px;
  color: var(--text-muted);
  font-weight: 500;
  letter-spacing: 0.2px;
}

.badge-secure {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}
</style>
