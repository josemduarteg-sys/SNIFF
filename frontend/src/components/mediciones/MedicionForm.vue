<script setup>
import { computed, reactive, watch } from 'vue'
import {
  actualizarMedicion,
  crearMedicion,
  obtenerSiguientePeriodo,
} from '../../services/medicionService'
import { formatearNumero } from '../../utils/formato'

const props = defineProps({
  indicadores: {
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
  mes_medicion: '',
  valor_resultado: '',
  observacion: '',
  evidencia: '',
})

const estado = reactive({
  guardando: false,
  error: '',
  cargandoPeriodo: false,
  periodoDisponible: true,
  mensajePeriodo: '',
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

  if (!indicador?.valor_meta) {
    return null
  }

  return Number(indicador.valor_meta)
})

const unidadMedida = computed(() => indicadorSeleccionado.value?.unidad_medida || 'unidad')

const ayudaResultado = computed(() => {
  const unidad = unidadMedida.value

  if (unidad === '%') {
    return 'Ingresá el porcentaje real obtenido en el periodo. Ejemplo: 85 para representar 85%.'
  }

  if (unidad.toLowerCase().includes('q')) {
    return 'Ingresá el monto real obtenido en el periodo. Ejemplo: 85000.'
  }

  return `Ingresá el valor real obtenido en el periodo usando la unidad configurada: ${unidad}.`
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
      form.evidencia = medicion.evidencia || ''
      return
    }

    limpiarFormulario()
  },
  { immediate: true }
)

watch(
  () => form.indicador,
  (nuevoIndicador) => {
    estado.error = ''
    cargarSiguientePeriodo(nuevoIndicador)
  }
)

function limpiarFormulario() {
  form.indicador = ''
  form.mes_medicion = ''
  form.valor_resultado = ''
  form.observacion = ''
  form.evidencia = ''
}

async function cargarSiguientePeriodo(indicadorId) {
  if (!indicadorId || esEdicion.value) {
    estado.mensajePeriodo = ''
    estado.periodoDisponible = true
    return
  }

  form.mes_medicion = ''
  estado.mensajePeriodo = ''
  estado.periodoDisponible = true
  estado.cargandoPeriodo = true

  try {
    const data = await obtenerSiguientePeriodo(indicadorId)

    estado.periodoDisponible = data.disponible !== false
    estado.mensajePeriodo = data.mensaje || ''

    if (data.disponible && data.mes_medicion) {
      form.mes_medicion = data.mes_medicion
    }
  } catch (error) {
    estado.periodoDisponible = false
    estado.mensajePeriodo =
      error.response?.data?.detail ||
      'No se pudo calcular el siguiente periodo de medición.'
  } finally {
    estado.cargandoPeriodo = false
  }
}

function obtenerMesDesdeMedicion(medicion) {
  const fecha = medicion.fecha_medicion || medicion.fecha_registro || ''

  if (!fecha) return ''

  return fecha.slice(0, 7)
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

  if (!estado.periodoDisponible) {
    return estado.mensajePeriodo || 'Este KPI no tiene periodos disponibles para registrar.'
  }

  if (!form.mes_medicion) return 'No se pudo determinar el periodo de medición.'

  if (form.valor_resultado === '' || form.valor_resultado === null) {
    return 'Ingresá el valor obtenido en el mes.'
  }

  const resultado = Number(form.valor_resultado)

  if (Number.isNaN(resultado)) return 'El valor obtenido debe ser un número válido.'
  if (resultado < 0) return 'El valor obtenido no puede ser negativo.'

  if (unidadMedida.value === '%' && resultado > 100) {
    return 'Cuando la unidad de medida es porcentaje, el resultado no puede ser mayor a 100.'
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
    mes_medicion: form.mes_medicion,
    valor_resultado: form.valor_resultado,
    observacion: form.observacion,
    evidencia: form.evidencia.trim(),
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
        <strong>{{ formatearNumero(metaVigente, { unidad: unidadMedida }) }}</strong>
      </div>

      <div class="context-item">
        <span>Vigencia del KPI</span>
        <strong>
          {{ formatearFecha(indicadorSeleccionado.fecha_inicio_vigencia) }}
          al
          {{ formatearFecha(indicadorSeleccionado.fecha_fin_vigencia) }}
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
      <label>Periodo a medir</label>
      <input
        v-model="form.mes_medicion"
        type="month"
        disabled
      />
      <small>El periodo se determina automáticamente según la frecuencia configurada en el KPI.</small>

      <p v-if="estado.cargandoPeriodo" class="field-hint">
        Calculando siguiente periodo...
      </p>

      <p
        v-else-if="estado.mensajePeriodo"
        class="field-hint"
        :class="{ error: !estado.periodoDisponible }"
      >
        {{ estado.mensajePeriodo }}
      </p>
    </div>

    <div class="form-group">
      <label>Valor obtenido en el periodo</label>
      <div class="input-with-unit">
        <input
          v-model="form.valor_resultado"
          type="number"
          min="0"
          :max="unidadMedida === '%' ? 100 : undefined"
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
        placeholder="Explicá brevemente el resultado obtenido, causas o contexto del periodo evaluado."
      ></textarea>
    </div>

    <div class="form-group full">
      <label>Evidencias / respaldo de lo realizado</label>
      <textarea
        v-model="form.evidencia"
        rows="6"
        placeholder="Describe el respaldo de la medición: acciones realizadas, acuerdos, documentos revisados, resultados obtenidos, justificación del avance, etc."
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
.medicion-form,
.medicion-form * {
  box-sizing: border-box;
}

.medicion-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
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
  min-width: 0;
  box-sizing: border-box;
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

input:disabled,
select:disabled,
textarea:disabled {
  background: #f4f7f9;
  color: #9aa8b8;
  cursor: not-allowed;
}

small {
  color: #9aa8b8;
  font-size: 11.5px;
  font-weight: 600;
}

.field-hint {
  margin: 4px 0 0;
  color: #7f8fa3;
  font-size: 11.5px;
  font-weight: 650;
  line-height: 1.35;
}

.field-hint.error {
  color: #e76f51;
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
