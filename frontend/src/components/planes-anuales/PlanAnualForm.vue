<script setup>
import { computed, reactive, watch } from 'vue'
import SelectorBuscable from '../common/SelectorBuscable.vue'

const props = defineProps({
  planAnual: {
    type: Object,
    default: null,
  },
  planes: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['guardar', 'cancelar'])

const estado = reactive({
  plan_estrategico: '',
  anio: '',
  fecha_inicio: '',
  fecha_fin: '',
  error: '',
})

const esEdicion = computed(() => Boolean(props.planAnual?.id))

// Mientras el Plan anual está En uso, la relación y el año quedan
// bloqueados (ver PlanAnualSerializer.validate). El listado ya oculta la
// acción Editar en ese caso; este disabled es un resguardo defensivo.
const esEnUso = computed(() => props.planAnual?.estado === 'en_uso')

const tituloBoton = computed(() => {
  return esEdicion.value ? 'Actualizar plan anual' : 'Crear plan anual'
})

const opcionesPlanes = computed(() => {
  return props.planes.map((plan) => ({ id: plan.id, texto: plan.titulo }))
})

watch(
  () => props.planAnual,
  () => {
    cargarFormulario()
  },
  { immediate: true }
)

function cargarFormulario() {
  estado.plan_estrategico = props.planAnual?.plan_estrategico || ''
  estado.anio = props.planAnual?.anio || ''
  estado.fecha_inicio = props.planAnual?.fecha_inicio || ''
  estado.fecha_fin = props.planAnual?.fecha_fin || ''
  estado.error = ''
}

function validarFormulario() {
  estado.error = ''

  if (!estado.plan_estrategico) {
    estado.error = 'Seleccioná un plan estratégico.'
    return false
  }

  if (!estado.anio) {
    estado.error = 'Ingresá el año del plan anual.'
    return false
  }

  // Fechas de vigencia: obligatorias solo al crear (ver también la
  // validación equivalente y autoritativa en backend:
  // PlanAnualSerializer.validate). En edición, mientras el plan sigue en
  // Borrador, también se revalidan si se tocan.
  if (!esEdicion.value || !esEnUso.value) {
    if (!estado.fecha_inicio) {
      estado.error = 'Ingresá la fecha de inicio del plan anual.'
      return false
    }

    if (!estado.fecha_fin) {
      estado.error = 'Ingresá la fecha de finalización del plan anual.'
      return false
    }
  }

  if (estado.fecha_inicio && estado.fecha_fin && estado.fecha_fin < estado.fecha_inicio) {
    estado.error = 'La fecha de finalización no puede ser anterior a la fecha de inicio.'
    return false
  }

  if (estado.fecha_inicio && Number(estado.fecha_inicio.slice(0, 4)) !== Number(estado.anio)) {
    estado.error = 'La fecha de inicio debe pertenecer al año seleccionado.'
    return false
  }

  if (estado.fecha_fin && Number(estado.fecha_fin.slice(0, 4)) !== Number(estado.anio)) {
    estado.error = 'La fecha de finalización debe pertenecer al año seleccionado.'
    return false
  }

  return true
}

function guardar() {
  if (!validarFormulario()) {
    return
  }

  const payload = {
    plan_estrategico: estado.plan_estrategico,
    anio: Number(estado.anio),
  }

  if (!esEnUso.value) {
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
  <form class="plan-anual-form" @submit.prevent="guardar">
    <div v-if="estado.error" class="alert error">
      {{ estado.error }}
    </div>

    <div v-if="esEnUso" class="help-box warning">
      Este plan anual está En uso: el plan estratégico y el año ya no pueden modificarse.
    </div>

    <div class="form-grid">
      <label class="field field-full">
        <span>Plan estratégico</span>

        <SelectorBuscable
          v-model="estado.plan_estrategico"
          :opciones="opcionesPlanes"
          placeholder="Seleccionar plan estratégico"
          placeholder-busqueda="Escribí el título del plan..."
          mensaje-vacio="No hay planes estratégicos En uso disponibles."
          :disabled="esEnUso"
        />
      </label>

      <label class="field field-full">
        <span>Año</span>

        <input
          v-model="estado.anio"
          type="number"
          placeholder="Ejemplo: 2027"
          :disabled="esEnUso"
        />

        <small class="field-hint">Debe estar dentro de la vigencia del plan estratégico seleccionado.</small>
      </label>

      <label class="field">
        <span>Fecha de inicio</span>

        <input
          v-model="estado.fecha_inicio"
          type="date"
          :disabled="esEnUso"
        />
      </label>

      <label class="field">
        <span>Fecha de finalización</span>

        <input
          v-model="estado.fecha_fin"
          type="date"
          :disabled="esEnUso"
        />

        <small class="field-hint">Ambas fechas deben pertenecer al año seleccionado.</small>
      </label>
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
.plan-anual-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plan-anual-form,
.plan-anual-form * {
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

.field input {
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

.field input:focus {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
}

.field input:disabled {
  background: #f4f7f9;
  color: #9aa8b8;
  cursor: not-allowed;
}

.field-hint {
  color: #9aa8b8;
  font-size: 11px;
  font-weight: 600;
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
