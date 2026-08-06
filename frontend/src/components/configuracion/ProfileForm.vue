<script setup>
import { reactive, watch } from 'vue'
import { actualizarPerfil } from '../../services/usuarioService'

const props = defineProps({
  perfil: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['actualizado'])

const form = reactive({
  first_name: '',
  last_name: '',
  correo: '',
})

const estado = reactive({
  guardando: false,
  mensaje: '',
  error: '',
})

watch(
  () => props.perfil,
  (perfil) => {
    form.first_name = perfil?.first_name || ''
    form.last_name = perfil?.last_name || ''
    form.correo = perfil?.correo || perfil?.email || ''
  },
  { immediate: true }
)

async function guardarPerfil() {
  estado.guardando = true
  estado.mensaje = ''
  estado.error = ''

  try {
    const perfilActualizado = await actualizarPerfil({
      first_name: form.first_name,
      last_name: form.last_name,
      correo: form.correo,
      email: form.correo,
    })

    estado.mensaje = 'Perfil actualizado correctamente.'
    emit('actualizado', perfilActualizado)
  } catch (error) {
    estado.error = 'No se pudo actualizar el perfil.'
  } finally {
    estado.guardando = false
  }
}
</script>

<template>
  <section class="config-card">
    <div class="card-header">
      <div>
        <h2>Mi perfil</h2>
        <p>Actualizá la información básica de tu cuenta.</p>
      </div>
    </div>

    <form class="form-grid" @submit.prevent="guardarPerfil">
      <div class="form-group">
        <label>Usuario</label>
        <input :value="perfil.username" type="text" disabled />
      </div>

      <div class="form-group">
        <label>Rol</label>
        <input :value="perfil.rol_nombre || 'Sin rol'" type="text" disabled />
      </div>

      <div class="form-group">
        <label>Nombres</label>
        <input v-model="form.first_name" type="text" placeholder="Nombres" />
      </div>

      <div class="form-group">
        <label>Apellidos</label>
        <input v-model="form.last_name" type="text" placeholder="Apellidos" />
      </div>

      <div class="form-group full">
        <label>Correo electrónico</label>
        <input v-model="form.correo" type="email" placeholder="correo@ejemplo.com" />
      </div>

      <div v-if="estado.mensaje" class="alert success full">
        {{ estado.mensaje }}
      </div>

      <div v-if="estado.error" class="alert error full">
        {{ estado.error }}
      </div>

      <div class="form-actions full">
        <button class="btn-primary" type="submit" :disabled="estado.guardando">
          {{ estado.guardando ? 'Guardando...' : 'Guardar cambios' }}
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.config-card {
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 14px;
  box-shadow: 0 2px 10px rgba(29, 53, 87, 0.05);
  padding: 22px;
}

.card-header {
  margin-bottom: 20px;
}

.card-header h2 {
  margin: 0;
  color: #1d3557;
  font-size: 17px;
  font-weight: 800;
}

.card-header p {
  margin: 5px 0 0;
  color: #9aa8b8;
  font-size: 13px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.form-group.full,
.full {
  grid-column: 1 / -1;
}

label {
  color: #1d3557;
  font-size: 12px;
  font-weight: 800;
}

input {
  height: 40px;
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  padding: 0 12px;
  font-family: inherit;
  color: #1d3557;
  outline: none;
}

input:focus {
  border-color: #a8dadc;
}

input:disabled {
  background: #f6f9fa;
  color: #9aa8b8;
}

.alert {
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
}

.alert.success {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.alert.error {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
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

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

@media (max-width: 700px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

