<script setup>
import { computed, reactive, watch } from 'vue'
import SelectorBuscable from '../common/SelectorBuscable.vue'
import { obtenerSiguientePeriodo } from '../../services/medicionService'
import { crearSolicitudAmpliacion } from '../../services/solicitudAmpliacionService'
import {
  DIAS_MAXIMOS_AMPLIACION,
  diasValidos,
  formatearFechaIso,
  sumarDias,
} from '../../utils/ampliaciones'

// Etapa 5: el Ejecutor elige el KPI; el periodo y la fecha límite ordinaria
// los informa el backend (siempre el siguiente periodo esperado del KPI).

const props = defineProps({
  indicadores: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['guardado', 'cancelar'])

const form = reactive({
  indicador: '',
  dias_solicitados: 5,
  motivo: '',
})

const estado = reactive({
  guardando: false,
  error: '',
  cargandoPeriodo: false,
  periodo: null,
})

const opcionesKpi = computed(() => {
  return props.indicadores.map((indicador) => ({
    id: indicador.id,
    texto: `${indicador.nombre} — ${indicador.plan_anual_nombre || 'Sin plan anual'}`,
  }))
})

const nuevoPlazo = computed(() => {
  if (!estado.periodo?.fecha_limite_ordinaria || !diasValidos(form.dias_solicitados)) return null

  return sumarDias(estado.periodo.fecha_limite_ordinaria, form.dias_solicitados)
})

const puedeGuardar = computed(() => {
  return (
    !estado.guardando &&
    !estado.cargandoPeriodo &&
    estado.periodo?.puede_solicitar_ampliacion === true &&
    diasValidos(form.dias_solicitados) &&
    form.motivo.trim() !== ''
  )
})

watch(
  () => form.indicador,
  async (indicadorId) => {
    estado.periodo = null
    estado.error = ''

    if (!indicadorId) return

    estado.cargandoPeriodo = true

    try {
      estado.periodo = await obtenerSiguientePeriodo(indicadorId)
    } catch (error) {
      estado.error = error.response?.data?.detail || 'No se pudo consultar el periodo del KPI.'
    } finally {
      estado.cargandoPeriodo = false
    }
  },
)

async function guardar() {
  if (!puedeGuardar.value) return

  estado.guardando = true
  estado.error = ''

  try {
    const solicitud = await crearSolicitudAmpliacion({
      indicador: form.indicador,
      dias_solicitados: Number(form.dias_solicitados),
      motivo: form.motivo.trim(),
    })

    emit('guardado', solicitud)
  } catch (error) {
    const data = error.response?.data

    if (data?.detail) {
      estado.error = data.detail
    } else if (typeof data === 'object' && data !== null) {
      estado.error = Object.values(data).flat().join(' ')
    } else {
      estado.error = 'No se pudo enviar la solicitud.'
    }
  } finally {
    estado.guardando = false
  }
}
</script>

<template>
  <form class="ampliacion-form" @submit.prevent="guardar">
    <div class="form-group full">
      <label>KPI</label>
      <SelectorBuscable
        v-model="form.indicador"
        :opciones="opcionesKpi"
        placeholder="Seleccionar KPI"
        placeholder-busqueda="Escribí el nombre del KPI..."
        mensaje-vacio="No hay KPI autorizados disponibles."
      />
    </div>

    <p v-if="estado.cargandoPeriodo" class="field-hint full">
      Consultando el periodo del KPI...
    </p>

    <template v-else-if="estado.periodo">
      <section class="contexto full">
        <div class="context-item">
          <span>Periodo</span>
          <strong>{{ estado.periodo.periodo_nombre || 'Sin periodo pendiente' }}</strong>
        </div>
        <div class="context-item">
          <span>Cierre del periodo</span>
          <strong>{{ formatearFechaIso(estado.periodo.fecha_cierre) }}</strong>
        </div>
        <div class="context-item">
          <span>Fecha límite ordinaria</span>
          <strong>{{ formatearFechaIso(estado.periodo.fecha_limite_ordinaria) }}</strong>
        </div>
        <div class="context-item">
          <span>Plazo solicitado</span>
          <strong>{{ nuevoPlazo ? formatearFechaIso(nuevoPlazo) : '—' }}</strong>
        </div>
      </section>

      <p v-if="!estado.periodo.puede_solicitar_ampliacion" class="field-hint error full">
        {{ estado.periodo.motivo_ampliacion }}
      </p>

      <template v-else>
        <div class="form-group">
          <label for="dias-ampliacion">Días adicionales</label>
          <input
            id="dias-ampliacion"
            v-model.number="form.dias_solicitados"
            type="number"
            min="1"
            :max="DIAS_MAXIMOS_AMPLIACION"
            step="1"
          />
          <small>De 1 a {{ DIAS_MAXIMOS_AMPLIACION }} días calendario, contados desde la fecha límite ordinaria.</small>
        </div>

        <div class="form-group full">
          <label for="motivo-ampliacion">Motivo</label>
          <textarea
            id="motivo-ampliacion"
            v-model="form.motivo"
            maxlength="2000"
            placeholder="Explicá por qué necesitás más tiempo para registrar la medición."
          ></textarea>
        </div>

        <p class="field-hint full">
          Si el plazo ordinario vence antes de que se resuelva la solicitud, no vas a poder registrar
          hasta que se autorice. El cierre automático espera como máximo hasta el
          {{ formatearFechaIso(sumarDias(estado.periodo.fecha_limite_ordinaria, DIAS_MAXIMOS_AMPLIACION)) }}.
        </p>
      </template>
    </template>

    <div v-if="estado.error" class="form-error full">
      {{ estado.error }}
    </div>

    <div class="form-actions full">
      <button class="btn-secondary" type="button" :disabled="estado.guardando" @click="emit('cancelar')">
        Cancelar
      </button>
      <button class="btn-primary" type="submit" :disabled="!puedeGuardar">
        {{ estado.guardando ? 'Enviando...' : 'Enviar solicitud' }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.ampliacion-form,
.ampliacion-form * {
  box-sizing: border-box;
}

.ampliacion-form {
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

.full {
  grid-column: 1 / -1;
}

label {
  color: #1d3557;
  font-size: 12px;
  font-weight: 800;
}

input,
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

input {
  height: 40px;
}

textarea {
  min-height: 96px;
  padding-top: 11px;
  resize: vertical;
}

input:focus,
textarea:focus {
  border-color: #a8dadc;
}

small {
  color: #9aa8b8;
  font-size: 11.5px;
  font-weight: 600;
}

.field-hint {
  margin: 0;
  color: #7f8fa3;
  font-size: 11.5px;
  font-weight: 650;
  line-height: 1.35;
}

.field-hint.error {
  color: #e76f51;
  font-size: 12.5px;
}

.contexto {
  display: grid;
  grid-template-columns: repeat(2, minmax(160px, 1fr));
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
  letter-spacing: 0.4px;
}

.context-item strong {
  color: #1d3557;
  font-size: 13px;
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
  .ampliacion-form,
  .contexto {
    grid-template-columns: 1fr;
  }
}
</style>
