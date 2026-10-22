<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { configurarRangosKpi, obtenerEstadosCumplimiento } from '../../services/indicadorService'
import { ESTADOS_RANGO, validarFilasRangos } from '../../utils/rangos'

// D3: configuración de los rangos de evaluación de un KPI en Borrador, dentro
// del detalle del KPI (sin pantalla administrativa nueva). Pensado sobre todo
// para KPI que no se miden en % (no reciben la plantilla 60/75): por ejemplo,
// en días, donde un valor menor es mejor y Favorable va en el tramo más bajo.
// Se guarda el conjunto completo en una sola operación del backend.

const props = defineProps({
  indicador: {
    type: Object,
    required: true,
  },
  rangos: {
    type: Array,
    required: false,
    default: () => [],
  },
})

const emit = defineEmits(['guardado', 'cancelar'])

const estados = ref([])
const filas = reactive([])
const guardando = ref(false)
const error = ref('')

const unidad = computed(() => props.indicador.unidad_medida || '')

onMounted(async () => {
  try {
    estados.value = await obtenerEstadosCumplimiento()
  } catch (e) {
    error.value = 'No se pudo cargar el catálogo de estados de cumplimiento.'
    return
  }

  ESTADOS_RANGO.forEach((nombre) => {
    const estado = estados.value.find((item) => item.nombre === nombre)
    const actual = props.rangos.find((rango) => rango.estado_cumplimiento_nombre === nombre && rango.estado !== false)

    if (estado) {
      filas.push({
        nombre,
        estado_cumplimiento: estado.id,
        valor_minimo: actual ? Number(actual.valor_minimo) : '',
        valor_maximo: actual && actual.valor_maximo !== null ? Number(actual.valor_maximo) : '',
      })
    }
  })

  if (filas.length < ESTADOS_RANGO.length) {
    error.value = 'Faltan estados de cumplimiento en el catálogo (Incumplido, En riesgo, Favorable).'
  }
})

async function guardar() {
  error.value = ''
  const errores = validarFilasRangos(filas)

  if (errores.length) {
    error.value = errores.join(' ')
    return
  }

  guardando.value = true

  try {
    const rangos = await configurarRangosKpi(props.indicador.id, filas.map((fila) => ({
      estado_cumplimiento: fila.estado_cumplimiento,
      valor_minimo: fila.valor_minimo,
      valor_maximo: fila.valor_maximo === '' ? null : fila.valor_maximo,
    })))
    emit('guardado', rangos)
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudieron guardar los rangos.'
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <form class="rangos-editor" @submit.prevent="guardar">
    <p class="ayuda">
      Valores en <strong>{{ unidad || 'la unidad del KPI' }}</strong>. El mínimo se incluye en el rango y el máximo
      no; dejá el máximo vacío para «sin límite». Si en este KPI un valor menor es mejor (por ejemplo, días),
      asigná <strong>Favorable</strong> al tramo más bajo.
    </p>

    <div class="rangos-tabla">
      <div class="rangos-cabecera">
        <span>Estado</span>
        <span>Mínimo (incluido)</span>
        <span>Máximo (no incluido)</span>
      </div>
      <div v-for="fila in filas" :key="fila.nombre" class="rangos-fila">
        <strong>{{ fila.nombre }}</strong>
        <input v-model="fila.valor_minimo" type="number" min="0" step="0.01" :aria-label="`Mínimo de ${fila.nombre}`" />
        <input v-model="fila.valor_maximo" type="number" min="0" step="0.01" placeholder="Sin límite" :aria-label="`Máximo de ${fila.nombre}`" />
      </div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="acciones">
      <button type="button" class="btn-secundario" :disabled="guardando" @click="emit('cancelar')">Cancelar</button>
      <button type="submit" class="btn-primario" :disabled="guardando || filas.length < 3">
        {{ guardando ? 'Guardando...' : 'Guardar rangos' }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.rangos-editor { display: flex; flex-direction: column; gap: 12px; }
.ayuda { margin: 0; font-size: 12px; color: #5e6e82; line-height: 1.45; }
.rangos-tabla { display: flex; flex-direction: column; gap: 8px; }
.rangos-cabecera,
.rangos-fila { display: grid; grid-template-columns: 110px 1fr 1fr; gap: 10px; align-items: center; }
.rangos-cabecera span { font-size: 11px; font-weight: 800; color: #9aa8b8; text-transform: uppercase; letter-spacing: 0.3px; }
.rangos-fila strong { font-size: 13px; color: #1d3557; }
.rangos-fila input {
  height: 36px;
  min-width: 0;
  border: 1.5px solid #e4eaef;
  border-radius: 8px;
  padding: 0 10px;
  font-family: inherit;
  font-size: 13px;
  color: #1d3557;
}
.error { padding: 10px 12px; border-radius: 8px; background: rgba(231, 111, 81, 0.12); color: #e76f51; font-size: 12.5px; font-weight: 700; }
.acciones { display: flex; justify-content: flex-end; gap: 8px; }
.btn-primario,
.btn-secundario { height: 36px; padding: 0 14px; border-radius: 9px; font-family: inherit; font-size: 12.5px; font-weight: 800; cursor: pointer; }
.btn-primario { border: none; background: #1d3557; color: #ffffff; }
.btn-secundario { border: 1.5px solid #e4eaef; background: #ffffff; color: #5e6e82; }
.btn-primario:disabled,
.btn-secundario:disabled { opacity: 0.6; cursor: not-allowed; }
@media (max-width: 520px) {
  .rangos-cabecera,
  .rangos-fila { grid-template-columns: 80px 1fr 1fr; }
}
</style>
