<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { obtenerPlanesEstrategicosParaObjetivo } from '../../services/objetivoGeneralService'

const props = defineProps({
  objetivo: {
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
  texto_objetivo: '',
  error: '',
})

const planFaltante = ref(null)

const esEdicion = computed(() => Boolean(props.objetivo?.id))

const tituloBoton = computed(() => {
  return esEdicion.value ? 'Actualizar objetivo general' : 'Crear objetivo general'
})

const planesDisponibles = computed(() => {
  const planActualId = props.objetivo?.plan_estrategico

  const yaIncluido = props.planes.some(
    (plan) => Number(plan.id) === Number(planActualId)
  )

  if (esEdicion.value && planActualId && !yaIncluido) {
    const tituloBase =
      planFaltante.value?.titulo || props.objetivo?.plan_estrategico_titulo || 'Plan estratégico'

    return [
      ...props.planes,
      { id: planActualId, titulo: `${tituloBase} (no disponible para nuevos objetivos)` },
    ]
  }

  return props.planes
})

watch(
  () => props.objetivo,
  () => {
    cargarFormulario()
    cargarPlanFaltante()
  },
  { immediate: true }
)

async function cargarPlanFaltante() {
  planFaltante.value = null

  const planActualId = props.objetivo?.plan_estrategico

  if (!planActualId) {
    return
  }

  const yaIncluido = props.planes.some(
    (plan) => Number(plan.id) === Number(planActualId)
  )

  if (yaIncluido) {
    return
  }

  try {
    const todos = await obtenerPlanesEstrategicosParaObjetivo()
    planFaltante.value = todos.find((plan) => Number(plan.id) === Number(planActualId)) || null
  } catch {
    planFaltante.value = null
  }
}

function cargarFormulario() {
  estado.plan_estrategico = props.objetivo?.plan_estrategico || ''
  estado.texto_objetivo = props.objetivo?.texto_objetivo || ''
  estado.error = ''
}

function validarFormulario() {
  estado.error = ''

  if (!estado.plan_estrategico) {
    estado.error = 'Seleccioná el plan estratégico relacionado con el objetivo.'
    return false
  }

  if (!estado.texto_objetivo.trim()) {
    estado.error = 'Ingresá el texto del objetivo general.'
    return false
  }

  return true
}

function guardar() {
  if (!validarFormulario()) {
    return
  }

  emit('guardar', {
    plan_estrategico: estado.plan_estrategico,
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
        <span>Plan estratégico</span>

        <select v-model="estado.plan_estrategico">
          <option value="">Seleccionar plan estratégico</option>

          <option
            v-for="plan in planesDisponibles"
            :key="plan.id"
            :value="plan.id"
          >
            {{ plan.titulo }}
          </option>
        </select>
      </label>

      <label class="field field-full">
        <span>Texto del objetivo general</span>

        <textarea
          v-model="estado.texto_objetivo"
          rows="4"
          placeholder="Ejemplo: Incrementar en 10.00 % la participación de asociados durante la vigencia del Plan estratégico."
        ></textarea>
      </label>
    </div>

    <div class="help-box">
      Solo se muestran planes estratégicos En uso: el objetivo general debe cumplirse durante toda su vigencia.
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
