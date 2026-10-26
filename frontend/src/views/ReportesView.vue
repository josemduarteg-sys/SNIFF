<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import MedicionDetalle from '../components/mediciones/MedicionDetalle.vue'
import GraficaHistoricaKpi from '../components/reportes/GraficaHistoricaKpi.vue'
import SelectorBuscable from '../components/common/SelectorBuscable.vue'
import { descargarReportePdfKpi, obtenerIndicadoresKpi } from '../services/indicadorService'
import { obtenerMedicionesKpi } from '../services/medicionService'
import { formatearNumero } from '../utils/formato'
import { textoObjetivoKpi } from '../utils/objetivos'
import { SIN_REGISTRO, claseColorCumplimiento, esMedicionSinRegistro, textoEstadoCumplimiento } from '../utils/cumplimiento'
import {
  kpiVigente,
  kpisConsultables,
  kpisDe,
  normalizarSeleccion,
  ordenarCronologicamente,
  planesAnualesDe,
  planesEstrategicosDe,
} from '../utils/reportes'

// D5: consulta histórica y reporte de un KPI. Solo lectura para los cuatro
// roles: no hay acciones de modificación en esta vista.
const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])
const route = useRoute()

// Todos los KPI que devuelve la API; `kpis` aplica la vigencia (por defecto
// solo vigentes, o también los de planes cerrados si se pide el histórico).
const todosKpis = ref([])
const incluirCerrados = ref(false)
const kpis = computed(() => kpisConsultables(todosKpis.value, { incluirCerrados: incluirCerrados.value }))
const hayCerrados = computed(() => kpisConsultables(todosKpis.value, { incluirCerrados: true }).some((kpi) => !kpiVigente(kpi)))
const mediciones = ref([])
const cargando = ref(true)
const cargandoMediciones = ref(false)
const error = ref('')
const errorPdf = ref('')
const generandoPdf = ref(false)
const medicionDetalle = ref(null)

const seleccion = reactive({ planEstrategico: '', planAnual: '', kpi: '' })

const planesEstrategicos = computed(() => planesEstrategicosDe(kpis.value))
const planesAnuales = computed(() => planesAnualesDe(kpis.value, seleccion.planEstrategico))
const kpisFiltrados = computed(() => kpisDe(kpis.value, seleccion.planEstrategico, seleccion.planAnual))

// Opciones para SelectorBuscable ({ id, texto }); "Todos" es la opción inicial.
const opcionesPlanEstrategico = computed(() => [
  { id: '', texto: 'Todos' },
  ...planesEstrategicos.value.map((plan) => ({ id: plan.id, texto: plan.nombre })),
])
const opcionesPlanAnual = computed(() => [
  { id: '', texto: 'Todos' },
  ...planesAnuales.value.map((plan) => ({ id: plan.id, texto: plan.nombre })),
])
const opcionesKpi = computed(() => kpisFiltrados.value.map((kpi) => ({
  id: kpi.id,
  texto: kpiVigente(kpi) ? kpi.nombre : `${kpi.nombre} (plan cerrado)`,
})))
const kpiSeleccionado = computed(() => kpis.value.find((kpi) => Number(kpi.id) === Number(seleccion.kpi)) || null)
const medicionesOrdenadas = computed(() => ordenarCronologicamente(mediciones.value))
const unidad = computed(() => kpiSeleccionado.value?.unidad_medida || '')

const resumen = computed(() => {
  const lista = medicionesOrdenadas.value
  const omisiones = lista.filter(esMedicionSinRegistro).length

  return {
    periodos: lista.length,
    conResultado: lista.length - omisiones,
    omisiones,
    evidencias: lista.reduce((total, medicion) => total + (medicion.cantidad_evidencias || 0), 0),
  }
})

function aplicarCoherencia() {
  Object.assign(seleccion, normalizarSeleccion(kpis.value, { ...seleccion }))
}

watch(() => seleccion.planEstrategico, aplicarCoherencia)
watch(() => seleccion.planAnual, aplicarCoherencia)
watch(incluirCerrados, aplicarCoherencia)

