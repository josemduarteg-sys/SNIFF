<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  area: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['guardar', 'cancelar'])

const estado = reactive({
  nombre: '',
  descripcion: '',
  error: '',
})

const esEdicion = computed(() => Boolean(props.area?.id))

const tituloBoton = computed(() => {
  return esEdicion.value ? 'Actualizar área' : 'Crear área'
})

watch(
  () => props.area,
  () => {
    cargarFormulario()
  },
  { immediate: true }
)

function cargarFormulario() {
  estado.nombre = props.area?.nombre || ''
  estado.descripcion = props.area?.descripcion || ''
  estado.error = ''
}

function validarFormulario() {
  estado.error = ''

  if (!estado.nombre.trim()) {
    estado.error = 'Ingresá el nombre del área.'
    return false
  }

  return true
}

function guardar() {
  if (!validarFormulario()) {
    return
  }

  emit('guardar', {
    nombre: estado.nombre.trim(),
    descripcion: estado.descripcion.trim(),
  })
}

function cancelar() {
  emit('cancelar')
}
</script>

<template>
  <form class="area-form" @submit.prevent="guardar">
    <div v-if="estado.error" class="alert error">
      {{ estado.error }}
    </div>

    <div class="form-grid">
      <label class="field field-full">
        <span>Nombre del área</span>

        <input
          v-model="estado.nombre"
          type="text"
          placeholder="Ejemplo: Créditos y Cobros"
        />
      </label>

      <label class="field field-full">
        <span>Descripción</span>

        <textarea
          v-model="estado.descripcion"
          rows="4"
          placeholder="Describe brevemente la función del área."
        ></textarea>
      </label>
    </div>

    <div class="help-box">
      Registra las áreas disponibles para la organización interna del sistema.
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
.area-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.area-form,
.area-form * {
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
  grid-template-columns: 1fr;
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
.field textarea {
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

.field textarea {
  resize: vertical;
  min-height: 95px;
}

.field input:focus,
.field textarea:focus {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
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
  .form-actions {
    flex-direction: column-reverse;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
