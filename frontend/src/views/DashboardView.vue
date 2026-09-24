<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import api from '../services/api'
import { formatearNumero } from '../utils/formato'
import {
  claseColorCumplimiento,
  claseCumplimientoAgregado,
  textoCumplimientoAgregado,
  textoEstadoCumplimiento,
} from '../utils/cumplimiento'

const router = useRouter()

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const cargandoDashboard = ref(false)
const errorDashboard = ref('')

const estrategias = ref([])
const objetivos = ref([])
const indicadores = ref([])
const mediciones = ref([])
const alertas = ref([])


const estrategiasActivas = computed(() => {
  return estrategias.value.filter(esEstrategiaActiva).length
})

const objetivosRegistrados = computed(() => objetivos.value.length)

const indicadoresActivos = computed(() => {
  return indicadores.value.filter((item) => item.estado === 'autorizado').length
})

const indicadoresEnRiesgo = computed(() => {
  const mapaUltimaMedicion = obtenerUltimaMedicionPorIndicador()

  return Array.from(mapaUltimaMedicion.values()).filter((medicion) => {
    const color = (medicion.estado_cumplimiento_color || '').toLowerCase().trim()
    return color === 'amarillo' || color === 'rojo'
  }).length
})

const cumplimientoGeneral = computed(() => {
  if (!mediciones.value.length) return 0

  const total = mediciones.value.reduce((acumulado, medicion) => {
    return acumulado + Number(medicion.porcentaje_cumplimiento || 0)
  }, 0)

  return total / mediciones.value.length
})

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

function formatearPorcentaje(valor) {
  return formatearNumero(valor, { decimales: 2, unidad: '%' })
}

function obtenerNombreIndicador(medicion) {
  return medicion?.indicador_nombre || 'Sin KPI'
}

