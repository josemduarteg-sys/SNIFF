<script setup>
import { reactive, ref } from 'vue'

const props = defineProps({
  solicitud: {
    type: Object,
    default: null,
  },
  guardando: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['asignar', 'cancelar'])

const estado = reactive({
  password: '',
  confirmarPassword: '',
  errorPassword: '',
  errorConfirmar: '',
})

const mostrarPassword = ref(false)
const mostrarConfirmar = ref(false)

function validarFormulario() {
  estado.errorPassword = ''
  estado.errorConfirmar = ''

  let valido = true

  if (!estado.password.trim()) {
    estado.errorPassword = 'Ingresá la contraseña temporal.'
    valido = false
  } else if (estado.password.length < 8) {
    estado.errorPassword = 'La contraseña debe tener al menos 8 caracteres.'
    valido = false
  }

  if (!estado.confirmarPassword.trim()) {
    estado.errorConfirmar = 'Confirmá la contraseña temporal.'
    valido = false
  } else if (valido && estado.confirmarPassword !== estado.password) {
    estado.errorConfirmar = 'Las contraseñas no coinciden.'
    valido = false
  }

  return valido
}

function confirmar() {
  if (props.guardando) return
  if (!validarFormulario()) return

  emit('asignar', { password_temporal: estado.password })
}

function cancelar() {
  emit('cancelar')
}
</script>

<template>
  <form class="password-temporal-form" @submit.prevent="confirmar">
    <p class="texto-apoyo">
      Ingrese la contraseña temporal que se asignará al usuario
      <strong v-if="solicitud?.usuario_username">"{{ solicitud.usuario_username }}"</strong>
      para recuperar el acceso al sistema.
    </p>

    <label class="field">
      <span>Contraseña temporal</span>

      <div class="password-wrapper">
        <input
          v-model="estado.password"
          :type="mostrarPassword ? 'text' : 'password'"
          placeholder="Mínimo 8 caracteres"
          :disabled="guardando"
          :class="{ 'campo-error': estado.errorPassword }"
        />

        <button
          class="password-toggle"
          type="button"
          :disabled="guardando"
          @click="mostrarPassword = !mostrarPassword"
        >
          {{ mostrarPassword ? 'Ocultar' : 'Ver' }}
        </button>
      </div>

      <small v-if="estado.errorPassword" class="field-error">{{ estado.errorPassword }}</small>
      <small v-else class="password-hint">
        Mínimo 8 caracteres. No puede ser una contraseña común, solo números ni parecerse a los datos del usuario.
      </small>
    </label>

    <label class="field">
      <span>Confirmar contraseña temporal</span>

      <div class="password-wrapper">
        <input
          v-model="estado.confirmarPassword"
          :type="mostrarConfirmar ? 'text' : 'password'"
          placeholder="Repetí la contraseña temporal"
          :disabled="guardando"
          :class="{ 'campo-error': estado.errorConfirmar }"
        />

        <button
          class="password-toggle"
          type="button"
          :disabled="guardando"
          @click="mostrarConfirmar = !mostrarConfirmar"
        >
          {{ mostrarConfirmar ? 'Ocultar' : 'Ver' }}
        </button>
      </div>

      <small v-if="estado.errorConfirmar" class="field-error">{{ estado.errorConfirmar }}</small>
    </label>

    <div class="help-box">
      <strong>Nota:</strong>
      El usuario deberá cambiar esta contraseña al iniciar sesión.
    </div>

    <div class="form-actions">
      <button class="btn-secondary" type="button" :disabled="guardando" @click="cancelar">
        Cancelar
      </button>

      <button class="btn-primary" type="submit" :disabled="guardando">
        <span v-if="guardando" class="spinner"></span>
        {{ guardando ? 'Asignando...' : 'Asignar contraseña' }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.password-temporal-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.password-temporal-form,
.password-temporal-form * {
  box-sizing: border-box;
}

.texto-apoyo {
  margin: 0;
  font-size: 13px;
  color: #5e6e82;
  font-weight: 550;
  line-height: 1.5;
}

.texto-apoyo strong {
  color: #1d3557;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.field span {
  font-size: 12px;
  font-weight: 800;
  color: #1d3557;
}

.password-wrapper {
  position: relative;
  width: 100%;
}

.password-wrapper input {
  width: 100%;
  min-width: 0;
  border: 1.5px solid #e4eaef;
  border-radius: 11px;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 13px;
  font-weight: 650;
  outline: none;
  padding: 11px 72px 11px 12px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.password-wrapper input:focus {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
}

.password-wrapper input:disabled {
  background: #f4f7f9;
  color: #9aa8b8;
  cursor: not-allowed;
}

.password-wrapper input.campo-error {
  border-color: #e76f51;
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

.password-toggle:hover:not(:disabled) {
  background: #dceff0;
  color: #1d3557;
}

.password-toggle:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.password-hint {
  color: #9aa8b8;
  font-size: 11px;
  font-weight: 600;
}

.field-error {
  color: #e76f51;
  font-size: 11.5px;
  font-weight: 700;
}

.help-box {
  border-radius: 12px;
  background: #eaf5f5;
  color: #457b9d;
  padding: 13px 14px;
  font-size: 12.5px;
  line-height: 1.45;
  font-weight: 650;
}

.help-box strong {
  color: #1d3557;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-primary,
.btn-secondary {
  height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-primary {
  border: none;
  background: #1d3557;
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(29, 53, 87, 0.14);
}

.btn-primary:hover:not(:disabled) {
  background: #152840;
}

.btn-primary:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.btn-secondary {
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
}

.btn-secondary:hover:not(:disabled) {
  background: #f4f7f9;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #ffffff;
  animation: girar 0.7s linear infinite;
}

@keyframes girar {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 480px) {
  .form-actions {
    flex-direction: column-reverse;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
