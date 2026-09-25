<script setup>
import { computed, reactive, watch } from 'vue'
import SelectorBuscable from '../common/SelectorBuscable.vue'

const props = defineProps({
  objetivo: {
    type: Object,
    default: null,
  },
  planesAnuales: {
    type: Array,
    default: () => [],
  },
  objetivosGenerales: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['guardar', 'cancelar'])

const estado = reactive({
  plan_anual: '',
  objetivo_general: '',
  texto_objetivo: '',
  error: '',
})

const esEdicion = computed(() => Boolean(props.objetivo?.id))

const tituloBoton = computed(() => {
  return esEdicion.value ? 'Actualizar objetivo específico' : 'Crear objetivo específico'
})

const opcionesPlanesAnuales = computed(() => {
  return props.planesAnuales.map((plan) => ({
    id: plan.id,
    texto: `${plan.nombre || `Plan ${plan.anio}`} — ${plan.plan_estrategico_titulo || 'Sin plan estratégico'}`,
  }))
})

const planAnualSeleccionado = computed(() => {
  return (
    props.planesAnuales.find((plan) => Number(plan.id) === Number(estado.plan_anual)) || null
  )
})

// Solo objetivos generales del MISMO Plan estratégico que el Plan anual
// elegido (ver validación equivalente, y autoritativa, en backend:
// ObjetivoEspecificoSerializer.validate).
const opcionesObjetivosGenerales = computed(() => {
  if (!planAnualSeleccionado.value) {
    return []
  }

  return props.objetivosGenerales
    .filter(
      (objetivo) =>
        Number(objetivo.plan_estrategico) === Number(planAnualSeleccionado.value.plan_estrategico)
    )
    .map((objetivo) => ({ id: objetivo.id, texto: objetivo.texto_objetivo }))
})

watch(
  () => props.objetivo,
  () => {
    cargarFormulario()
  },
  { immediate: true }
)

watch(
  () => estado.plan_anual,
  () => {
    const siguePerteneciendo = opcionesObjetivosGenerales.value.some(
      (opcion) => Number(opcion.id) === Number(estado.objetivo_general)
    )

    if (!siguePerteneciendo) {
      estado.objetivo_general = ''
    }
  }
)

function cargarFormulario() {
  estado.plan_anual = props.objetivo?.plan_anual || ''
  estado.objetivo_general = props.objetivo?.objetivo_general || ''
  estado.texto_objetivo = props.objetivo?.texto_objetivo || ''
  estado.error = ''
}

function validarFormulario() {
  estado.error = ''

  if (!estado.plan_anual) {
    estado.error = 'Seleccioná un plan anual.'
    return false
  }

  if (!estado.objetivo_general) {
    estado.error = 'Seleccioná un objetivo general.'
    return false
  }

  if (!estado.texto_objetivo.trim()) {
    estado.error = 'Ingresá el texto del objetivo específico.'
    return false
  }

  return true
}

function guardar() {
  if (!validarFormulario()) {
    return
  }

  emit('guardar', {
    plan_anual: estado.plan_anual,
    objetivo_general: estado.objetivo_general,
    texto_objetivo: estado.texto_objetivo.trim(),
  })
}

function cancelar() {
  emit('cancelar')
}
</script>

<template>
  <form class="objetivo-form" @submit.prevent="guardar">
    <div v-if="estado.error" class="alert error">
      {{ estado.error }}
    </div>

    <div class="form-grid">
      <label class="field field-full">
        <span>Plan anual</span>

        <SelectorBuscable
          v-model="estado.plan_anual"
          :opciones="opcionesPlanesAnuales"
          placeholder="Seleccionar plan anual"
          placeholder-busqueda="Escribí el plan o el año..."
          mensaje-vacio="No hay planes anuales En uso disponibles."
        />
      </label>

      <label class="field field-full">
        <span>Objetivo general</span>

        <SelectorBuscable
          v-model="estado.objetivo_general"
          :opciones="opcionesObjetivosGenerales"
          placeholder="Seleccionar objetivo general"
          placeholder-busqueda="Escribí el texto del objetivo..."
          mensaje-vacio="Seleccioná primero un plan anual."
          :disabled="!estado.plan_anual"
        />
      </label>

      <label class="field field-full">
        <span>Texto del objetivo específico</span>

        <textarea
          v-model="estado.texto_objetivo"
          rows="4"
          placeholder="Ejemplo: Incrementar la recuperación mensual de cartera durante el año 2027."
        ></textarea>
      </label>
    </div>

    <div class="help-box">
      Solo se muestran planes anuales En uso. El objetivo general disponible depende del plan estratégico al que pertenece el plan anual seleccionado.
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
.objetivo-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.objetivo-form,
.objetivo-form * {
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
  resize: vertical;
  min-height: 95px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

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
