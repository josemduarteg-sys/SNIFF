<script setup>
import { computed, reactive, watch } from 'vue'
import { crearMedicion } from '../../services/medicionService'

const props = defineProps({
  indicadores: {
    type: Array,
    required: true,
  },
  metas: {
    type: Array,
    required: true,
  },
  periodos: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['guardado', 'cancelar'])

const form = reactive({
  indicador: '',
  meta: '',
  periodo: '',
  valor_resultado: '',
  observacion: '',
})

const estado = reactive({
  guardando: false,
  error: '',
})

const metasDisponibles = computed(() => {
  if (!form.indicador) {
    return []
  }

  return props.metas.filter((meta) => Number(meta.indicador) === Number(form.indicador))
})

const metaSeleccionada = computed(() => {
  return props.metas.find((meta) => Number(meta.id) === Number(form.meta)) || null
})

const indicadorSeleccionado = computed(() => {
  return props.indicadores.find((indicador) => Number(indicador.id) === Number(form.indicador)) || null
})

watch(
  () => form.indicador,
  () => {
    form.meta = ''
  }
)

function textoMeta(meta) {
  const valor = meta.valor_meta ?? meta.valor ?? '-'
  const inicio = meta.fecha_inicio || 'sin inicio'
  const fin = meta.fecha_fin || 'sin fin'
  return `${formatearNumero(valor)} · ${inicio} a ${fin}`
}

function formatearNumero(valor) {
  if (valor === null || valor === undefined || valor === '') {
    return '-'
  }

  const numero = Number(valor)

  if (Number.isNaN(numero)) {
    return valor
  }

  return numero.toLocaleString('es-GT', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })
}

function validarFormulario() {
  if (!form.indicador) {
    return 'Seleccioná el indicador KPI.'
  }

  if (!form.meta) {
    return 'Seleccioná la meta contra la que se evaluará la medición.'
  }

  if (!form.periodo) {
    return 'Seleccioná el periodo de medición.'
  }

  if (form.valor_resultado === '' || form.valor_resultado === null) {
    return 'Ingresá el resultado medido.'
  }

  if (Number.isNaN(Number(form.valor_resultado))) {
    return 'El resultado medido debe ser un número válido.'
  }

  return ''
}

async function guardar() {
  estado.error = ''

  const errorValidacion = validarFormulario()

  if (errorValidacion) {
    estado.error = errorValidacion
    return
  }

  estado.guardando = true

  try {
    const medicion = await crearMedicion({
      indicador: Number(form.indicador),
      meta: Number(form.meta),
      periodo: Number(form.periodo),
      valor_resultado: form.valor_resultado,
      observacion: form.observacion,
    })

    emit('guardado', medicion)
  } catch (error) {
    const data = error.response?.data

    if (data && typeof data === 'object') {
      const primerError = Object.values(data).flat().join(' ')
      estado.error = primerError || 'No se pudo guardar la medición.'
    } else {
      estado.error = 'No se pudo guardar la medición.'
    }
  } finally {
    estado.guardando = false
  }
}

function cancelar() {
  emit('cancelar')
}
</script>

<template>
  <form class="form-grid" @submit.prevent="guardar">
    <div class="form-group full">
      <label>Indicador KPI</label>
      <select v-model="form.indicador">
        <option value="">Seleccionar indicador</option>
        <option
          v-for="indicador in indicadores"
          :key="indicador.id"
          :value="indicador.id"
        >
          {{ indicador.nombre }}
        </option>
      </select>
    </div>

    <div class="form-group">
      <label>Meta</label>
      <select v-model="form.meta" :disabled="!form.indicador">
        <option value="">
          {{ form.indicador ? 'Seleccionar meta' : 'Primero seleccioná un KPI' }}
        </option>
        <option
          v-for="meta in metasDisponibles"
          :key="meta.id"
          :value="meta.id"
        >
          {{ textoMeta(meta) }}
        </option>
      </select>
    </div>

    <div class="form-group">
      <label>Periodo</label>
      <select v-model="form.periodo">
        <option value="">Seleccionar periodo</option>
        <option
          v-for="periodo in periodos"
          :key="periodo.id"
          :value="periodo.id"
        >
          {{ periodo.nombre || periodo.periodo_nombre || `Periodo ${periodo.id}` }}
        </option>
      </select>
    </div>

    <div class="form-group">
      <label>Resultado medido</label>
      <input
        v-model="form.valor_resultado"
        type="number"
        step="0.01"
        min="0"
        placeholder="Ej. 85000"
      />
    </div>

    <div class="form-group">
      <label>Unidad</label>
      <input
        :value="indicadorSeleccionado?.unidad_medida || '-'"
        type="text"
        disabled
      />
    </div>

    <div v-if="metaSeleccionada" class="info-box full">
      <strong>Meta seleccionada:</strong>
      <span>{{ formatearNumero(metaSeleccionada.valor_meta ?? metaSeleccionada.valor) }}</span>
    </div>

    <div class="form-group full">
      <label>Observaciones</label>
      <textarea
        v-model="form.observacion"
        rows="3"
        placeholder="Observaciones opcionales de la medición"
      ></textarea>
    </div>

    <div v-if="estado.error" class="alert error full">
      {{ estado.error }}
    </div>

    <div class="form-actions full">
      <button class="btn-secondary" type="button" @click="cancelar">
        Cancelar
      </button>

      <button class="btn-primary" type="submit" :disabled="estado.guardando">
        {{ estado.guardando ? 'Guardando...' : 'Guardar medición' }}
      </button>
    </div>
  </form>
</template>

<style scoped>
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

input,
select,
textarea {
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  padding: 0 12px;
  font-family: inherit;
  color: #1d3557;
  outline: none;
  background: #ffffff;
}

input,
select {
  height: 40px;
}

textarea {
  resize: vertical;
  min-height: 86px;
  padding-top: 10px;
}

input:focus,
select:focus,
textarea:focus {
  border-color: #a8dadc;
}

input:disabled,
select:disabled {
  background: #f6f9fa;
  color: #9aa8b8;
  cursor: not-allowed;
}

.info-box {
  padding: 12px 14px;
  border-radius: 12px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-box strong {
  color: #1d3557;
}

.alert {
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
}

.alert.error {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
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
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-secondary {
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
}

.btn-secondary:hover {
  background: #f6f9fa;
}

@media (max-width: 700px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
