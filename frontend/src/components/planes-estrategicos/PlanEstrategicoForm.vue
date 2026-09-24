<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  plan: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['guardar', 'cancelar'])

const estado = reactive({
  titulo: '',
  descripcion: '',
  fecha_inicio: '',
  fecha_fin: '',
  error: '',
})

const esEdicion = computed(() => Boolean(props.plan?.id))

const esEnUso = computed(() => props.plan?.estado === 'en_uso')

const tituloBoton = computed(() => {
  return esEdicion.value ? 'Actualizar plan estratégico' : 'Crear plan estratégico'
})

watch(
  () => props.plan,
  () => {
    cargarFormulario()
  },
  { immediate: true }
)

function cargarFormulario() {
  estado.titulo = props.plan?.titulo || ''
  estado.descripcion = props.plan?.descripcion || ''
  estado.fecha_inicio = props.plan?.fecha_inicio || ''
  estado.fecha_fin = props.plan?.fecha_fin || ''
  estado.error = ''
}

function validarFormulario() {
  estado.error = ''

  if (!estado.titulo.trim()) {
    estado.error = 'Ingresá el título del plan estratégico.'
    return false
  }

  if (estado.fecha_inicio && estado.fecha_fin && estado.fecha_fin < estado.fecha_inicio) {
    estado.error = 'La fecha fin no puede ser menor que la fecha inicio.'
    return false
  }

  return true
}

function guardar() {
  if (!validarFormulario()) {
    return
  }

  const payload = {
    descripcion: estado.descripcion.trim(),
  }

  // Título y periodo solo se envían cuando todavía se pueden modificar
  // (Borrador). Mientras está En uso, el backend los rechaza de todas
  // formas, pero evitamos mandarlos ya bloqueados desde acá.
  if (!esEnUso.value) {
    payload.titulo = estado.titulo.trim()
    payload.fecha_inicio = estado.fecha_inicio || null
    payload.fecha_fin = estado.fecha_fin || null
  }

  emit('guardar', payload)
}

function cancelar() {
  emit('cancelar')
}
</script>

<template>
  <form class="plan-form" @submit.prevent="guardar">
    <div v-if="estado.error" class="alert error">
      {{ estado.error }}
    </div>

    <div v-if="esEnUso" class="help-box warning">
      Este plan está En uso: el título y el periodo ya no pueden modificarse. Solo la descripción es editable.
    </div>

    <div class="form-grid">
      <label class="field field-full">
        <span>Título del plan estratégico</span>

        <input
          v-model="estado.titulo"
          type="text"
          placeholder="Ejemplo: Plan estratégico 2027-2030"
          :disabled="esEnUso"
        />
      </label>

      <label class="field field-full">
        <span>Descripción</span>

        <textarea
          v-model="estado.descripcion"
          rows="4"
          placeholder="Describe el enfoque general del plan estratégico."
        ></textarea>
      </label>

      <label class="field">
        <span>Fecha inicio</span>

        <input
          v-model="estado.fecha_inicio"
          type="date"
          :disabled="esEnUso"
        />
      </label>

      <label class="field">
        <span>Fecha fin</span>

        <input
          v-model="estado.fecha_fin"
          type="date"
          :disabled="esEnUso"
        />
      </label>

    </div>

    <div class="help-box">
      Todo plan estratégico nuevo nace en Borrador. Desde el listado podés pasarlo a En uso cuando esté listo para ejecutarse.
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
.plan-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plan-form,
.plan-form * {
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
.field select,
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
.field select:focus,
.field textarea:focus {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
}

.field input:disabled,
.field select:disabled,
.field textarea:disabled {
  background: #f4f7f9;
  color: #9aa8b8;
  cursor: not-allowed;
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

.help-box.warning {
  background: rgba(244, 162, 97, 0.14);
  color: #b9701e;
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
