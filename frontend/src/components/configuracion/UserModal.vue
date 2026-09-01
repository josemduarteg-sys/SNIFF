<script setup>
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  usuario: {
    type: Object,
    default: null,
  },
  roles: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['guardar', 'cancelar'])

const estado = reactive({
  username: '',
  first_name: '',
  last_name: '',
  correo: '',
  rol: '',
  password: '',
  error: '',
})

const esEdicion = computed(() => Boolean(props.usuario?.id))

const tituloBoton = computed(() => {
  return esEdicion.value ? 'Actualizar usuario' : 'Crear usuario'
})

const mostrarPassword = ref(false)

watch(
  () => props.usuario,
  () => {
    cargarFormulario()
  },
  { immediate: true }
)

function cargarFormulario() {
  estado.username = props.usuario?.username || ''
  estado.first_name = props.usuario?.first_name || ''
  estado.last_name = props.usuario?.last_name || ''
  estado.correo = props.usuario?.correo || props.usuario?.email || ''
  estado.rol = props.usuario?.rol || ''
  estado.password = ''
  estado.error = ''
}

function validarFormulario() {
  estado.error = ''

  if (!estado.username.trim()) {
    estado.error = 'Ingresá el nombre de usuario.'
    return false
  }

  if (!estado.first_name.trim()) {
    estado.error = 'Ingresá el nombre.'
    return false
  }

  if (!estado.last_name.trim()) {
    estado.error = 'Ingresá el apellido.'
    return false
  }

  if (!estado.correo.trim()) {
    estado.error = 'Ingresá el correo electrónico.'
    return false
  }

  if (!estado.rol) {
    estado.error = 'Seleccioná el rol del usuario.'
    return false
  }

  if (!esEdicion.value && !estado.password.trim()) {
    estado.error = 'Ingresá una contraseña para el nuevo usuario.'
    return false
  }

  if (!esEdicion.value && estado.password.length < 8) {
    estado.error = 'La contraseña debe tener al menos 8 caracteres.'
    return false
  }

  return true
}

function guardar() {
  if (!validarFormulario()) {
    return
  }

  const payload = {
    username: estado.username.trim(),
    first_name: estado.first_name.trim(),
    last_name: estado.last_name.trim(),
    correo: estado.correo.trim(),
    email: estado.correo.trim(),
    rol: estado.rol,
  }

  if (!esEdicion.value) {
    payload.password = estado.password
  }

  emit('guardar', payload)
}

function cancelar() {
  emit('cancelar')
}
</script>

<template>
  <form class="user-form" @submit.prevent="guardar">
    <div v-if="estado.error" class="alert error">
      {{ estado.error }}
    </div>

    <div class="form-grid">
      <label class="field">
        <span>Usuario</span>

        <input
          v-model="estado.username"
          type="text"
          placeholder="Ejemplo: jduarte"
          :disabled="esEdicion"
        />
      </label>

      <label class="field">
        <span>Rol</span>

        <select v-model="estado.rol">
          <option value="">Seleccionar rol</option>

          <option
            v-for="rol in roles"
            :key="rol.id"
            :value="rol.id"
          >
            {{ rol.nombre }}
          </option>
        </select>
      </label>

      <label class="field">
        <span>Nombre</span>

        <input
          v-model="estado.first_name"
          type="text"
          placeholder="Nombre"
        />
      </label>

      <label class="field">
        <span>Apellido</span>

        <input
          v-model="estado.last_name"
          type="text"
          placeholder="Apellido"
        />
      </label>

      <label class="field field-full">
        <span>Correo electrónico</span>

        <input
          v-model="estado.correo"
          type="email"
          placeholder="correo@ejemplo.com"
        />
      </label>

      <label v-if="!esEdicion" class="field field-full">
        <span>Contraseña inicial</span>

        <div class="password-wrapper">
          <input
            v-model="estado.password"
            :type="mostrarPassword ? 'text' : 'password'"
            placeholder="Mínimo 8 caracteres"
          />

          <button
            class="password-toggle"
            type="button"
            @click="mostrarPassword = !mostrarPassword"
          >
            {{ mostrarPassword ? 'Ocultar' : 'Ver' }}
          </button>
        </div>
      </label>
    </div>

    <div class="help-box">
      <strong>Nota:</strong>
      la contraseña solo se define al crear el usuario. Para edición se modifican datos generales y rol.
      Para activar o inactivar el usuario, usá las acciones de la tabla.
    </div>

    <div class="form-actions">
      <button class="btn-secondary" type="button" @click="cancelar">
        Cancelar
      </button>

      <button class="btn-primary" type="submit">
        {{ tituloBoton }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.user-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.user-form,
.user-form * {
  box-sizing: border-box;
}

.alert {
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 750;
}

.alert.error {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
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

.field input,
.field select {
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
  padding: 11px 12px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.field input:focus,
.field select:focus {
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
}

.btn-primary {
  border: none;
  background: #1d3557;
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(29, 53, 87, 0.14);
}

.btn-primary:hover {
  background: #152840;
}

.btn-secondary {
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
}

.btn-secondary:hover {
  background: #f4f7f9;
}

@media (max-width: 680px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
