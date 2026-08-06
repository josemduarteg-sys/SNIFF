<script setup>
import { computed, reactive, watch } from 'vue'
import { actualizarMedicion, crearMedicion } from '../../services/medicionService'

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
  medicionEditar: {
    type: Object,
    required: false,
    default: null,
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

const esEdicion = computed(() => !!props.medicionEditar?.id)

const tituloBoton = computed(() => {
  if (estado.guardando) return esEdicion.value ? 'Actualizando...' : 'Guardando...'
  return esEdicion.value ? 'Actualizar medición' : 'Guardar medición'
})

const metasDisponibles = computed(() => {
  if (!form.indicador) return props.metas

  return props.metas.filter((meta) => {
    return Number(meta.indicador) === Number(form.indicador)
  })
})

watch(
  () => props.medicionEditar,
  (medicion) => {
    estado.error = ''

    if (medicion?.id) {
      form.indicador = medicion.indicador || ''
      form.meta = medicion.meta || ''
      form.periodo = medicion.periodo || ''
      form.valor_resultado = medicion.valor_resultado || ''
      form.observacion = medicion.observacion || medicion.observaciones || ''
      return
    }

    limpiarFormulario()
  },
  { immediate: true }
)

watch(
  () => form.indicador,
  () => {
    if (!form.meta) return

    const metaExiste = metasDisponibles.value.some((meta) => {
      return Number(meta.id) === Number(form.meta)
    })

    if (!metaExiste) {
      form.meta = ''
    }
  }
)

function limpiarFormulario() {
  form.indicador = ''
  form.meta = ''
  form.periodo = ''
  form.valor_resultado = ''
  form.observacion = ''
}

function obtenerValorMeta(meta) {
  if (meta.valor_meta !== undefined && meta.valor_meta !== null) return meta.valor_meta
  if (meta.valor !== undefined && meta.valor !== null) return meta.valor
  return '-'
}

function formatearMeta(meta) {
  const valor = obtenerValorMeta(meta)
  const indicador = meta.indicador_nombre ? ` - ${meta.indicador_nombre}` : ''
  return `${valor}${indicador}`
}

function validarFormulario() {
  if (!form.indicador) return 'Seleccioná el KPI.'
  if (!form.meta) return 'Seleccioná la meta asociada.'
  if (!form.periodo) return 'Seleccioná el periodo de medición.'
  if (form.valor_resultado === '' || form.valor_resultado === null) return 'Ingresá el resultado medido.'

  const resultado = Number(form.valor_resultado)

  if (Number.isNaN(resultado)) {
    return 'El resultado medido debe ser un número válido.'
  }

  if (resultado < 0) {
    return 'El resultado medido no puede ser negativo.'
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

  const payload = {
    indicador: Number(form.indicador),
    meta: Number(form.meta),
    periodo: Number(form.periodo),
    valor_resultado: form.valor_resultado,
    observacion: form.observacion,
  }

  try {
    if (esEdicion.value) {
      await actualizarMedicion(props.medicionEditar.id, payload)
    } else {
      await crearMedicion(payload)
    }

    emit('guardado')
    limpiarFormulario()
  } catch (error) {
    const data = error.response?.data

    if (data?.non_field_errors) {
      estado.error = data.non_field_errors.join(' ')
    } else if (data?.detail) {
      estado.error = data.detail
    } else if (typeof data === 'object' && data !== null) {
      const primerCampo = Object.keys(data)[0]
      const mensaje = data[primerCampo]
      estado.error = Array.isArray(mensaje) ? mensaje.join(' ') : String(mensaje)
    } else {
      estado.error = esEdicion.value
        ? 'No se pudo actualizar la medición.'
        : 'No se pudo guardar la medición.'
    }
  } finally {
    estado.guardando = false
  }
}
</script>

<template>
  <form class="medicion-form" @submit.prevent="guardar">
    <div class="form-group full">
      <label>KPI</label>
      <select v-model="form.indicador">
        <option value="">Seleccionar KPI</option>

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
      <select v-model="form.meta">
        <option value="">Seleccionar meta</option>

        <option
          v-for="meta in metasDisponibles"
          :key="meta.id"
          :value="meta.id"
        >
          {{ formatearMeta(meta) }}
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
          {{ periodo.nombre || periodo.periodo_nombre || periodo.descripcion }}
        </option>
      </select>
    </div>

    <div class="form-group full">
      <label>Resultado medido</label>
      <input
        v-model="form.valor_resultado"
        type="number"
        min="0"
        step="0.01"
        placeholder="Ejemplo: 85000"
      />
    </div>

    <div class="form-group full">
      <label>Observaciones</label>
      <textarea
        v-model="form.observacion"
        rows="3"
        placeholder="Agregar observaciones de la medición"
      ></textarea>
    </div>

    <div v-if="estado.error" class="alert error full">
      {{ estado.error }}
    </div>

    <div class="form-actions full">
      <button class="btn-secondary" type="button" @click="emit('cancelar')">
        Cancelar
      </button>

      <button class="btn-primary" type="submit" :disabled="estado.guardando">
        {{ tituloBoton }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.medicion-form {
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
  width: 100%;
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
  padding-top: 10px;
  resize: vertical;
}

input:focus,
select:focus,
textarea:focus {
  border-color: #a8dadc;
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
  padding-top: 4px;
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

@media (max-width: 640px) {
  .medicion-form {
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
