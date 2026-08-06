<script setup>
import { reactive } from 'vue'
import { cambiarPassword } from '../../services/usuarioService'

const form = reactive({
  password_actual: '',
  password_nuevo: '',
  password_confirmacion: '',
})

const estado = reactive({
  guardando: false,
  mensaje: '',
  error: '',
})

async function guardarPassword() {
  estado.guardando = true
  estado.mensaje = ''
  estado.error = ''

  if (!form.password_actual || !form.password_nuevo || !form.password_confirmacion) {
    estado.error = 'Completá todos los campos de contraseña.'
    estado.guardando = false
    return
  }

  if (form.password_nuevo !== form.password_confirmacion) {
    estado.error = 'La confirmación no coincide con la nueva contraseña.'
    estado.guardando = false
    return
  }

  try {
    await cambiarPassword({
      password_actual: form.password_actual,
      password_nuevo: form.password_nuevo,
      password_confirmacion: form.password_confirmacion,
    })

    form.password_actual = ''
    form.password_nuevo = ''
    form.password_confirmacion = ''

    estado.mensaje = 'Contraseña actualizada correctamente.'
  } catch (error) {
    const data = error.response?.data

    if (data?.password_actual) {
      estado.error = data.password_actual
    } else if (data?.password_confirmacion) {
      estado.error = data.password_confirmacion
    } else if (Array.isArray(data?.password_nuevo)) {
      estado.error = data.password_nuevo.join(' ')
    } else {
      estado.error = 'No se pudo actualizar la contraseña.'
    }
  } finally {
    estado.guardando = false
  }
}
</script>

<template>
  <section class="config-card">
    <div class="card-header">
      <div>
        <h2>Cambiar contraseña</h2>
        <p>Actualizá tu contraseña de acceso al sistema.</p>
      </div>
    </div>

    <form class="form-grid" @submit.prevent="guardarPassword">
      <div class="form-group full">
        <label>Contraseña actual</label>
        <input
          v-model="form.password_actual"
          type="password"
          placeholder="Ingresá tu contraseña actual"
        />
      </div>

      <div class="form-group">
        <label>Nueva contraseña</label>
        <input
          v-model="form.password_nuevo"
          type="password"
          placeholder="Nueva contraseña"
        />
      </div>

      <div class="form-group">
        <label>Confirmar contraseña</label>
        <input
          v-model="form.password_confirmacion"
          type="password"
          placeholder="Confirmar contraseña"
        />
      </div>

      <div v-if="estado.mensaje" class="alert success full">
        {{ estado.mensaje }}
      </div>

      <div v-if="estado.error" class="alert error full">
        {{ estado.error }}
      </div>

      <div class="form-actions full">
        <button class="btn-primary" type="submit" :disabled="estado.guardando">
          {{ estado.guardando ? 'Guardando...' : 'Actualizar contraseña' }}
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

