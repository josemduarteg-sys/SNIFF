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
    required: false,
    default: () => [],
  },
  periodos: {
    type: Array,
    required: false,
    default: () => [],
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
  mes_medicion: '',
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

const indicadorSeleccionado = computed(() => {
  if (!form.indicador) return null

  return props.indicadores.find((indicador) => {
    return Number(indicador.id) === Number(form.indicador)
  }) || null
})

const metaVigente = computed(() => {
  const indicador = indicadorSeleccionado.value

  if (!indicador) return null

  if (indicador.valor_meta !== null && indicador.valor_meta !== undefined && indicador.valor_meta !== '') {
    return {
      valor_meta: indicador.valor_meta,
      fecha_inicio: indicador.fecha_inicio,
      fecha_fin: indicador.fecha_fin,
      origen: 'kpi',
    }
  }

  return props.metas.find((meta) => {
    return Number(meta.indicador) === Number(indicador.id) && meta.estado === 'vigente'
  }) || props.metas.find((meta) => Number(meta.indicador) === Number(indicador.id)) || null
})

const unidadMedida = computed(() => indicadorSeleccionado.value?.unidad_medida || 'unidad')

const ayudaResultado = computed(() => {
  const unidad = unidadMedida.value

  if (unidad === '%') {
    return 'Ingresá el porcentaje real obtenido en el mes. Ejemplo: 85 para representar 85%.'
  }

  if (unidad.toLowerCase().includes('q')) {
    return 'Ingresá el monto real obtenido en el mes. Ejemplo: 85000.'
  }

  return `Ingresá el valor real obtenido en el mes usando la unidad configurada: ${unidad}.`
})

watch(
  () => props.medicionEditar,
  (medicion) => {
    estado.error = ''

    if (medicion?.id) {
      form.indicador = medicion.indicador || ''
      form.mes_medicion = obtenerMesDesdeMedicion(medicion)
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
    estado.error = ''
  }
)

function limpiarFormulario() {
  form.indicador = ''
  form.mes_medicion = ''
  form.valor_resultado = ''
  form.observacion = ''
}

function obtenerMesDesdeMedicion(medicion) {
  const fecha = medicion.fecha_medicion || medicion.fecha_registro || ''

  if (!fecha) return ''

  return fecha.slice(0, 7)
}

function formatearNumero(valor) {
  if (valor === null || valor === undefined || valor === '') return '-'

  const numero = Number(valor)

  if (Number.isNaN(numero)) return valor

  return numero.toLocaleString('es-GT', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })
}

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

function textoEstadoKpi(estadoKpi) {
  const estados = {
    borrador: 'Borrador',
    autorizado: 'Autorizado',
    inactivo: 'Inactivo',
    anulado: 'Anulado',
    activo: 'Activo',
  }

  return estados[estadoKpi] || estadoKpi || 'Sin estado'
}

function validarFormulario() {
  if (!form.indicador) return 'Seleccioná el KPI.'

  if (!metaVigente.value) {
    return 'El KPI seleccionado no tiene una meta configurada. Primero configurá la meta en el KPI.'
  }

  if (!form.mes_medicion) return 'Seleccioná el mes que se va a medir.'

  if (form.valor_resultado === '' || form.valor_resultado === null) {
    return 'Ingresá el valor obtenido en el mes.'
  }

  const resultado = Number(form.valor_resultado)

  if (Number.isNaN(resultado)) return 'El valor obtenido debe ser un número válido.'
  if (resultado < 0) return 'El valor obtenido no puede ser negativo.'

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
    mes_medicion: form.mes_medicion,
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

    <section v-if="indicadorSeleccionado" class="kpi-context full">
      <div class="context-item">
        <span>Meta configurada</span>
        <strong>{{ formatearNumero(metaVigente?.valor_meta) }} {{ unidadMedida }}</strong>
      </div>

      <div class="context-item">
        <span>Vigencia del KPI</span>
        <strong>
          {{ formatearFecha(indicadorSeleccionado.fecha_inicio || metaVigente?.fecha_inicio) }}
          al
          {{ formatearFecha(indicadorSeleccionado.fecha_fin || metaVigente?.fecha_fin) }}
        </strong>
      </div>

      <div class="context-item">
        <span>Frecuencia / seguimiento</span>
        <strong>{{ indicadorSeleccionado.frecuencia_nombre || 'Mensual' }}</strong>
      </div>

      <div class="context-item">
        <span>Estado del KPI</span>
        <strong>{{ textoEstadoKpi(indicadorSeleccionado.estado) }}</strong>
      </div>
    </section>

    <div class="form-group">
      <label>Mes de medición</label>
      <input
        v-model="form.mes_medicion"
        type="month"
      />
      <small>La medición se registra por corte mensual.</small>
    </div>

    <div class="form-group">
      <label>Valor obtenido en el mes</label>
      <div class="input-with-unit">
        <input
          v-model="form.valor_resultado"
          type="number"
          min="0"
          step="0.01"
          placeholder="Ejemplo: 85"
        />
        <span>{{ unidadMedida }}</span>
      </div>
      <small>{{ ayudaResultado }}</small>
    </div>

    <div class="form-group full">
      <label>Razones / observaciones</label>
      <textarea
        v-model="form.observacion"
        rows="4"
        placeholder="Explicá brevemente el resultado obtenido, causas o contexto del mes evaluado."
      ></textarea>
    </div>

    <div v-if="estado.error" class="form-error full">
      {{ estado.error }}
    </div>

    <div class="form-actions full">
      <button
        class="btn-secondary"
        type="button"
        :disabled="estado.guardando"
        @click="emit('cancelar')"
      >
        Cancelar
      </button>

      <button
        class="btn-primary"
        type="submit"
        :disabled="estado.guardando"
      >
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
  min-height: 96px;
  padding-top: 11px;
  resize: vertical;
}

input:focus,
select:focus,
textarea:focus {
  border-color: #a8dadc;
}

small {
  color: #9aa8b8;
  font-size: 11.5px;
  font-weight: 600;
}

.kpi-context {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  background: #f6f9fa;
  border: 1px solid #e4eaef;
}

.context-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.context-item span {
  color: #9aa8b8;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-item strong {
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
}

.input-with-unit {
  display: flex;
  align-items: center;
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
}

.input-with-unit:focus-within {
  border-color: #a8dadc;
}

.input-with-unit input {
  border: none;
  border-radius: 0;
}

.input-with-unit span {
  height: 40px;
  min-width: 48px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 12px;
  font-weight: 800;
}

.form-error {
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
  font-size: 13px;
  font-weight: 700;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
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

.btn-secondary {
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

@media (max-width: 700px) {
  .medicion-form,
  .kpi-context {
    grid-template-columns: 1fr;
  }
}
</style>