watch(() => seleccion.kpi, async (id) => {
  mediciones.value = []
  errorPdf.value = ''

  if (!id) return

  cargandoMediciones.value = true

  try {
    mediciones.value = await obtenerMedicionesKpi(id)
  } catch {
    error.value = 'No se pudo cargar el historial del KPI.'
  } finally {
    cargandoMediciones.value = false
  }
})

// Al elegir un KPI directamente, los planes se completan solos.
function elegirKpi(id) {
  const kpi = kpis.value.find((item) => Number(item.id) === Number(id))

  if (!kpi) {
    seleccion.kpi = ''
    return
  }

  if (kpi) {
    seleccion.planEstrategico = kpi.plan_estrategico
    seleccion.planAnual = kpi.plan_anual
  }

  seleccion.kpi = id
}

onMounted(async () => {
  try {
    todosKpis.value = await obtenerIndicadoresKpi()

    if (route.query.kpi) {
      // Un enlace a un KPI de un plan cerrado abre directamente el histórico.
      const pedido = kpisConsultables(todosKpis.value, { incluirCerrados: true })
        .find((kpi) => Number(kpi.id) === Number(route.query.kpi))

      if (pedido && !kpiVigente(pedido)) incluirCerrados.value = true
      elegirKpi(Number(route.query.kpi))
    }
  } catch {
    error.value = 'No se pudieron cargar los KPI.'
  } finally {
    cargando.value = false
  }
})

function textoValor(valor) {
  return formatearNumero(valor, { unidad: unidad.value })
}

function textoFecha(fecha) {
  if (!fecha) return '-'
  const [anio, mes, dia] = fecha.slice(0, 10).split('-')
  return `${dia}/${mes}/${anio}`
}