function obtenerIniciales(nombre) {
  if (!nombre) return 'US'

  return nombre
    .split(' ')
    .map((parte) => parte.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

function obtenerFechaOrden(item) {
  return item?.fecha_medicion || item?.fecha_registro || item?.fecha_generacion || item?.fecha_creacion || ''
}

function obtenerUltimaMedicionPorIndicador() {
  const mapa = new Map()

  mediciones.value.forEach((medicion) => {
    const anterior = mapa.get(medicion.indicador)

    if (!anterior || obtenerFechaOrden(medicion) > obtenerFechaOrden(anterior)) {
      mapa.set(medicion.indicador, medicion)
    }
  })

  return mapa
}

function obtenerObjetivoDeIndicador(indicadorId) {
  const indicador = indicadores.value.find((item) => item.id === indicadorId)
  return indicador?.objetivo_nombre || ''
}

function claseAlerta(alerta) {
  const tipo = (alerta.tipo_alerta || '').toLowerCase()

  if (tipo.includes('incumplido') || tipo.includes('crítico') || tipo.includes('critico')) {
    return 'critical'
  }

  if (tipo.includes('riesgo') || tipo.includes('vencido')) {
    return 'warning'
  }

  return 'info'
}

function claseCumplimiento(medicion) {
  return claseColorCumplimiento(medicion?.estado_cumplimiento_color)
}

function colorPorClaseCumplimiento(clase) {
  const mapa = {
    ok: 'var(--success)',
    warning: 'var(--orange)',
    danger: 'var(--danger)',
    neutral: 'var(--text-muted)',
  }

  return mapa[clase] || 'var(--text-muted)'
}

const alertasRecientes = computed(() => {
  return [...alertas.value]
    .sort((a, b) => new Date(obtenerFechaOrden(b)) - new Date(obtenerFechaOrden(a)))
    .slice(0, 5)
})

const ultimasMediciones = computed(() => {
  return [...mediciones.value]
    .sort((a, b) => new Date(obtenerFechaOrden(b)) - new Date(obtenerFechaOrden(a)))
    .slice(0, 5)
})

const indicadoresMenorCumplimiento = computed(() => {
  const mapaUltimaMedicion = obtenerUltimaMedicionPorIndicador()

  return Array.from(mapaUltimaMedicion.values())
    .filter((medicion) => medicion.porcentaje_cumplimiento !== null && medicion.porcentaje_cumplimiento !== undefined)
    .sort((a, b) => Number(a.porcentaje_cumplimiento) - Number(b.porcentaje_cumplimiento))
    .slice(0, 5)
})

// NOTA (Bloque 1 del rediseño, solo compatibilidad): "estrategia.estado"
// ahora es el estado del PlanEstrategico (borrador/en_uso/cerrado), no el
// viejo activa/en_revision/finalizada/inactiva. El equivalente funcional
// de "estrategia activa" que esta tarjeta contaba es un plan En uso — se
// actualiza el valor comparado, sin tocar el resto de la lógica/diseño del
// Dashboard (eso es Bloque 6).
// Misma regla que ya usa la tarjeta "Estrategias activas" del Panel.
function esEstrategiaActiva(estrategia) {
  return estrategia.estado === 'en_uso' || estrategia.estado === true
}

const cumplimientoPorEstrategia = computed(() => {
  const mapaUltimaMedicion = obtenerUltimaMedicionPorIndicador()

  return estrategias.value
    .filter(esEstrategiaActiva)
    .map((estrategia) => {
      const idsObjetivos = objetivos.value
        .filter((objetivo) => Number(objetivo.plan_estrategico) === Number(estrategia.id))
        .map((objetivo) => objetivo.id)

      const porcentajes = indicadores.value
        .filter((indicador) => idsObjetivos.includes(indicador.objetivo))
        .map((indicador) => mapaUltimaMedicion.get(indicador.id))
        .filter(Boolean)
        .map((medicion) => Number(medicion.porcentaje_cumplimiento))
        .filter((valor) => !Number.isNaN(valor))

      if (!porcentajes.length) {
        // Sin mediciones todavía: la estrategia se sigue mostrando, pero
        // nunca como 0.00 % (eso implicaría un resultado real de
        // incumplimiento) ni clasificada en Favorable/En riesgo/Incumplido.
        return {
          id: estrategia.id,
          nombre: estrategia.titulo,
          tieneMediciones: false,
          porcentaje: null,
        }
      }

      const promedio = porcentajes.reduce((acumulado, valor) => acumulado + valor, 0) / porcentajes.length

      return {
        id: estrategia.id,
        nombre: estrategia.titulo,
        tieneMediciones: true,
        porcentaje: promedio,
      }
    })
    .sort((a, b) => {
      if (a.tieneMediciones && b.tieneMediciones) {
        return b.porcentaje - a.porcentaje
      }

      if (a.tieneMediciones !== b.tieneMediciones) {
        return a.tieneMediciones ? -1 : 1
      }

      return a.nombre.localeCompare(b.nombre)
    })
})

// Escala adaptativa compartida por ambas gráficas: mínimo 0–100 %, y si hay
// un valor por encima de 100 % la escala crece en pasos redondos de 25 para
// no cortar el dato ni deformar los demás valores.
function construirEscala(valores) {
  let maximo = 100

  valores.forEach((valor) => {
    if (valor > maximo) maximo = valor
  })

  maximo = Math.ceil(maximo / 25) * 25

  const ticks = []

  for (let valor = 0; valor <= maximo; valor += 25) {
    ticks.push({ valor, pct: (valor / maximo) * 100 })
  }

  return { maximo, ticks }
}

const escalaEstrategias = computed(() => {
  const valores = cumplimientoPorEstrategia.value
    .filter((item) => item.tieneMediciones)
    .map((item) => item.porcentaje)

  return construirEscala(valores)
})

function obtenerClaveMes(fecha) {
  if (!fecha) return null

  return fecha.slice(0, 7)
}

function formatearMesCorto(claveMes) {
  const meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
  const [anio, mes] = claveMes.split('-')

  return `${meses[Number(mes) - 1]} ${anio.slice(2)}`
}

function formatearMesLargo(claveMes) {
  const meses = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
  ]
  const [anio, mes] = claveMes.split('-')

  return `${meses[Number(mes) - 1]} ${anio}`
}

const evolucionMediciones = computed(() => {
  const grupos = new Map()

  mediciones.value.forEach((medicion) => {
    const clave = obtenerClaveMes(medicion.fecha_medicion || medicion.fecha_registro)
    const porcentaje = Number(medicion.porcentaje_cumplimiento)

    if (!clave || Number.isNaN(porcentaje)) return

    if (!grupos.has(clave)) {
      grupos.set(clave, [])
    }

    grupos.get(clave).push(porcentaje)
  })

  return Array.from(grupos.entries())
    .map(([clave, valores]) => ({
      clave,
      etiqueta: formatearMesCorto(clave),
      etiquetaCompleta: formatearMesLargo(clave),
      promedio: valores.reduce((acumulado, valor) => acumulado + valor, 0) / valores.length,
    }))
    .sort((a, b) => a.clave.localeCompare(b.clave))
    // Límite de visualización del Panel: solo los últimos 12 meses, del más
    // antiguo al más reciente. No borra ni modifica mediciones históricas.
    .slice(-12)
})

// Geometría de la gráfica de línea "Evolución de mediciones" (SVG plano,
// sin librería externa). Solo presentación: no toca datos ni cálculos.
// "izquierda" deja margen suficiente para que el área de dibujo (línea,
// puntos) nunca invada el espacio de las etiquetas del eje Y.
const EVOLUCION_ANCHO = 600
const EVOLUCION_ALTO = 220
const EVOLUCION_PAD = { izquierda: 54, derecha: 16, arriba: 22, abajo: 32 }

const escalaEvolucion = computed(() => {
  return construirEscala(evolucionMediciones.value.map((item) => item.promedio))
})

function coordEvolucionX(indice, total) {
  const anchoUtil = EVOLUCION_ANCHO - EVOLUCION_PAD.izquierda - EVOLUCION_PAD.derecha

  if (total <= 1) {
    return EVOLUCION_PAD.izquierda + anchoUtil / 2
  }

  return EVOLUCION_PAD.izquierda + (anchoUtil * indice) / (total - 1)
}

function coordEvolucionY(valor, maximo) {
  const altoUtil = EVOLUCION_ALTO - EVOLUCION_PAD.arriba - EVOLUCION_PAD.abajo
  const proporcion = Math.min(valor / maximo, 1)

  return EVOLUCION_PAD.arriba + altoUtil - proporcion * altoUtil
}

const gridlinesEvolucion = computed(() => {
  const anchoUtil = EVOLUCION_ANCHO - EVOLUCION_PAD.izquierda - EVOLUCION_PAD.derecha

  return escalaEvolucion.value.ticks.map((tick) => ({
    valor: tick.valor,
    y: coordEvolucionY(tick.valor, escalaEvolucion.value.maximo),
    xInicio: EVOLUCION_PAD.izquierda,
    xFin: EVOLUCION_PAD.izquierda + anchoUtil,
  }))
})

const puntosEvolucion = computed(() => {
  const datos = evolucionMediciones.value
  const maximo = escalaEvolucion.value.maximo

  return datos.map((item, indice) => ({
    clave: item.clave,
    etiqueta: item.etiqueta,
    etiquetaCompleta: item.etiquetaCompleta,
    valor: item.promedio,
    x: coordEvolucionX(indice, datos.length),
    y: coordEvolucionY(item.promedio, maximo),
    clase: claseCumplimientoAgregado(item.promedio),
  }))
})

// Tooltip al pasar el cursor sobre un punto (reemplaza el porcentaje
// permanente que antes se superponía con el eje Y y con otros valores).
const puntoActivoEvolucion = ref(null)

const tooltipEvolucionEstilo = computed(() => {
  if (!puntoActivoEvolucion.value) return {}

  return {
    left: `${(puntoActivoEvolucion.value.x / EVOLUCION_ANCHO) * 100}%`,
    top: `${(puntoActivoEvolucion.value.y / EVOLUCION_ALTO) * 100}%`,
  }
})

const lineaEvolucionPath = computed(() => {
  return puntosEvolucion.value
    .map((punto, indice) => `${indice === 0 ? 'M' : 'L'} ${punto.x.toFixed(2)} ${punto.y.toFixed(2)}`)
    .join(' ')
})

function normalizarRespuesta(response) {
  if (Array.isArray(response.data)) {
    return response.data
  }

  if (Array.isArray(response.data.results)) {
    return response.data.results
  }

  return []
}

async function cargarDatosDashboard() {
  cargandoDashboard.value = true
  errorDashboard.value = ''

  try {
    const [
      estrategiasResponse,
      objetivosResponse,
      indicadoresResponse,
      medicionesResponse,
      alertasResponse,
    ] = await Promise.all([
      api.get('planes-estrategicos/'),
      api.get('objetivos-generales/'),
      api.get('indicadores-kpi/'),
      api.get('mediciones/'),
      api.get('alertas/'),
    ])

    estrategias.value = normalizarRespuesta(estrategiasResponse)
    objetivos.value = normalizarRespuesta(objetivosResponse)
    indicadores.value = normalizarRespuesta(indicadoresResponse)
    mediciones.value = normalizarRespuesta(medicionesResponse)
    alertas.value = normalizarRespuesta(alertasResponse)
  } catch (error) {
    errorDashboard.value = 'No se pudieron cargar los datos del panel de control.'
  } finally {
    cargandoDashboard.value = false
  }
}

function cerrarSesion() {
  emit('logout')
}

function irAEstrategia(id) {
  if (!id) return
  router.push({ path: '/planes-estrategicos', query: { resaltar: id } })
}

function irAIndicador(id) {
  if (!id) return
  router.push({ path: '/indicadores', query: { resaltar: id } })
}

function irAMedicion(id) {
  if (!id) return
  router.push({ path: '/mediciones', query: { resaltar: id } })
}

function verTodasAlertas() {
  router.push('/indicadores')
}

function verTodasMediciones() {
  router.push('/mediciones')
}

onMounted(() => {
  cargarDatosDashboard()
})
</script>

<template>
  <AppLayout
    :usuario="usuario"
    titulo="Panel de control"
    subtitulo="Resumen general del cumplimiento estratégico"
    breadcrumb-actual="Panel de control"
    @logout="cerrarSesion"
  >
    <template #actions>
      <div class="period-select">
        <svg class="cal" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        Datos actualizados del sistema
      </div>
    </template>

    <div class="dashboard-content">

      <div v-if="cargandoDashboard" class="dashboard-message">Cargando datos del panel de control...</div>
      <div v-if="errorDashboard" class="dashboard-error">{{ errorDashboard }}</div>

      <!-- ================= SUMMARY CARDS ================= -->
      <section class="summary-grid">

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon navy">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ formatearPorcentaje(cumplimientoGeneral) }}</div>
          <div class="kpi-label">Cumplimiento general</div>
          <div class="progress-track"><div class="progress-fill" :style="{ width: `${cumplimientoGeneral}%` }"></div></div>
          <div class="kpi-foot">Promedio calculado según mediciones registradas</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon steel">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ estrategiasActivas }}</div>
          <div class="kpi-label">Estrategias activas</div>
          <div class="kpi-foot" style="margin-top:22px;">De {{ estrategias.length }} estrategias registradas</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon aqua">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21V4a1 1 0 0 1 1-1h9l4 4v3"/><path d="M4 14h8"/><path d="M4 21h9"/><circle cx="18" cy="16" r="4"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ objetivosRegistrados }}</div>
          <div class="kpi-label">Objetivos registrados</div>
          <div class="kpi-foot" style="margin-top:22px;">Distribuidos en {{ estrategias.length }} estrategias</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon steel">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ indicadoresActivos }}</div>
          <div class="kpi-label">KPI activos</div>
          <div class="kpi-foot" style="margin-top:22px;">En seguimiento este trimestre</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon danger">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ indicadoresEnRiesgo }}</div>
          <div class="kpi-label">Indicadores en riesgo</div>
          <div class="kpi-foot">Requieren atención inmediata</div>
        </div>

      </section>

      <!-- ================= CHARTS ================= -->
      <section class="charts-grid">

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Cumplimiento por estrategia</h2>
              <div class="desc">Promedio de cumplimiento de los indicadores medidos, por estrategia</div>
            </div>
          </div>

          <div v-if="!cumplimientoPorEstrategia.length" class="dashboard-message">
            No hay estrategias activas registradas.
          </div>

          <template v-else>
            <div class="estrategia-chart">
              <div class="estrategia-scale">
                <div></div>
                <div class="estrategia-scale-track">
                  <span
                    v-for="tick in escalaEstrategias.ticks"
                    :key="tick.valor"
                    class="estrategia-scale-tick"
                    :style="{ left: tick.pct + '%' }"
                  >{{ formatearPorcentaje(tick.valor) }}</span>
                </div>
                <div></div>
              </div>

              <div class="estrategia-rows">
                <div
                  v-for="item in cumplimientoPorEstrategia"
                  :key="item.id"
                  class="estrategia-row"
                  :title="item.nombre"
                  @click="irAEstrategia(item.id)"
                >
                  <div class="estrategia-row-name">{{ item.nombre }}</div>

                  <div class="estrategia-row-track">
                    <span
                      v-for="tick in escalaEstrategias.ticks"
                      :key="tick.valor"
                      class="estrategia-grid-line"
                      :style="{ left: tick.pct + '%' }"
                    ></span>

                    <div
                      v-if="item.tieneMediciones"
                      class="estrategia-row-fill"
                      :style="{
                        width: `${(item.porcentaje / escalaEstrategias.maximo) * 100}%`,
                        background: colorPorClaseCumplimiento(claseCumplimientoAgregado(item.porcentaje)),
                      }"
                    ></div>
                    <div v-else class="estrategia-row-fill estrategia-row-fill--vacio"></div>
                  </div>

                  <div class="estrategia-row-value" :class="{ 'estrategia-row-value--vacio': !item.tieneMediciones }">
                    {{ item.tieneMediciones ? formatearPorcentaje(item.porcentaje) : 'Sin mediciones' }}
                  </div>
                </div>
              </div>
            </div>

            <div class="chart-legend">
              <div class="legend-item"><span class="legend-dot" :style="{ background: colorPorClaseCumplimiento('ok') }"></span>Favorable</div>
              <div class="legend-item"><span class="legend-dot" :style="{ background: colorPorClaseCumplimiento('warning') }"></span>En riesgo</div>
              <div class="legend-item"><span class="legend-dot" :style="{ background: colorPorClaseCumplimiento('danger') }"></span>Incumplido</div>
              <div class="legend-item"><span class="legend-dot" :style="{ background: colorPorClaseCumplimiento('neutral') }"></span>Sin mediciones</div>
            </div>
          </template>
        </div>

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Evolución de mediciones</h2>
              <div class="desc">Cumplimiento general promedio, últimos meses con datos</div>
            </div>
          </div>

          <div v-if="!evolucionMediciones.length" class="dashboard-message">
            No hay mediciones suficientes para mostrar una evolución mensual.
          </div>

          <template v-else>
            <div class="evolucion-wrap">
              <svg
                class="evolucion-svg"
                :viewBox="`0 0 ${EVOLUCION_ANCHO} ${EVOLUCION_ALTO}`"
                preserveAspectRatio="none"
                role="img"
                aria-label="Evolución del cumplimiento promedio por periodo"
              >
                <line
                  v-for="linea in gridlinesEvolucion"
                  :key="`grid-${linea.valor}`"
                  :x1="linea.xInicio" :x2="linea.xFin" :y1="linea.y" :y2="linea.y"
                  class="evolucion-gridline"
                />
                <text
                  v-for="linea in gridlinesEvolucion"
                  :key="`label-${linea.valor}`"
                  :x="EVOLUCION_PAD.izquierda - 8" :y="linea.y + 3"
                  class="evolucion-eje-label"
                  text-anchor="end"
                >{{ formatearPorcentaje(linea.valor) }}</text>

                <path :d="lineaEvolucionPath" class="evolucion-linea" fill="none" />

                <g v-for="punto in puntosEvolucion" :key="punto.clave">
                  <circle
                    :cx="punto.x" :cy="punto.y" r="4.5"
                    :fill="colorPorClaseCumplimiento(punto.clase)"
                    class="evolucion-punto"
                  ></circle>

                  <circle
                    :cx="punto.x" :cy="punto.y" r="11"
                    fill="transparent"
                    class="evolucion-punto-hitbox"
                    @mouseenter="puntoActivoEvolucion = punto"
                    @mouseleave="puntoActivoEvolucion = null"
                  ></circle>

                  <text
                    :x="punto.x" :y="EVOLUCION_ALTO - 10"
                    text-anchor="middle"
                    class="evolucion-eje-x-label"
                  >{{ punto.etiqueta }}</text>
                </g>
              </svg>

              <div
                v-if="puntoActivoEvolucion"
                class="evolucion-tooltip"
                :style="tooltipEvolucionEstilo"
              >
                <div class="evolucion-tooltip-fila">
                  <span>Periodo:</span>
                  <strong>{{ puntoActivoEvolucion.etiquetaCompleta }}</strong>
                </div>
                <div class="evolucion-tooltip-fila">
                  <span>Cumplimiento:</span>
                  <strong>{{ formatearPorcentaje(puntoActivoEvolucion.valor) }}</strong>
                </div>
                <div class="evolucion-tooltip-fila">
                  <span>Estado:</span>
                  <strong :class="puntoActivoEvolucion.clase">{{ textoCumplimientoAgregado(puntoActivoEvolucion.valor) }}</strong>
                </div>
              </div>
            </div>

            <div class="chart-legend">
              <div class="legend-item"><span class="legend-dot" :style="{ background: colorPorClaseCumplimiento('ok') }"></span>Favorable</div>
              <div class="legend-item"><span class="legend-dot" :style="{ background: colorPorClaseCumplimiento('warning') }"></span>En riesgo</div>
              <div class="legend-item"><span class="legend-dot" :style="{ background: colorPorClaseCumplimiento('danger') }"></span>Incumplido</div>
            </div>
          </template>

        </div>

      </section>

      <!-- ================= TABLE ================= -->
      <section class="card-panel table-card">
        <div class="panel-head">
          <div>
            <h2>Indicadores con menor cumplimiento</h2>
            <div class="desc">Los 5 KPI que más se alejan de su meta, según su última medición</div>
          </div>
        </div>

        <div v-if="!indicadoresMenorCumplimiento.length" class="dashboard-message">
          Aún no hay mediciones suficientes para calcular cumplimiento.
        </div>

        <table v-else>
          <thead>
            <tr>
              <th>Indicador</th>
              <th>Meta</th>
              <th>Resultado</th>
              <th title="Se calcula comparando el resultado obtenido con la meta establecida.">Cumplimiento</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="medicion in indicadoresMenorCumplimiento"
              :key="medicion.id"
              class="fila-navegable"
              @click="irAIndicador(medicion.indicador)"
            >
              <td>
                <div class="cell-main" :title="obtenerNombreIndicador(medicion)">{{ obtenerNombreIndicador(medicion) }}</div>
                <div class="cell-sub" :title="obtenerObjetivoDeIndicador(medicion.indicador)">{{ obtenerObjetivoDeIndicador(medicion.indicador) || 'Sin objetivo' }}</div>
              </td>
              <td>{{ medicion.valor_meta !== null && medicion.valor_meta !== undefined ? formatearNumero(medicion.valor_meta, { unidad: medicion.unidad_medida }) : 'Sin meta' }}</td>
              <td>{{ formatearNumero(medicion.valor_resultado, { unidad: medicion.unidad_medida }) }}</td>
              <td>
                <div class="mini-progress">
                  <div class="track">
                    <div
                      class="fill"
                      :style="{ width: `${Math.min(Number(medicion.porcentaje_cumplimiento) || 0, 100)}%`, background: colorPorClaseCumplimiento(claseCumplimiento(medicion)) }"
                    ></div>
                  </div>
                  <span class="pct">{{ formatearPorcentaje(medicion.porcentaje_cumplimiento) }}</span>
                </div>
              </td>
              <td>
                <span class="badge" :class="claseCumplimiento(medicion)">
                  <span class="badge-dot"></span>
                  {{ textoEstadoCumplimiento(medicion.estado_cumplimiento_nombre) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ================= BOTTOM: ALERTS + MEASUREMENTS ================= -->
      <section class="bottom-grid">

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Alertas recientes</h2>
              <div class="desc">Eventos que requieren revisión</div>
            </div>
          </div>

          <div v-if="!alertasRecientes.length" class="dashboard-message">
            No hay alertas pendientes o recientes.
          </div>

          <template v-else>
            <div
              v-for="alerta in alertasRecientes"
              :key="alerta.id"
              class="alert-item fila-navegable"
              @click="irAIndicador(alerta.indicador)"
            >
              <div class="alert-icon" :class="claseAlerta(alerta)">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </div>
              <div>
                <div class="alert-text">{{ alerta.mensaje }}</div>
                <div class="alert-time">{{ formatearFecha(alerta.fecha_generacion) }}</div>
              </div>
            </div>
          </template>

          <div class="link-see-all" @click="verTodasAlertas">Ver todas las alertas</div>
        </div>

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Últimas mediciones registradas</h2>
              <div class="desc">Cargas más recientes al sistema</div>
            </div>
          </div>

          <div v-if="!ultimasMediciones.length" class="dashboard-message">
            No hay mediciones registradas.
          </div>

          <template v-else>
            <div
              v-for="medicion in ultimasMediciones"
              :key="medicion.id"
              class="meas-item fila-navegable"
              @click="irAMedicion(medicion.id)"
            >
              <div class="meas-left">
                <div class="meas-avatar">{{ obtenerIniciales(medicion.registrado_por_username) }}</div>
                <div>
                  <div class="meas-name" :title="obtenerNombreIndicador(medicion)">{{ obtenerNombreIndicador(medicion) }}</div>
                  <div class="meas-sub">{{ medicion.registrado_por_username || 'Sistema' }} · {{ formatearFecha(medicion.fecha_registro) }}</div>
                </div>
              </div>
              <div class="meas-value">{{ formatearNumero(medicion.valor_resultado, { unidad: medicion.unidad_medida }) }}</div>
            </div>
          </template>

          <div class="link-see-all" @click="verTodasMediciones">Ver todas las mediciones</div>
        </div>

      </section>

    
    </div>
  </AppLayout>
</template>

<style scoped>
  .dashboard-content{
    --navy:#1D3557;
    --navy-dark:#152840;
    --steel:#457B9D;
    --aqua:#A8DADC;
    --aqua-soft:#EAF5F5;
    --orange:#F4A261;
    --success:#2A9D8F;
    --danger:#E76F51;
    --bg:#F6F9FA;
    --white:#FFFFFF;
    --text-secondary:#5E6E82;
    --text-muted:#9AA8B8;
    --border:#E4EAEF;
    --radius-lg:20px;
    --radius-md:14px;
    --radius-sm:10px;
    --shadow-card: 0 2px 10px rgba(29,53,87,0.05), 0 1px 2px rgba(29,53,87,0.04);
    --shadow-hover: 0 10px 26px rgba(29,53,87,0.10);
    --sidebar-w:264px;
  }
  .dashboard-content *{ box-sizing:border-box; margin:0; padding:0; }
  .dashboard-content{
    font-family:'Montserrat', sans-serif;
    background:var(--bg);
    color:var(--navy);
    -webkit-font-smoothing:antialiased;
  }
  .dashboard-content a{ color:inherit; text-decoration:none; }
  .dashboard-content button{ font-family:inherit; }

  /* ===================== SIDEBAR ===================== */
  .sidebar{
    position:fixed;
    top:0; left:0; bottom:0;
    width:var(--sidebar-w);
    background:var(--white);
    border-right:1px solid var(--border);
    display:flex;
    flex-direction:column;
    z-index:20;
  }

  .sidebar-brand{
    display:flex;
    align-items:center;
    gap:11px;
    padding:22px 22px 20px;
    border-bottom:1px solid var(--border);
  }
  .sidebar-brand img{
    width:38px; height:38px; border-radius:10px; display:block;
  }
  .sidebar-brand .wordmark{
    font-weight:800;
    font-size:19px;
    letter-spacing:-0.4px;
    color:var(--navy);
  }
  .sidebar-brand .wordmark span{ color:var(--steel); }

  .nav-section{
    padding:18px 14px;
    flex:1;
    overflow-y:auto;
  }
  .nav-label{
    font-size:10.5px;
    font-weight:700;
    letter-spacing:1.2px;
    text-transform:uppercase;
    color:var(--text-muted);
    padding:6px 12px 10px;
  }
  .nav-item{
    display:flex;
    align-items:center;
    gap:11px;
    padding:10px 12px;
    border-radius:var(--radius-sm);
    font-size:13.5px;
    font-weight:600;
    color:var(--text-secondary);
    margin-bottom:2px;
    cursor:pointer;
    transition:background .15s ease, color .15s ease;
  }
  .nav-item svg{ flex-shrink:0; opacity:0.85; }
  .nav-item:hover{ background:#F4F8F9; color:var(--navy); }
  .nav-item.active{
    background:var(--navy);
    color:var(--white);
  }
  .nav-item.active svg{ opacity:1; }

  .sidebar-user{
    display:flex;
    align-items:center;
    gap:10px;
    padding:16px 20px;
    border-top:1px solid var(--border);
  }
  .avatar-sm{
    width:36px; height:36px; border-radius:10px;
    background:var(--aqua-soft);
    color:var(--steel);
    display:flex; align-items:center; justify-content:center;
    font-weight:700; font-size:13px;
    flex-shrink:0;
  }
  .sidebar-user .name{ font-size:13px; font-weight:700; color:var(--navy); line-height:1.3; }
  .sidebar-user .role{ font-size:11px; color:var(--text-muted); font-weight:500; }

  /* ===================== MAIN AREA ===================== */
  .main-area{
    margin-left:var(--sidebar-w);
    min-height:100vh;
    display:flex;
    flex-direction:column;
  }

  /* ---- topbar ---- */
  .topbar{
    position:sticky;
    top:0;
    z-index:10;
    height:66px;
    background:var(--white);
    border-bottom:1px solid var(--border);
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:0 28px;
    gap:20px;
  }
  .breadcrumb{
    font-size:13px;
    font-weight:600;
    color:var(--text-muted);
    display:flex;
    align-items:center;
    gap:6px;
    white-space:nowrap;
  }
  .breadcrumb .current{ color:var(--navy); }

  .topbar-search{
    flex:1;
    max-width:380px;
    position:relative;
  }
  .topbar-search svg{
    position:absolute; left:13px; top:50%; transform:translateY(-50%);
    color:var(--text-muted);
  }
  .topbar-search input{
    width:100%;
    height:38px;
    border-radius:10px;
    border:1.5px solid var(--border);
    background:var(--bg);
    padding:0 14px 0 38px;
    font-family:inherit;
    font-size:13px;
    color:var(--navy);
    outline:none;
    transition:border-color .15s ease, background .15s ease;
  }
  .topbar-search input::placeholder{ color:var(--text-muted); }
  .topbar-search input:focus{ border-color:var(--steel); background:var(--white); }

  .topbar-actions{
    display:flex;
    align-items:center;
    gap:14px;
    flex-shrink:0;
  }
  .icon-btn{
    width:38px; height:38px;
    border-radius:10px;
    border:1.5px solid var(--border);
    background:var(--white);
    display:flex; align-items:center; justify-content:center;
    color:var(--text-secondary);
    cursor:pointer;
    position:relative;
    transition:background .15s ease, border-color .15s ease;
  }
  .icon-btn:hover{ background:var(--bg); border-color:var(--steel); color:var(--steel); }
  .icon-btn .dot{
    position:absolute; top:8px; right:8px;
    width:7px; height:7px; border-radius:50%;
    background:var(--orange);
    border:1.5px solid var(--white);
  }
  .topbar-profile{
    display:flex; align-items:center; gap:9px;
    padding:5px 6px 5px 5px;
    border-radius:10px;
    cursor:pointer;
    transition:background .15s ease;
  }
  .topbar-profile:hover{ background:var(--bg); }
  .topbar-profile .chev{ color:var(--text-muted); }

  /* ---- content ---- */
  .content{
    padding:28px 32px 40px;
    max-width:1400px;
    width:100%;
  }

  .page-header{
    display:flex;
    align-items:flex-end;
    justify-content:space-between;
    flex-wrap:wrap;
    gap:16px;
    margin-bottom:24px;
  }
  .page-header h1{
    font-size:23px;
    font-weight:800;
    letter-spacing:-0.3px;
    color:var(--navy);
  }
  .page-header .subtitle{
    font-size:13px;
    color:var(--text-muted);
    font-weight:500;
    margin-top:4px;
  }

  .period-select{
    display:flex;
    align-items:center;
    gap:8px;
    height:40px;
    padding:0 14px;
    border-radius:10px;
    border:1.5px solid var(--border);
    background:var(--white);
    font-size:13px;
    font-weight:600;
    color:var(--navy);
    cursor:default;
    box-shadow:var(--shadow-card);
  }
  .period-select svg.cal{ color:var(--steel); }

  /* ---- summary cards ---- */
  .summary-grid{
    display:grid;
    grid-template-columns:repeat(5, 1fr);
    gap:16px;
    margin-bottom:24px;
  }
  .kpi-card{
    background:var(--white);
    border:1px solid var(--border);
    border-radius:var(--radius-md);
    padding:18px 18px 16px;
    box-shadow:var(--shadow-card);
    transition:box-shadow .15s ease, transform .15s ease;
  }
  .kpi-card:hover{ box-shadow:var(--shadow-hover); transform:translateY(-2px); }

  .kpi-top{
    display:flex;
    align-items:center;
    justify-content:space-between;
    margin-bottom:14px;
  }
  .kpi-icon{
    width:34px; height:34px;
    border-radius:9px;
    display:flex; align-items:center; justify-content:center;
  }
  .kpi-icon.navy{ background:rgba(29,53,87,0.08); color:var(--navy); }
  .kpi-icon.steel{ background:rgba(69,123,157,0.10); color:var(--steel); }
  .kpi-icon.aqua{ background:var(--aqua-soft); color:var(--steel); }
  .kpi-icon.orange{ background:rgba(244,162,97,0.14); color:var(--orange); }
  .kpi-icon.danger{ background:rgba(231,111,81,0.12); color:var(--danger); }

  .kpi-value{
    font-size:26px;
    font-weight:800;
    color:var(--navy);
    letter-spacing:-0.4px;
    line-height:1;
    margin-bottom:6px;
  }
  .kpi-label{
    font-size:12.5px;
    font-weight:600;
    color:var(--text-secondary);
    margin-bottom:12px;
  }

  .progress-track{
    width:100%; height:6px;
    background:#EEF2F5;
    border-radius:6px;
    overflow:hidden;
  }
  .progress-fill{
    height:100%;
    border-radius:6px;
    background:linear-gradient(90deg, var(--steel), var(--navy));
  }
  .kpi-foot{
    font-size:11px;
    color:var(--text-muted);
    font-weight:500;
    margin-top:8px;
  }

  /* ---- section titles ---- */
  .card-panel{
    background:var(--white);
    border:1px solid var(--border);
    border-radius:var(--radius-md);
    box-shadow:var(--shadow-card);
    padding:20px 22px 22px;
  }
  .panel-head{
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    margin-bottom:18px;
    gap:12px;
  }
  .panel-head h2{
    font-size:14.5px;
    font-weight:700;
    color:var(--navy);
  }
  .panel-head .desc{
    font-size:11.5px;
    color:var(--text-muted);
    font-weight:500;
    margin-top:3px;
  }
  /* ---- charts row ---- */
  .charts-grid{
    display:grid;
    grid-template-columns:1.3fr 1fr;
    gap:18px;
    margin-bottom:20px;
    align-items:stretch;
  }

  /* ---- Cumplimiento por estrategia (barras horizontales) ---- */
  .estrategia-chart{ display:flex; flex-direction:column; gap:6px; }

  .estrategia-scale{ display:grid; grid-template-columns:150px 1fr 90px; gap:10px; }
  .estrategia-scale-track{ position:relative; height:16px; }
  .estrategia-scale-tick{
    position:absolute; top:0; transform:translateX(-50%);
    font-size:10px; font-weight:700; color:var(--text-muted); white-space:nowrap;
  }
  .estrategia-scale-tick:first-child{ transform:translateX(0); }
  .estrategia-scale-tick:last-child{ transform:translateX(-100%); }

  /* Máximo 10 filas visibles a la vez (10 * 26px + 9 * 10px de espacio =
     350px); si hay más, el contenedor scrollea en vez de crecer, y con 10
     o menos no aparece scroll porque todo cabe exacto. */
  .estrategia-rows{ display:flex; flex-direction:column; gap:10px; max-height:350px; overflow-y:auto; padding-right:4px; }

  .estrategia-row{ display:grid; grid-template-columns:150px 1fr 90px; align-items:center; gap:10px; height:26px; cursor:pointer; }
  .estrategia-row-name{
    font-size:11.5px; font-weight:700; color:var(--navy);
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  }

  .estrategia-row-track{ position:relative; height:16px; border-radius:8px; background:var(--bg); overflow:hidden; }
  .estrategia-grid-line{ position:absolute; top:0; bottom:0; width:1px; background:var(--border); }
  .estrategia-row-fill{ position:relative; height:100%; border-radius:8px; transition:width .2s ease; }
  .estrategia-row-fill--vacio{
    width:100%;
    background:repeating-linear-gradient(45deg, var(--border), var(--border) 4px, transparent 4px, transparent 8px);
  }

  .estrategia-row-value{ font-size:10.5px; font-weight:800; color:var(--navy); text-align:right; }
  .estrategia-row-value--vacio{ color:var(--text-muted); font-weight:700; font-size:10px; }

  /* ---- Evolución de mediciones (línea SVG) ---- */
  .evolucion-wrap{ position:relative; }
  .evolucion-svg{ width:100%; height:220px; display:block; }
  .evolucion-gridline{ stroke:var(--border); stroke-width:1; }
  .evolucion-eje-label, .evolucion-eje-x-label{
    font-family:'Montserrat', sans-serif; font-size:9.5px; font-weight:600; fill:var(--text-muted);
  }
  .evolucion-linea{ stroke:var(--steel); stroke-width:2; }
  .evolucion-punto{ stroke:var(--white); stroke-width:2; pointer-events:none; }
  .evolucion-punto-hitbox{ cursor:pointer; }

  .evolucion-tooltip{
    position:absolute;
    transform:translate(-50%, -100%) translateY(-14px);
    min-width:150px;
    background:var(--navy);
    color:var(--white);
    border-radius:10px;
    padding:10px 12px;
    box-shadow:0 10px 24px rgba(29,53,87,0.28);
    pointer-events:none;
    z-index:5;
  }
  .evolucion-tooltip-fila{
    display:flex; align-items:center; justify-content:space-between; gap:12px;
    font-size:11px; font-weight:600;
  }
  .evolucion-tooltip-fila + .evolucion-tooltip-fila{ margin-top:4px; }
  .evolucion-tooltip-fila span{ color:rgba(255,255,255,0.65); }
  .evolucion-tooltip-fila strong{ font-weight:800; }
  .evolucion-tooltip-fila strong.ok{ color:#7fd9c9; }
  .evolucion-tooltip-fila strong.warning{ color:#ffc98a; }
  .evolucion-tooltip-fila strong.danger{ color:#ff9d85; }

  .chart-legend{ display:flex; gap:16px; flex-wrap:wrap; margin-top:16px; padding-top:14px; border-top:1px solid var(--border); }
  .legend-item{ display:flex; align-items:center; gap:6px; font-size:11px; font-weight:700; color:var(--text-secondary); }
  .legend-dot{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }

  /* ---- table ---- */
  .table-card{ margin-bottom:20px; }
  table{ width:100%; border-collapse:collapse; }
  thead th{
    text-align:left;
    font-size:10.5px;
    font-weight:700;
    letter-spacing:0.5px;
    text-transform:uppercase;
    color:var(--text-muted);
    padding:0 12px 10px;
    border-bottom:1px solid var(--border);
  }
  tbody td{
    padding:13px 12px;
    font-size:13px;
    color:var(--navy);
    border-bottom:1px solid #F1F4F7;
    vertical-align:middle;
  }
  tbody tr:last-child td{ border-bottom:none; }
  tbody tr{ transition:background .12s ease; }
  tbody tr:hover{ background:#FAFCFD; }
  tbody tr.fila-navegable{ cursor:pointer; }

  .cell-main{ font-weight:700; font-size:13px; color:var(--navy); max-width:220px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .cell-sub{ font-size:11.5px; color:var(--text-muted); font-weight:500; margin-top:2px; max-width:220px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

  .badge{
    display:inline-flex;
    align-items:center;
    gap:5px;
    font-size:11px;
    font-weight:700;
    padding:4px 10px;
    border-radius:20px;
    white-space:nowrap;
  }
  .badge.critical, .badge.danger{ background:rgba(231,111,81,0.12); color:var(--danger); }
  .badge.warning{ background:rgba(244,162,97,0.16); color:#B9701E; }
  .badge.ok{ background:rgba(42,157,143,0.12); color:var(--success); }
  .badge.neutral{ background:rgba(154,168,184,0.16); color:var(--text-muted); }
  .badge-dot{ width:6px; height:6px; border-radius:50%; background:currentColor; }

  .mini-progress{ display:flex; align-items:center; gap:8px; }
  .mini-progress .track{ width:80px; height:6px; background:#EEF2F5; border-radius:6px; overflow:hidden; }
  .mini-progress .fill{ height:100%; border-radius:6px; }
  .mini-progress .pct{ font-size:12px; font-weight:700; color:var(--navy); width:34px; }

  /* ---- bottom grid ---- */
  .bottom-grid{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:18px;
  }

  .alert-item{
    display:flex;
    gap:12px;
    padding:12px 4px;
    border-bottom:1px solid #F1F4F7;
  }
  .alert-item:last-child{ border-bottom:none; padding-bottom:0; }
  .alert-item.fila-navegable, .meas-item.fila-navegable{ cursor:pointer; }
  .alert-icon{
    width:32px; height:32px; border-radius:9px;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0;
  }
  .alert-icon.critical{ background:rgba(231,111,81,0.12); color:var(--danger); }
  .alert-icon.warning{ background:rgba(244,162,97,0.16); color:#B9701E; }
  .alert-icon.info{ background:rgba(69,123,157,0.10); color:var(--steel); }
  .alert-text{ font-size:12.5px; font-weight:600; color:var(--navy); line-height:1.4; }
  .alert-time{ font-size:11px; color:var(--text-muted); font-weight:500; margin-top:3px; }

  .meas-item{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    padding:12px 4px;
    border-bottom:1px solid #F1F4F7;
  }
  .meas-item:last-child{ border-bottom:none; padding-bottom:0; }
  .meas-left{ display:flex; align-items:center; gap:11px; min-width:0; }
  .meas-avatar{
    width:30px; height:30px; border-radius:9px;
    background:var(--aqua-soft); color:var(--steel);
    display:flex; align-items:center; justify-content:center;
    font-size:11px; font-weight:700; flex-shrink:0;
  }
  .meas-name{ font-size:12.5px; font-weight:700; color:var(--navy); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .meas-sub{ font-size:11px; color:var(--text-muted); font-weight:500; margin-top:1px; }
  .meas-value{ font-size:13px; font-weight:800; color:var(--navy); white-space:nowrap; }

  .link-see-all{
    display:block;
    text-align:center;
    font-size:12px;
    font-weight:700;
    color:var(--steel);
    padding-top:14px;
    cursor:pointer;
  }
  .link-see-all:hover{ color:var(--navy); }

.dashboard-message,
.dashboard-error {
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
}

.dashboard-message {
  background: var(--aqua-soft);
  color: var(--steel);
}

.dashboard-error {
  background: rgba(231, 111, 81, 0.12);
  color: var(--danger);
}

  /* ===================== RESPONSIVE ===================== */
  @media (max-width:1180px){
    .summary-grid{ grid-template-columns:repeat(3, 1fr); }
    .charts-grid{ grid-template-columns:1fr; }
  }
  @media (max-width:900px){
    .summary-grid{ grid-template-columns:repeat(2, 1fr); }
    .bottom-grid{ grid-template-columns:1fr; }
    .topbar-search{ display:none; }
  }
  @media (max-width:760px){
    .dashboard-content{ --sidebar-w:76px; }
    .sidebar-brand .wordmark, .nav-label, .nav-item span, .sidebar-user .name, .sidebar-user .role{ display:none; }
    .sidebar-brand{ justify-content:center; padding:20px 0; }
    .nav-item{ justify-content:center; }
    .sidebar-user{ justify-content:center; }
    .summary-grid{ grid-template-columns:repeat(2, 1fr); }
    .content{ padding:20px 16px 32px; }
    .estrategia-scale, .estrategia-row{ grid-template-columns:88px 1fr 64px; gap:6px; }
    .estrategia-row-name{ font-size:10.5px; }
    .estrategia-row-value{ font-size:9.5px; }
  }


  .topbar-profile {
    border: none;
    background: transparent;
    font-family: inherit;
  }

</style>
