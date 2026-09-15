<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  estrategia: {
    type: Object,
    default: null,
  },
  areas: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['guardar', 'cancelar'])

const estado = reactive({
  area: '',
  nombre: '',
  descripcion: '',
  fecha_inicio: '',
  fecha_fin: '',
  error: '',
})

const esEdicion = computed(() => Boolean(props.estrategia?.id))

const tituloBoton = computed(() => {
  return esEdicion.value ? 'Actualizar estrategia' : 'Crear estrategia'
})

const areasDisponibles = computed(() => {
  const areaActualId = props.estrategia?.area
  const yaIncluida = props.areas.some((area) => Number(area.id) === Number(areaActualId))

  if (esEdicion.value && areaActualId && !yaIncluida) {
    return [
      ...props.areas,
      {
        id: areaActualId,
        nombre: `${props.estrategia?.area_nombre || 'Área'} (inactiva)`,
      },
    ]
  }

  return props.areas
})

watch(
  () => props.estrategia,
  () => {
    cargarFormulario()
  },
  { immediate: true }
)

function cargarFormulario() {
  estado.area = props.estrategia?.area || ''
  estado.nombre = props.estrategia?.nombre || ''
  estado.descripcion = props.estrategia?.descripcion || ''
  estado.fecha_inicio = props.estrategia?.fecha_inicio || ''
  estado.fecha_fin = props.estrategia?.fecha_fin || ''
  estado.error = ''
}

function validarFormulario() {
  estado.error = ''

  if (!estado.area) {
    estado.error = 'Seleccioná el área relacionada con la estrategia.'
    return false
  }

  if (!estado.nombre.trim()) {
    estado.error = 'Ingresá el nombre de la estrategia.'
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

  emit('guardar', {
    area: estado.area,
    nombre: estado.nombre.trim(),
    descripcion: estado.descripcion.trim(),
    fecha_inicio: estado.fecha_inicio || null,
    fecha_fin: estado.fecha_fin || null,
  })
}

function cancelar() {
  emit('cancelar')
}
</script>

<template>
  <form class="estrategia-form" @submit.prevent="guardar">
    <div v-if="estado.error" class="alert error">
      {{ estado.error }}
    </div>

    <div class="form-grid">
      <label class="field field-full">
        <span>Área</span>

        <select v-model="estado.area">
          <option value="">Seleccionar área</option>

          <option
            v-for="area in areasDisponibles"
            :key="area.id"
            :value="area.id"
          >
            {{ area.nombre }}
          </option>
        </select>
      </label>

      <label class="field field-full">
        <span>Nombre de la estrategia</span>

        <input
          v-model="estado.nombre"
          type="text"
          placeholder="Ejemplo: Fortalecimiento de recuperación de cartera"
        />
      </label>

      <label class="field field-full">
        <span>Descripción</span>

        <textarea
          v-model="estado.descripcion"
          rows="4"
          placeholder="Describe el enfoque general de la estrategia."
        ></textarea>
      </label>

      <label class="field">
        <span>Fecha inicio</span>

        <input
          v-model="estado.fecha_inicio"
          type="date"
        />
      </label>

      <label class="field">
        <span>Fecha fin</span>

        <input
          v-model="estado.fecha_fin"
          type="date"
        />
      </label>

    </div>

    <div class="help-box">
      Completa los datos generales de la estrategia. El sistema gestionará su estado
      durante el proceso de revisión.
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
.estrategia-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.estrategia-form,
.estrategia-form * {
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