async function descargarPdf() {
  if (!kpiSeleccionado.value) return

  generandoPdf.value = true
  errorPdf.value = ''

  try {
    const blob = await descargarReportePdfKpi(kpiSeleccionado.value.id)
    const url = window.URL.createObjectURL(blob)
    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = `reporte_kpi_${kpiSeleccionado.value.id}.pdf`
    document.body.appendChild(enlace)
    enlace.click()
    enlace.remove()
    window.setTimeout(() => window.URL.revokeObjectURL(url), 60000)
  } catch {
    errorPdf.value = 'No se pudo generar el reporte PDF. Intentá de nuevo.'
  } finally {
    generandoPdf.value = false
  }
}
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Reportes de KPI"
    subtitulo="Consulta histórica de cada KPI: resultados por periodo, evolución y evidencias."
    breadcrumb-actual="Reportes"
    @logout="emit('logout')"
  >
    <section class="reporte-card filtros">
      <div class="filtro">
        <span>Plan estratégico</span>
        <SelectorBuscable
          v-model="seleccion.planEstrategico"
          :opciones="opcionesPlanEstrategico"
          :disabled="cargando"
          etiqueta="Plan estratégico"
          placeholder="Todos"
          placeholder-busqueda="Buscar plan estratégico..."
        />
      </div>

      <div class="filtro">
        <span>Plan anual</span>
        <SelectorBuscable
          v-model="seleccion.planAnual"
          :opciones="opcionesPlanAnual"
          :disabled="cargando"
          etiqueta="Plan anual"
          placeholder="Todos"
          placeholder-busqueda="Buscar plan anual..."
        />
      </div>

      <div class="filtro filtro-kpi">
        <span>KPI</span>
        <SelectorBuscable
          :model-value="seleccion.kpi"
          :opciones="opcionesKpi"
          :disabled="cargando"
          etiqueta="KPI"
          placeholder="Seleccioná un KPI"
          placeholder-busqueda="Buscar KPI por nombre..."
          mensaje-vacio="Ningún KPI coincide con los filtros"
          @update:model-value="elegirKpi"
        />
      </div>

      <label v-if="hayCerrados || incluirCerrados" class="filtro-historico">
        <input v-model="incluirCerrados" type="checkbox" />
        <span>Incluir KPI de planes cerrados (consulta histórica)</span>
      </label>
    </section>

    <p v-if="error" class="mensaje error">{{ error }}</p>
    <p v-else-if="cargando" class="mensaje">Cargando KPI...</p>
    <p v-else-if="!kpis.length" class="mensaje">
      {{ incluirCerrados ? 'Todavía no hay KPI autorizados para consultar.' : 'No hay KPI vigentes para consultar. Podés incluir los de planes cerrados.' }}
    </p>
    <p v-else-if="!kpiSeleccionado" class="mensaje">Seleccioná un KPI para ver su historial.</p>

    <template v-if="kpiSeleccionado">
      <section class="reporte-card">
        <div class="kpi-encabezado">
          <div>
            <h2>{{ kpiSeleccionado.nombre }}</h2>
            <p class="kpi-jerarquia">
              {{ kpiSeleccionado.plan_estrategico_titulo }} · {{ kpiSeleccionado.plan_anual_nombre }}
            </p>
          </div>

          <button class="btn-pdf" type="button" :disabled="generandoPdf" @click="descargarPdf">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            {{ generandoPdf ? 'Generando...' : 'Descargar reporte PDF' }}
          </button>
        </div>
        <p v-if="errorPdf" class="mensaje error">{{ errorPdf }}</p>

        <dl class="kpi-datos">
          <div><dt>Objetivo</dt><dd>{{ textoObjetivoKpi(kpiSeleccionado) }}</dd></div>
          <div><dt>Frecuencia</dt><dd>{{ kpiSeleccionado.frecuencia_nombre || '-' }}</dd></div>
          <div><dt>Unidad</dt><dd>{{ unidad || '-' }}</dd></div>
          <div><dt>Meta</dt><dd>{{ textoValor(kpiSeleccionado.valor_meta) }}</dd></div>
          <div><dt>Periodos registrados</dt><dd>{{ resumen.periodos }} ({{ resumen.omisiones }} sin registro)</dd></div>
          <div><dt>Evidencias</dt><dd>{{ resumen.evidencias }} archivos</dd></div>
        </dl>
      </section>

      <section class="reporte-card">
        <h3>Evolución del KPI</h3>
        <p v-if="cargandoMediciones" class="mensaje">Cargando historial...</p>
        <GraficaHistoricaKpi v-else :mediciones="medicionesOrdenadas" :unidad="unidad" />
      </section>

      <section class="reporte-card">
        <h3>Mediciones por periodo</h3>

        <p v-if="!cargandoMediciones && !medicionesOrdenadas.length" class="mensaje">
          Este KPI todavía no tiene mediciones.
        </p>

        <div v-else-if="!cargandoMediciones" class="tabla-scroll">
          <table class="tabla-historial">
            <thead>
              <tr>
                <th>Periodo</th>
                <th>Resultado</th>
                <th>Meta</th>
                <th>Estado</th>
                <th>Fecha de registro</th>
                <th>Evidencias</th>
                <th><span class="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="medicion in medicionesOrdenadas" :key="medicion.id">
                <td class="celda-periodo">{{ medicion.periodo_nombre }}</td>
                <td :class="{ 'sin-registro': esMedicionSinRegistro(medicion) }">
                  {{ esMedicionSinRegistro(medicion) ? SIN_REGISTRO : textoValor(medicion.valor_resultado) }}
                </td>
                <td>{{ textoValor(medicion.valor_meta) }}</td>
                <td>
                  <span class="badge" :class="claseColorCumplimiento(medicion.estado_cumplimiento_color)">
                    <span class="badge-dot"></span>
                    {{ textoEstadoCumplimiento(medicion.estado_cumplimiento_nombre) }}
                  </span>
                </td>
                <td>{{ medicion.cierre_automatico ? 'Cierre automático' : textoFecha(medicion.fecha_registro) }}</td>
                <td>{{ medicion.cantidad_evidencias || 0 }}</td>
                <td>
                  <button class="btn-detalle" type="button" @click="medicionDetalle = medicion">Ver detalle</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <ModalBase
      :abierto="Boolean(medicionDetalle)"
      titulo="Detalle de la medición"
      :subtitulo="medicionDetalle ? `${medicionDetalle.indicador_nombre} · ${medicionDetalle.periodo_nombre}` : ''"
      @cerrar="medicionDetalle = null"
    >
      <MedicionDetalle v-if="medicionDetalle" :medicion="medicionDetalle" />
    </ModalBase>
  </AppLayout>
</template>

<style scoped>
.reporte-card {
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 16px;
  box-shadow: 0 2px 10px rgba(29, 53, 87, 0.05);
  padding: 18px 20px;
  margin-bottom: 16px;
}

.reporte-card h3 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 800;
  color: #1d3557;
}

.filtros {
  display: grid;
  grid-template-columns: repeat(2, minmax(160px, 1fr)) minmax(220px, 2fr);
  gap: 12px;
}

.filtro {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.filtro > span {
  font-size: 11.5px;
  font-weight: 800;
  color: #5e6e82;
}

.filtro-historico {
  grid-column: 1 / -1;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 700;
  color: #5e6e82;
  cursor: pointer;
}

.mensaje {
  margin: 0 0 16px;
  color: #5e6e82;
  font-size: 13px;
  font-weight: 600;
}

.mensaje.error {
  color: #e76f51;
}

.kpi-encabezado {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.kpi-encabezado h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #1d3557;
}

.kpi-jerarquia {
  margin: 4px 0 0;
  font-size: 12.5px;
  font-weight: 600;
  color: #5e6e82;
}

.btn-pdf,
.btn-detalle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1.5px solid #a8dadc;
  background: #eaf5f5;
  color: #1d3557;
  font-family: inherit;
  font-weight: 800;
  border-radius: 10px;
  cursor: pointer;
}

.btn-pdf {
  font-size: 12.5px;
  padding: 8px 14px;
}

.btn-detalle {
  font-size: 11.5px;
  padding: 5px 10px;
  white-space: nowrap;
}

.btn-pdf:disabled {
  opacity: 0.6;
  cursor: wait;
}

.kpi-datos {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px 18px;
  margin: 16px 0 0;
}

.kpi-datos dt {
  font-size: 11px;
  font-weight: 800;
  color: #5e6e82;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.kpi-datos dd {
  margin: 3px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: #1d3557;
  overflow-wrap: anywhere;
}

.tabla-scroll {
  width: 100%;
  overflow-x: auto;
}

.tabla-historial {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  color: #1d3557;
}

.tabla-historial th {
  text-align: left;
  font-size: 11px;
  font-weight: 800;
  color: #5e6e82;
  padding: 8px 10px;
  border-bottom: 1.5px solid #e4eaef;
  white-space: nowrap;
}

.tabla-historial td {
  padding: 9px 10px;
  border-bottom: 1px solid #edf1f4;
  white-space: nowrap;
}

.celda-periodo {
  font-weight: 700;
}

.sin-registro {
  color: #55657a;
  font-style: italic;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 20px;
}
.badge.ok { background: rgba(42, 157, 143, 0.12); color: #2a9d8f; }
.badge.warning { background: rgba(244, 162, 97, 0.16); color: #b9701e; }
.badge.danger { background: rgba(231, 111, 81, 0.12); color: #e76f51; }
.badge.neutral { background: rgba(154, 168, 184, 0.16); color: #5e6e82; }
.badge-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

@media (max-width: 900px) {
  .filtros { grid-template-columns: 1fr 1fr; }
  .filtro-kpi { grid-column: 1 / -1; }
  .kpi-datos { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .reporte-card { padding: 14px; }
  .filtros { grid-template-columns: 1fr; }
  .kpi-datos { grid-template-columns: 1fr; }
  .btn-pdf { width: 100%; justify-content: center; }
}
</style>
