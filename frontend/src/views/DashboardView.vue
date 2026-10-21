<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import { obtenerIndicadoresKpi, obtenerEstadosCumplimiento } from '../services/indicadorService'
import { obtenerMediciones } from '../services/medicionService'
import { obtenerPlanesEstrategicos } from '../services/planEstrategicoService'
import { obtenerPlanesAnuales } from '../services/planAnualService'
import { formatearNumero } from '../utils/formato'
import {
  aniosDisponibles,
  descripcionContexto,
  filtrarContexto,
  normalizarSeleccion,
  planesAnualesDe,
} from '../utils/dashboardFiltros'
import {
  alturaConteo,
  codigoKpi,
  ejeConteo,
  ejeEscala,
  etiquetasDona,
  evidenciasPorKpi,
  gruposCumplimiento,
  nombreCorto,
  paginar,
  porcentajeDe,
  resumenEvidencias,
  resumenOportunidad,
  resumenTarjetas,
} from '../utils/dashboardBloques'
import { textoObjetivoKpi } from '../utils/objetivos'
import {
  SIN_REGISTRO,
  categoriaKpi,
  claseColorCumplimiento,
  textoEstadoCumplimiento,
  textoOmisiones,
} from '../utils/cumplimiento'

// Dashboard de la entrega, según la referencia visual aprobada por Hernán:
// año del plan anual arriba a la derecha, cinco tarjetas resumen y cinco
// bloques (Cumplimiento de KPI, Estado actual de KPI, KPI con evidencias,
// Oportunidad de registro y Detalle de indicadores KPI). Solo presenta lo
// que ya calcula el backend: no cambia fórmulas, rangos ni clasificaciones.

const router = useRouter()
const route = useRoute()

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const cargando = ref(false)
const error = ref('')

const todosPlanesEstrategicos = ref([])
const todosPlanesAnuales = ref([])
const todosIndicadores = ref([])
const todasMediciones = ref([])
const estadosCumplimientoCatalogo = ref([])

// ============================================================
// Contexto: año, plan estratégico y plan anual (en la URL). Las tarjetas y
// los cinco bloques parten siempre del mismo conjunto filtrado.
// ============================================================

const seleccion = computed(() => normalizarSeleccion(
  { planEstrategico: route.query.plan, planAnual: route.query.anual, anio: route.query.anio },
  todosPlanesEstrategicos.value,
  todosPlanesAnuales.value,
))

const contexto = computed(() => filtrarContexto({
  planesEstrategicos: todosPlanesEstrategicos.value,
  planesAnuales: todosPlanesAnuales.value,
  indicadores: todosIndicadores.value,
  mediciones: todasMediciones.value,
  alertas: [],
}, seleccion.value))

const anios = computed(() => aniosDisponibles(todosPlanesAnuales.value))
const opcionesPlanAnual = computed(() => planesAnualesDe(
  todosPlanesAnuales.value, seleccion.value.planEstrategico, seleccion.value.anio,
))
const hayFiltroPlanes = computed(() => Boolean(seleccion.value.planEstrategico || seleccion.value.planAnual))
const hayFiltro = computed(() => hayFiltroPlanes.value || Boolean(seleccion.value.anio))
const textoContexto = computed(() => descripcionContexto(
  seleccion.value, todosPlanesEstrategicos.value, todosPlanesAnuales.value,
))
const sufijoVacio = computed(() => (hayFiltro.value ? ' para los filtros seleccionados' : ''))

function cambiarFiltro({ planEstrategico = null, planAnual = null, anio = null }) {
  const normalizada = normalizarSeleccion({ planEstrategico, planAnual, anio }, todosPlanesEstrategicos.value, todosPlanesAnuales.value)
  const query = {}

  if (normalizada.anio) query.anio = String(normalizada.anio)
  if (normalizada.planEstrategico) query.plan = String(normalizada.planEstrategico)
  if (normalizada.planAnual) query.anual = String(normalizada.planAnual)

  router.replace({ path: '/dashboard', query })
}

// Cambiar el año descarta un plan anual de otro año; el plan estratégico se
// conserva (puede tener un plan anual en el año nuevo).
function seleccionarAnio(valor) {
  cambiarFiltro({ anio: valor, planEstrategico: seleccion.value.planEstrategico })
}

function seleccionarPlanEstrategico(valor) {
  cambiarFiltro({ anio: seleccion.value.anio, planEstrategico: valor })
}

function seleccionarPlanAnual(valor) {
  cambiarFiltro({ anio: seleccion.value.anio, planEstrategico: seleccion.value.planEstrategico, planAnual: valor })
}

function limpiarFiltro() {
  cambiarFiltro({})
}

async function cargarDatosDashboard() {
  cargando.value = true
  error.value = ''

  try {
    const [planesEstrategicosData, planesAnualesData, indicadoresData, medicionesData, estadosData] = await Promise.all([
      obtenerPlanesEstrategicos(),
      obtenerPlanesAnuales(),
      obtenerIndicadoresKpi(),
      obtenerMediciones(),
      obtenerEstadosCumplimiento(),
    ])

    todosPlanesEstrategicos.value = planesEstrategicosData
    todosPlanesAnuales.value = planesAnualesData
    todosIndicadores.value = indicadoresData
    todasMediciones.value = medicionesData
    estadosCumplimientoCatalogo.value = estadosData
  } catch (e) {
    error.value = 'No se pudieron cargar los datos del panel de control.'
  } finally {
    cargando.value = false
  }
}

// Borrador y anulado nunca representan un KPI en seguimiento.
const indicadoresAutorizados = computed(() => {
  return contexto.value.indicadores.filter((kpi) => kpi.estado === 'autorizado')
})

const medicionesAutorizadas = computed(() => {
  const ids = new Set(indicadoresAutorizados.value.map((kpi) => kpi.id))
  return contexto.value.mediciones.filter((medicion) => ids.has(medicion.indicador) && medicion.fecha_medicion)
})

// ============================================================
// Tarjetas resumen
// ============================================================

// Conteos en utils/dashboardBloques.js (resumenTarjetas), sobre el contexto.
const tarjetas = computed(() => {
  const resumen = resumenTarjetas(contexto.value.planesEstrategicos, contexto.value.planesAnuales, indicadoresAutorizados.value)

  return [
    { clave: 'planes', icono: 'capas', clase: 'navy', valor: resumen.planesEnUso, titulo: 'Planes estratégicos en uso', detalle: `De ${resumen.planesRegistrados} planes registrados` },
    { clave: 'anuales', icono: 'calendario', clase: 'steel', valor: resumen.anualesEnUso, titulo: 'Planes anuales en ejecución', detalle: `De ${resumen.anualesRegistrados} planes anuales registrados` },
    { clave: 'kpi', icono: 'pulso', clase: 'aqua', valor: resumen.kpiAutorizados, titulo: 'KPI autorizados', detalle: 'En seguimiento activo' },
    { clave: 'favorables', icono: 'check', clase: 'ok', valor: resumen.kpiFavorables, titulo: 'KPI favorables', detalle: 'Según su promedio acumulado' },
    { clave: 'atencion', icono: 'alerta', clase: 'danger', valor: resumen.kpiAtencion, titulo: 'Requieren atención', detalle: 'En riesgo o incumplidos' },
  ]
})

// ============================================================
// Colores: del catálogo real EstadoCumplimiento (fuente única).
// ============================================================

const coloresPorNombreEstado = computed(() => {
  const mapa = new Map()

  estadosCumplimientoCatalogo.value.forEach((estado) => {
    if (estado.nombre && estado.color) mapa.set(estado.nombre, estado.color)
  })

  return mapa
})

function claseEstadoNombre(nombre) {
  if (!nombre || nombre === 'Sin mediciones') return 'neutral'
  if (nombre === SIN_REGISTRO) return 'omision'

  return claseColorCumplimiento(coloresPorNombreEstado.value.get(nombre))
}

const CATEGORIAS_ESTADO = ['Favorable', 'En riesgo', 'Incumplido', 'Pendiente de actualización', SIN_REGISTRO, 'Sin mediciones']

function formatearValorUnidad(valor, unidad) {
  if (valor === null || valor === undefined) return 'Sin mediciones'
  return formatearNumero(valor, { unidad: unidad || '' })
}

// Promedio acumulado real del backend, con la unidad propia del KPI.
function textoPromedioKpi(kpi) {
  if (!kpi.cantidad_mediciones && kpi.cantidad_omisiones) return SIN_REGISTRO
  return formatearValorUnidad(kpi.promedio_acumulado, kpi.unidad_medida)
}

// ============================================================
// 1) Cumplimiento de KPI — una unidad por vista, 6 KPI por página
// ============================================================

// Dentro de una unidad la altura es proporcional al valor real y la línea
// punteada marca la meta. Unidades distintas nunca comparten escala: se
// elige la unidad con el selector. El color es el estado del backend.
const KPI_POR_VISTA = 6
const unidadElegida = ref('')
const paginaCumplimiento = ref(1)

const gruposCumplimientoKpi = computed(() => gruposCumplimiento(indicadoresAutorizados.value))

const grupoVisible = computed(() => {
  const grupos = gruposCumplimientoKpi.value
  return grupos.find((grupo) => grupo.unidad === unidadElegida.value) || grupos[0] || null
})

const vistaCumplimiento = computed(() => {
  const grupo = grupoVisible.value

  if (!grupo) return null

  const pagina = paginar(grupo.barras, paginaCumplimiento.value, KPI_POR_VISTA)

  return {
    ...pagina,
    unidad: grupo.unidad,
    marcas: ejeEscala(grupo.escala).map((valor) => ({
      valor,
      texto: formatearNumero(valor, { unidad: '' }),
      altura: grupo.escala ? (valor / grupo.escala) * 100 : 0,
    })),
    barras: pagina.elementos.map((barra) => {
      const categoria = categoriaKpi(barra.kpi)
      const valorTexto = textoPromedioKpi(barra.kpi)
      const metaTexto = formatearValorUnidad(barra.kpi.valor_meta, barra.kpi.unidad_medida)

      return {
        ...barra,
        categoria,
        clase: claseEstadoNombre(categoria),
        valorTexto,
        nombre: nombreCorto(barra.kpi.nombre),
        sinDato: barra.valor === null,
        tieneOmisiones: Boolean(barra.kpi.cantidad_mediciones && barra.kpi.cantidad_omisiones),
        tooltip: [
          `${barra.codigo} · ${barra.kpi.nombre}`,
          `Estado: ${categoria}`,
          `Promedio acumulado: ${valorTexto}`,
          `Meta: ${metaTexto}`,
          textoOmisiones(barra.kpi.cantidad_omisiones),
        ].filter(Boolean).join('\n'),
      }
    }),
  }
})

function elegirUnidad(unidad) {
  unidadElegida.value = unidad
  paginaCumplimiento.value = 1
}

// ============================================================
// 2) Estado actual de KPI — dona
// ============================================================

const COLOR_HEX_POR_CLASE = {
  ok: 'var(--success)',
  warning: 'var(--orange)',
  danger: 'var(--danger)',
  neutral: '#C7D0D9',
  omision: '#8D99AE',
}

const distribucionEstadoActual = computed(() => {
  const conteos = Object.fromEntries(CATEGORIAS_ESTADO.map((categoria) => [categoria, 0]))
  indicadoresAutorizados.value.forEach((kpi) => { conteos[categoriaKpi(kpi)] += 1 })

  const total = indicadoresAutorizados.value.length
  const segmentos = CATEGORIAS_ESTADO
    .filter((categoria) => conteos[categoria] > 0)
    .map((categoria) => ({
      nombre: categoria,
      cantidad: conteos[categoria],
      porcentaje: total ? (conteos[categoria] / total) * 100 : 0,
      clase: claseEstadoNombre(categoria),
    }))

  return { total, segmentos, etiquetas: etiquetasDona(segmentos) }
})

const estiloDona = computed(() => {
  const { segmentos } = distribucionEstadoActual.value

  if (!segmentos.length) return { background: '#C7D0D9' }

  let acumulado = 0
  const partes = segmentos.map((segmento) => {
    const inicio = acumulado
    acumulado += segmento.porcentaje
    return `${COLOR_HEX_POR_CLASE[segmento.clase]} ${inicio}% ${acumulado}%`
  })

  return { background: `conic-gradient(${partes.join(', ')})` }
})

// ============================================================
// 3) KPI con evidencias — cuenta INDICADORES (con / sin evidencia)
// ============================================================

const evidenciasKpi = computed(() => resumenEvidencias(indicadoresAutorizados.value, medicionesAutorizadas.value))

// Barras horizontales: el largo es la proporción de KPI autorizados del
// contexto (con + sin = total), y la cantidad va al extremo de la barra.
const graficoEvidencias = computed(() => {
  const { con, sin, total } = evidenciasKpi.value

  return [
    { nombre: 'Con evidencia', cantidad: con, clase: 'steel', porcentaje: porcentajeDe(con, total) },
    { nombre: 'Sin evidencia', cantidad: sin, clase: 'neutral', porcentaje: porcentajeDe(sin, total) },
  ].map((barra) => ({ ...barra, ancho: alturaConteo(barra.cantidad, total) }))
})

// ============================================================
// 4) Oportunidad de registro — clasificación actual del backend
// ============================================================

// "A tiempo" y "Con retraso" son mediciones registradas; "Sin registro" son
// periodos cerrados sin medición (se muestran con su propio color, nunca
// como medición tardía). "Con ampliación" queda como nota secundaria.
const oportunidad = computed(() => resumenOportunidad(medicionesAutorizadas.value, SIN_REGISTRO))

const graficoOportunidad = computed(() => {
  const { aTiempo, conRetraso, sinRegistro, total } = oportunidad.value
  const eje = ejeConteo(Math.max(aTiempo, conRetraso, sinRegistro))

  return {
    eje,
    barras: [
      { nombre: 'A tiempo', cantidad: aTiempo, clase: 'ok', ayuda: 'Mediciones registradas dentro del plazo ordinario' },
      { nombre: 'Con retraso', cantidad: conRetraso, clase: 'warning', ayuda: 'Mediciones registradas después del plazo' },
      { nombre: SIN_REGISTRO, cantidad: sinRegistro, clase: 'danger', ayuda: 'Periodos cerrados por el sistema sin medición' },
    ].map((barra) => ({ ...barra, porcentaje: porcentajeDe(barra.cantidad, total), altura: (barra.cantidad / eje.tope) * 100 })),
  }
})

// ============================================================
// 5) Detalle de indicadores KPI — 8 por página
// ============================================================

const KPI_POR_PAGINA = 8
const paginaTabla = ref(1)

const SEVERIDAD = {
  Incumplido: 0,
  'En riesgo': 1,
  [SIN_REGISTRO]: 2,
  'Pendiente de actualización': 3,
  'Sin mediciones': 4,
}

const filasDetalle = computed(() => {
  const evidencias = evidenciasPorKpi(medicionesAutorizadas.value)

  return indicadoresAutorizados.value
    .map((kpi) => ({
      kpi,
      codigo: codigoKpi(kpi),
      objetivo: textoObjetivoKpi(kpi),
      cumplimiento: textoPromedioKpi(kpi),
      meta: formatearValorUnidad(kpi.valor_meta, kpi.unidad_medida),
      // Barra de la celda: solo para KPI en %, donde el valor ya está en
      // escala 0–100 (no se calcula ninguna relación con la meta).
      barra: kpi.unidad_medida === '%' && kpi.promedio_acumulado !== null && kpi.promedio_acumulado !== undefined
        ? Math.min(100, Math.max(0, Number(kpi.promedio_acumulado)))
        : null,
      categoria: categoriaKpi(kpi),
      evidencias: evidencias.get(kpi.id) || 0,
    }))
    .sort((a, b) => (SEVERIDAD[a.categoria] ?? 1.5) - (SEVERIDAD[b.categoria] ?? 1.5) || a.kpi.id - b.kpi.id)
})

// paginar() ajusta la página al rango válido: si los resultados disminuyen,
// nunca queda una página vacía.
const tablaPaginada = computed(() => paginar(filasDetalle.value, paginaTabla.value, KPI_POR_PAGINA))

function irPaginaTabla(pagina) {
  paginaTabla.value = paginar(filasDetalle.value, pagina, KPI_POR_PAGINA).pagina
}

// Cambiar año, plan estratégico o plan anual vuelve a la página 1.
watch(
  () => [seleccion.value.anio, seleccion.value.planEstrategico, seleccion.value.planAnual],
  () => {
    paginaTabla.value = 1
    paginaCumplimiento.value = 1
  },
)

function irAIndicador(id) {
  if (!id) return
  router.push({ path: '/indicadores', query: { resaltar: id } })
}

function cerrarSesion() {
  emit('logout')
}

onMounted(() => {
  cargarDatosDashboard()
})
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Panel de control"
    subtitulo="Estado general de los indicadores KPI"
    breadcrumb-actual="Panel de control"
    @logout="cerrarSesion"
  >
    <template #actions>
      <div class="encabezado-filtros">
        <label class="filtro-anio">
          <span>Plan anual:</span>
          <select :value="seleccion.anio || ''" aria-label="Año del plan anual" @change="seleccionarAnio($event.target.value)">
            <option value="">Todos</option>
            <option v-for="anio in anios" :key="anio" :value="anio">{{ anio }}</option>
          </select>
        </label>

        <!-- Filtros por plan, discretos: se despliegan a pedido. -->
        <details class="mas-filtros" :open="hayFiltroPlanes">
          <summary>Filtros<span v-if="hayFiltroPlanes" class="punto-activo"></span></summary>
          <div class="mas-filtros-panel">
            <label>
              <span>Plan estratégico</span>
              <select :value="seleccion.planEstrategico || ''" @change="seleccionarPlanEstrategico($event.target.value)">
                <option value="">Todos</option>
                <option v-for="plan in todosPlanesEstrategicos" :key="plan.id" :value="plan.id">
                  {{ plan.titulo }}{{ plan.estado === 'en_uso' ? '' : ` (${plan.estado === 'cerrado' ? 'Cerrado' : 'Borrador'})` }}
                </option>
              </select>
            </label>
            <label>
              <span>Plan anual</span>
              <select
                :value="seleccion.planAnual || ''"
                :disabled="!opcionesPlanAnual.length"
                @change="seleccionarPlanAnual($event.target.value)"
              >
                <option value="">Todos</option>
                <option v-for="anual in opcionesPlanAnual" :key="anual.id" :value="anual.id">
                  {{ anual.nombre }}{{ seleccion.planEstrategico ? '' : ` — ${anual.plan_estrategico_titulo}` }}
                </option>
              </select>
            </label>
          </div>
        </details>
      </div>
    </template>

    <div class="dashboard-content">
      <div v-if="cargando" class="dashboard-message">Cargando datos del panel de control...</div>
      <div v-if="error" class="dashboard-error">{{ error }}</div>

      <p v-if="hayFiltro" class="contexto-linea">
        Mostrando: {{ textoContexto }}
        <button type="button" class="btn-limpiar" @click="limpiarFiltro">Quitar filtros</button>
      </p>

      <!-- ===== Tarjetas resumen ===== -->
      <section class="tarjetas" aria-label="Resumen">
        <article v-for="tarjeta in tarjetas" :key="tarjeta.clave" class="tarjeta">
          <div class="tarjeta-icono" :class="tarjeta.clase" aria-hidden="true">
            <svg v-if="tarjeta.icono === 'capas'" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>
            <svg v-else-if="tarjeta.icono === 'calendario'" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            <svg v-else-if="tarjeta.icono === 'pulso'" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            <svg v-else-if="tarjeta.icono === 'check'" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8 12l2.5 2.5L16 9"/></svg>
            <svg v-else width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </div>
          <div class="tarjeta-valor">{{ tarjeta.valor }}</div>
          <div class="tarjeta-titulo">{{ tarjeta.titulo }}</div>
          <div class="tarjeta-detalle">{{ tarjeta.detalle }}</div>
        </article>
      </section>

      <!-- ===== Fila 1: Cumplimiento de KPI | Estado actual de KPI ===== -->
      <section class="fila-graficos fila-graficos--principal">
        <div class="card-panel">
          <div class="panel-head">
            <h2>
              <svg class="icono-titulo" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><line x1="6" y1="20" x2="6" y2="13"/><line x1="12" y1="20" x2="12" y2="8"/><line x1="18" y1="20" x2="18" y2="4"/></svg>
              Cumplimiento de KPI
            </h2>
            <div class="leyenda-mini">
              <span><i class="punto-leyenda"></i>Promedio acumulado</span>
              <span><i class="linea-meta"></i>Meta</span>
            </div>
          </div>

          <div v-if="!vistaCumplimiento" class="dashboard-message">
            No hay KPI autorizados{{ sufijoVacio }}.
          </div>

          <template v-else>
            <div v-if="gruposCumplimientoKpi.length > 1" class="unidades" role="tablist" aria-label="Unidad de medida">
              <button
                v-for="grupo in gruposCumplimientoKpi"
                :key="grupo.unidad"
                type="button"
                role="tab"
                class="unidad"
                :class="{ activa: grupo.unidad === vistaCumplimiento.unidad }"
                :aria-selected="grupo.unidad === vistaCumplimiento.unidad"
                @click="elegirUnidad(grupo.unidad)"
              >
                {{ grupo.unidad === '%' ? 'Porcentaje' : grupo.unidad }} ({{ grupo.barras.length }})
              </button>
            </div>

            <div class="grafico">
              <div class="eje" aria-hidden="true">
                <span v-for="marca in vistaCumplimiento.marcas" :key="marca.valor" :style="{ bottom: `${marca.altura}%` }">
                  {{ marca.texto }}
                </span>
              </div>
              <div class="area">
                <div
                  v-for="marca in vistaCumplimiento.marcas"
                  :key="`linea-${marca.valor}`"
                  class="linea-guia"
                  :style="{ bottom: `${marca.altura}%` }"
                ></div>

                <div
                  v-for="barra in vistaCumplimiento.barras"
                  :key="barra.kpi.id"
                  class="columna"
                  :title="barra.tooltip"
                  role="button"
                  tabindex="0"
                  @click="irAIndicador(barra.kpi.id)"
                  @keydown.enter="irAIndicador(barra.kpi.id)"
                >
                  <div class="columna-cuerpo">
                    <div
                      v-if="barra.metaPorcentaje !== null"
                      class="marca-meta"
                      :style="{ bottom: `${barra.metaPorcentaje}%` }"
                    ></div>
                    <div
                      class="barra"
                      :class="[barra.clase, { 'sin-dato': barra.sinDato }]"
                      :style="{ height: barra.sinDato ? '0' : `${barra.alturaPorcentaje}%` }"
                    >
                      <span class="barra-valor" :class="{ 'sin-dato': barra.sinDato }">
                        {{ barra.valorTexto }}<span v-if="barra.tieneOmisiones" class="marca-omision" title="Tiene periodos sin registro">*</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div></div>
              <div class="etiquetas">
                <div v-for="barra in vistaCumplimiento.barras" :key="`etiqueta-${barra.kpi.id}`" class="etiqueta" :title="barra.kpi.nombre">
                  <strong>{{ barra.codigo }}</strong>
                  <span>{{ barra.nombre }}</span>
                </div>
              </div>
            </div>

            <div v-if="vistaCumplimiento.totalPaginas > 1" class="paginador paginador--mini">
              <button type="button" :disabled="!vistaCumplimiento.hayAnterior" aria-label="KPI anteriores" @click="paginaCumplimiento = vistaCumplimiento.pagina - 1">‹</button>
              <span>{{ vistaCumplimiento.desde }}–{{ vistaCumplimiento.hasta }} de {{ vistaCumplimiento.total }}</span>
              <button type="button" :disabled="!vistaCumplimiento.haySiguiente" aria-label="KPI siguientes" @click="paginaCumplimiento = vistaCumplimiento.pagina + 1">›</button>
            </div>
          </template>
        </div>

        <div class="card-panel">
          <div class="panel-head">
            <h2>
              <svg class="icono-titulo" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>
              Estado actual de KPI
            </h2>
          </div>

          <div v-if="!distribucionEstadoActual.total" class="dashboard-message">
            No hay KPI autorizados{{ sufijoVacio }}.
          </div>

          <div v-else class="dona-contenido">
            <div class="dona-wrap">
              <div class="dona" :style="estiloDona"></div>
              <span
                v-for="etiqueta in distribucionEstadoActual.etiquetas"
                :key="etiqueta.nombre"
                class="dona-porcentaje"
                :style="{ left: `${etiqueta.x}%`, top: `${etiqueta.y}%` }"
              >{{ etiqueta.texto }}</span>
              <div class="dona-centro">
                <span class="dona-total">{{ distribucionEstadoActual.total }}</span>
                <span class="dona-label">KPI autorizados</span>
              </div>
            </div>

            <ul class="dona-leyenda">
              <li v-for="segmento in distribucionEstadoActual.segmentos" :key="segmento.nombre">
                <span class="legend-dot" :class="segmento.clase"></span>
                <span>
                  {{ segmento.nombre }}
                  <small>{{ segmento.cantidad }} ({{ Math.round(segmento.porcentaje) }}%)</small>
                </span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- ===== Fila 2: KPI con evidencias | Oportunidad de registro ===== -->
      <section class="fila-graficos">
        <div class="card-panel">
          <div class="panel-head">
            <h2>
              <svg class="icono-titulo" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/></svg>
              KPI con evidencias
            </h2>
          </div>

          <div v-if="!evidenciasKpi.total" class="dashboard-message">
            No hay KPI autorizados{{ sufijoVacio }}.
          </div>

          <div v-else class="barras-horizontales">
            <div
              v-for="barra in graficoEvidencias"
              :key="barra.nombre"
              class="fila-horizontal"
              :title="`${barra.nombre}: ${barra.cantidad} de ${evidenciasKpi.total} KPI (${barra.porcentaje}%)`"
            >
              <div class="horizontal-etiqueta">
                <strong>{{ barra.nombre }}</strong>
                <span>{{ barra.porcentaje }}%</span>
              </div>
              <div class="horizontal-track">
                <div class="horizontal-barra" :class="barra.clase" :style="{ width: `${barra.ancho}%` }"></div>
                <span class="horizontal-valor">{{ barra.cantidad }}</span>
              </div>
            </div>
            <p class="nota-secundaria">De {{ evidenciasKpi.total }} KPI autorizados</p>
          </div>
        </div>

        <div class="card-panel">
          <div class="panel-head">
            <h2>
              <svg class="icono-titulo" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
              Oportunidad de registro
            </h2>
          </div>

          <div v-if="!oportunidad.total" class="dashboard-message">
            No hay mediciones ni periodos cerrados{{ sufijoVacio }}.
          </div>

          <template v-else>
            <div class="grafico grafico--conteo">
              <div class="eje" aria-hidden="true">
                <span v-for="marca in graficoOportunidad.eje.marcas" :key="marca" :style="{ bottom: `${(marca / graficoOportunidad.eje.tope) * 100}%` }">{{ marca }}</span>
              </div>
              <div class="area area--conteo">
                <div v-for="marca in graficoOportunidad.eje.marcas" :key="`l-${marca}`" class="linea-guia" :style="{ bottom: `${(marca / graficoOportunidad.eje.tope) * 100}%` }"></div>
                <div
                  v-for="barra in graficoOportunidad.barras"
                  :key="barra.nombre"
                  class="columna columna--conteo"
                  :title="barra.ayuda"
                >
                  <div class="columna-cuerpo">
                    <div class="barra" :class="barra.clase" :style="{ height: `${barra.altura}%` }">
                      <span class="barra-valor">{{ barra.cantidad }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div></div>
              <div class="etiquetas etiquetas--conteo">
                <div v-for="barra in graficoOportunidad.barras" :key="`o-${barra.nombre}`" class="etiqueta" :title="barra.ayuda">
                  <strong>{{ barra.nombre }}</strong>
                  <span>({{ barra.porcentaje }}%)</span>
                </div>
              </div>
            </div>

            <p v-if="oportunidad.conAmpliacion" class="nota-secundaria">
              Además, {{ oportunidad.conAmpliacion }} medición(es) registrada(s) con días adicionales autorizados.
            </p>
          </template>
        </div>
      </section>

      <!-- ===== Fila 3: Detalle de indicadores KPI ===== -->
      <section class="card-panel">
        <div class="panel-head">
          <h2>
            <svg class="icono-titulo" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="18" x2="20" y2="18"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/></svg>
            Detalle de indicadores KPI
          </h2>
          <span v-if="tablaPaginada.total" class="total-kpi">{{ tablaPaginada.total }} KPI encontrados</span>
        </div>

        <div v-if="!tablaPaginada.total" class="dashboard-message">
          No hay KPI autorizados{{ sufijoVacio }}.
        </div>

        <template v-else>
          <div class="table-scroll">
            <table>
              <colgroup>
                <col style="width: 9%">
                <col style="width: 26%">
                <col style="width: 23%">
                <col style="width: 18%">
                <col style="width: 14%">
                <col style="width: 10%">
              </colgroup>
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Nombre del indicador</th>
                  <th>Objetivo</th>
                  <th title="Promedio acumulado, en la unidad del KPI">Cumplimiento</th>
                  <th title="Estado acumulado según los rangos del KPI">Estado</th>
                  <th title="Archivos de evidencia en las mediciones del KPI">Evidencias</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="fila in tablaPaginada.elementos"
                  :key="fila.kpi.id"
                  class="fila-navegable"
                  @click="irAIndicador(fila.kpi.id)"
                >
                  <td class="celda-codigo">{{ fila.codigo }}</td>
                  <td>
                    <button type="button" class="nombre-kpi" :title="`Ver el detalle de ${fila.kpi.nombre}`" @click.stop="irAIndicador(fila.kpi.id)">
                      {{ fila.kpi.nombre }}
                    </button>
                  </td>
                  <td class="celda-texto" :title="fila.objetivo">{{ fila.objetivo }}</td>
                  <td :title="`Meta: ${fila.meta}`">
                    <div class="cumplimiento-celda">
                      <span class="celda-valor">{{ fila.cumplimiento }}</span>
                      <span v-if="fila.barra !== null" class="mini-track">
                        <span class="mini-barra" :class="claseEstadoNombre(fila.categoria)" :style="{ width: `${fila.barra}%` }"></span>
                      </span>
                    </div>
                  </td>
                  <td>
                    <span class="badge" :class="claseEstadoNombre(fila.categoria)">
                      <span class="badge-dot"></span>
                      {{ textoEstadoCumplimiento(fila.categoria) }}
                    </span>
                  </td>
                  <td>
                    <span class="evidencias-celda" :class="{ 'es-cero': !fila.evidencias }">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                      {{ fila.evidencias }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <nav class="paginador" aria-label="Paginación de indicadores">
            <span class="paginador-rango">{{ tablaPaginada.desde }}–{{ tablaPaginada.hasta }} de {{ tablaPaginada.total }} KPI</span>
            <div class="paginador-controles">
              <button type="button" :disabled="!tablaPaginada.hayAnterior" @click="irPaginaTabla(tablaPaginada.pagina - 1)">Anterior</button>
              <span>Página {{ tablaPaginada.pagina }} de {{ tablaPaginada.totalPaginas }}</span>
              <button type="button" :disabled="!tablaPaginada.haySiguiente" @click="irPaginaTabla(tablaPaginada.pagina + 1)">Siguiente</button>
            </div>
          </nav>
        </template>
      </section>
    </div>
  </AppLayout>
</template>

<style scoped>
  .dashboard-content{
    --navy:#1D3557;
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
    --radius-md:14px;
    --radius-sm:10px;
    --shadow-card: 0 2px 10px rgba(29,53,87,0.05), 0 1px 2px rgba(29,53,87,0.04);
    font-family:'Montserrat', sans-serif;
    color:var(--navy);
  }
  .dashboard-content *{ box-sizing:border-box; }

  /* ---- encabezado: año y filtros discretos ---- */
  .encabezado-filtros{ display:flex; align-items:center; gap:10px; position:relative; font-family:'Montserrat', sans-serif; }
  .filtro-anio{ display:flex; align-items:center; gap:8px; }
  .filtro-anio span{ font-size:13px; font-weight:600; color:#5E6E82; }
  .filtro-anio select{
    height:40px;
    min-width:120px;
    padding:0 12px;
    border:1.5px solid #E4EAEF;
    border-radius:10px;
    background:#FFFFFF;
    font-family:inherit;
    font-size:14px;
    font-weight:700;
    color:#1D3557;
    box-shadow:0 2px 10px rgba(29,53,87,0.05);
  }
  .mas-filtros{ position:relative; }
  .mas-filtros summary{
    list-style:none;
    display:flex;
    align-items:center;
    gap:6px;
    height:40px;
    padding:0 12px;
    border:1.5px solid #E4EAEF;
    border-radius:10px;
    background:#FFFFFF;
    font-size:12.5px;
    font-weight:700;
    color:#5E6E82;
    cursor:pointer;
  }
  .mas-filtros summary::-webkit-details-marker{ display:none; }
  .punto-activo{ width:7px; height:7px; border-radius:50%; background:#457B9D; }
  .mas-filtros-panel{
    position:absolute;
    right:0;
    top:46px;
    z-index:20;
    width:280px;
    display:flex;
    flex-direction:column;
    gap:10px;
    padding:12px;
    border:1px solid #E4EAEF;
    border-radius:12px;
    background:#FFFFFF;
    box-shadow:0 10px 26px rgba(29,53,87,0.12);
  }
  .mas-filtros-panel label{ display:flex; flex-direction:column; gap:4px; }
  .mas-filtros-panel span{ font-size:11px; font-weight:700; color:#9AA8B8; }
  .mas-filtros-panel select{
    height:34px;
    border:1px solid #E4EAEF;
    border-radius:8px;
    padding:0 8px;
    font-family:inherit;
    font-size:12.5px;
    font-weight:600;
    color:#1D3557;
  }
  .mas-filtros-panel select:disabled{ background:#F6F9FA; color:#9AA8B8; }

  .contexto-linea{ margin:-4px 0 12px; font-size:11.5px; font-weight:600; color:var(--text-muted); }
  .btn-limpiar{
    border:none;
    background:none;
    padding:0 0 0 6px;
    color:var(--steel);
    font-family:inherit;
    font-size:11.5px;
    font-weight:700;
    cursor:pointer;
    text-decoration:underline;
  }

  /* ---- tarjetas resumen ---- */
  .tarjetas{ display:grid; grid-template-columns:repeat(5, minmax(0, 1fr)); gap:14px; margin-bottom:16px; }
  .tarjeta{
    background:var(--white);
    border:1px solid var(--border);
    border-radius:var(--radius-md);
    box-shadow:var(--shadow-card);
    padding:16px 16px 14px;
    min-width:0;
  }
  .tarjeta-icono{ width:34px; height:34px; border-radius:9px; display:flex; align-items:center; justify-content:center; margin-bottom:12px; }
  .tarjeta-icono.navy{ background:rgba(29,53,87,0.08); color:var(--navy); }
  .tarjeta-icono.steel{ background:rgba(69,123,157,0.10); color:var(--steel); }
  .tarjeta-icono.aqua{ background:var(--aqua-soft); color:var(--steel); }
  .tarjeta-icono.ok{ background:rgba(42,157,143,0.12); color:var(--success); }
  .tarjeta-icono.danger{ background:rgba(231,111,81,0.12); color:var(--danger); }
  .tarjeta-valor{ font-size:26px; font-weight:800; line-height:1; margin-bottom:6px; }
  .tarjeta-titulo{ font-size:13px; font-weight:700; margin-bottom:4px; }
  .tarjeta-detalle{ font-size:11.5px; font-weight:500; color:var(--text-muted); }

  /* ---- paneles ---- */
  .card-panel{
    background:var(--white);
    border:1px solid var(--border);
    border-radius:var(--radius-md);
    box-shadow:var(--shadow-card);
    padding:16px 18px 16px;
    min-width:0;
  }
  .panel-head{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:12px; flex-wrap:wrap; }
  .panel-head h2{ display:flex; align-items:center; gap:8px; font-size:14.5px; font-weight:800; margin:0; }
  .icono-titulo{ color:var(--steel); flex-shrink:0; }
  .leyenda-mini{ display:flex; gap:12px; font-size:11px; font-weight:600; color:var(--text-secondary); }
  .leyenda-mini span{ display:flex; align-items:center; gap:5px; }
  .punto-leyenda{ width:8px; height:8px; border-radius:50%; background:var(--steel); display:inline-block; }
  .linea-meta{ width:14px; border-top:2px dashed var(--navy); opacity:.6; display:inline-block; }
  .total-kpi{ font-size:11.5px; font-weight:700; color:var(--text-muted); }

  .fila-graficos{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; align-items:stretch; }
  .fila-graficos--principal{ grid-template-columns:1.45fr 1fr; }

  /* ---- gráficos de barras (eje + área + etiquetas) ---- */
  .unidades{ display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }
  .unidad{
    height:26px;
    padding:0 10px;
    border-radius:13px;
    border:1px solid var(--border);
    background:var(--white);
    font-family:inherit;
    font-size:11px;
    font-weight:700;
    color:var(--text-secondary);
    cursor:pointer;
  }
  .unidad.activa{ background:var(--navy); border-color:var(--navy); color:var(--white); }

  .grafico{ display:grid; grid-template-columns:34px 1fr; grid-template-rows:180px auto; column-gap:6px; }
  .grafico--conteo{ grid-template-rows:150px auto; }
  .eje{ position:relative; }
  .eje span{
    position:absolute;
    right:0;
    transform:translateY(50%);
    font-size:10px;
    font-weight:600;
    color:var(--text-muted);
    white-space:nowrap;
  }
  .area{
    position:relative;
    display:flex;
    align-items:flex-end;
    justify-content:space-around;
    gap:10px;
    border-left:1px solid var(--border);
    border-bottom:1px solid var(--border);
    padding:0 8px;
  }
  .area--conteo{ justify-content:center; gap:28px; }
  .linea-guia{ position:absolute; left:0; right:0; border-top:1px solid #F1F4F7; pointer-events:none; }
  /* Área y etiquetas usan la misma distribución (flex 1 o 84px fijos y el
     mismo gap), así cada etiqueta queda debajo de su barra. */
  .columna{ position:relative; flex:1 1 0; min-width:0; height:100%; cursor:pointer; outline:none; }
  .columna--conteo{ flex:0 0 84px; cursor:default; }
  .columna:focus-visible .barra{ box-shadow:0 0 0 2px var(--aqua); }
  .columna-cuerpo{ position:absolute; inset:0; display:flex; align-items:flex-end; justify-content:center; }
  .barra{ position:relative; width:100%; max-width:46px; border-radius:6px 6px 0 0; transition:height .2s ease, opacity .15s ease; }
  .columna--conteo .barra{ max-width:56px; }
  .columna:hover .barra{ opacity:0.85; }
  .barra.ok{ background:var(--success); }
  .barra.warning{ background:var(--orange); }
  .barra.danger{ background:var(--danger); }
  .barra.steel{ background:#4A90D9; }
  .barra.neutral{ background:#C7D0D9; }
  .barra.omision{ background:repeating-linear-gradient(45deg, #8D99AE 0 4px, #C7D0D9 4px 8px); }
  .barra-valor{
    position:absolute;
    bottom:100%;
    left:50%;
    transform:translateX(-50%);
    margin-bottom:4px;
    font-size:11.5px;
    font-weight:800;
    color:var(--navy);
    white-space:nowrap;
  }
  .barra-valor.sin-dato{ font-size:9.5px; font-weight:700; color:var(--text-muted); }
  .marca-meta{ position:absolute; left:-5px; right:-5px; border-top:2px dashed var(--navy); opacity:.55; z-index:2; pointer-events:none; }
  .etiquetas{ display:flex; justify-content:space-around; gap:10px; padding:6px 8px 0; }
  .etiquetas--conteo{ justify-content:center; gap:28px; }
  .etiqueta{ flex:1 1 0; display:flex; flex-direction:column; align-items:center; text-align:center; min-width:0; }
  .etiquetas--conteo .etiqueta{ flex:0 0 84px; }
  .etiqueta strong{ font-size:11px; font-weight:800; color:var(--navy); white-space:nowrap; }
  .etiqueta span{ font-size:10px; font-weight:600; color:var(--text-muted); line-height:1.25; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }
  .marca-omision{ color:#55657A; font-weight:800; margin-left:2px; }
  .nota-secundaria{ margin:10px 0 0; font-size:11px; color:var(--text-muted); font-weight:600; text-align:center; }

  /* ---- KPI con evidencias: barras horizontales ---- */
  .barras-horizontales{ display:flex; flex-direction:column; justify-content:center; gap:16px; min-height:150px; padding:6px 2px 0; }
  .fila-horizontal{ display:grid; grid-template-columns:120px 1fr; align-items:center; gap:12px; }
  .horizontal-etiqueta{ display:flex; flex-direction:column; min-width:0; }
  .horizontal-etiqueta strong{ font-size:12px; font-weight:800; color:var(--navy); white-space:nowrap; }
  .horizontal-etiqueta span{ font-size:11px; font-weight:600; color:var(--text-muted); }
  /* La barra crece hasta el ancho disponible menos el espacio de la cantidad. */
  .horizontal-track{ display:flex; align-items:center; gap:8px; height:26px; min-width:0; }
  .horizontal-barra{ height:100%; max-width:calc(100% - 36px); min-width:3px; border-radius:0 6px 6px 0; transition:width .2s ease; }
  .horizontal-barra.steel{ background:#4A90D9; }
  .horizontal-barra.neutral{ background:#C7D0D9; }
  .horizontal-valor{ font-size:14px; font-weight:800; color:var(--navy); flex-shrink:0; }

  /* ---- dona ---- */
  .dona-contenido{ display:flex; align-items:center; justify-content:center; gap:22px; flex-wrap:wrap; padding-top:6px; }
  .dona-wrap{ position:relative; width:190px; height:190px; flex-shrink:0; }
  .dona{ width:100%; height:100%; border-radius:50%; }
  .dona-porcentaje{
    position:absolute;
    transform:translate(-50%, -50%);
    font-size:11px;
    font-weight:800;
    color:#FFFFFF;
    text-shadow:0 1px 2px rgba(0,0,0,0.25);
    pointer-events:none;
  }
  .dona-centro{
    position:absolute;
    inset:0;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    width:104px;
    height:104px;
    margin:auto;
    border-radius:50%;
    background:var(--white);
  }
  .dona-total{ font-size:28px; font-weight:800; line-height:1; }
  .dona-label{ font-size:10.5px; font-weight:700; color:var(--text-muted); margin-top:3px; text-align:center; max-width:80px; }
  .dona-leyenda{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:10px; }
  .dona-leyenda li{ display:flex; align-items:flex-start; gap:8px; font-size:12px; font-weight:700; color:var(--navy); }
  .dona-leyenda small{ display:block; font-size:11px; font-weight:600; color:var(--text-muted); margin-top:1px; }
  .legend-dot{ width:9px; height:9px; border-radius:50%; flex-shrink:0; margin-top:3px; }
  .legend-dot.ok{ background:var(--success); }
  .legend-dot.warning{ background:var(--orange); }
  .legend-dot.danger{ background:var(--danger); }
  .legend-dot.neutral{ background:#C7D0D9; }
  .legend-dot.omision{ background:repeating-linear-gradient(45deg, #8D99AE 0 4px, #C7D0D9 4px 8px); }

  /* ---- tabla ---- */
  .table-scroll{ overflow-x:auto; }
  table{ width:100%; border-collapse:collapse; min-width:760px; table-layout:fixed; }
  thead th{
    text-align:left;
    font-size:11.5px;
    font-weight:700;
    color:var(--navy);
    background:var(--bg);
    padding:9px 12px;
  }
  thead th:first-child{ border-radius:8px 0 0 8px; }
  thead th:last-child{ border-radius:0 8px 8px 0; }
  tbody td{ padding:9px 12px; font-size:12.5px; color:var(--navy); border-bottom:1px solid #F1F4F7; vertical-align:middle; }
  tbody tr:last-child td{ border-bottom:none; }
  .fila-navegable{ cursor:pointer; transition:background .12s ease; }
  .fila-navegable:hover{ background:#FAFCFD; }
  .celda-codigo{ font-weight:800; }
  .celda-texto{ font-size:12px; color:var(--text-secondary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .celda-valor{ font-weight:700; white-space:nowrap; }
  .nombre-kpi{
    border:none;
    background:none;
    padding:0;
    text-align:left;
    font-family:inherit;
    font-size:12.5px;
    font-weight:600;
    color:var(--navy);
    line-height:1.35;
    cursor:pointer;
    word-break:break-word;
  }
  .nombre-kpi:hover{ color:var(--steel); text-decoration:underline; }
  .cumplimiento-celda{ display:flex; align-items:center; gap:10px; }
  .mini-track{ flex:1; height:7px; border-radius:4px; background:#EEF2F5; overflow:hidden; min-width:50px; }
  .mini-barra{ display:block; height:100%; border-radius:4px; }
  .mini-barra.ok{ background:var(--success); }
  .mini-barra.warning{ background:var(--orange); }
  .mini-barra.danger{ background:var(--danger); }
  .mini-barra.neutral{ background:#C7D0D9; }
  .evidencias-celda{ display:inline-flex; align-items:center; gap:5px; font-weight:700; color:var(--text-secondary); }
  .evidencias-celda.es-cero{ color:var(--text-muted); font-weight:600; }

  .badge{
    display:inline-flex;
    align-items:center;
    gap:5px;
    font-size:11px;
    font-weight:700;
    padding:3px 9px;
    border-radius:6px;
    white-space:nowrap;
    max-width:100%;
  }
  .badge.ok{ background:rgba(42,157,143,0.12); color:var(--success); }
  .badge.warning{ background:rgba(244,162,97,0.16); color:#B9701E; }
  .badge.danger{ background:rgba(231,111,81,0.12); color:var(--danger); }
  .badge.neutral{ background:rgba(154,168,184,0.16); color:var(--text-muted); }
  .badge.omision{ background:rgba(141,153,174,0.20); color:#55657A; border:1px dashed #8D99AE; }
  .badge-dot{ width:7px; height:7px; border-radius:50%; background:currentColor; flex-shrink:0; }

  /* ---- paginación ---- */
  .paginador{ display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; margin-top:12px; font-size:12px; font-weight:600; color:var(--text-secondary); }
  .paginador-controles{ display:flex; align-items:center; gap:10px; }
  .paginador button{
    height:30px;
    padding:0 12px;
    border-radius:8px;
    border:1px solid var(--border);
    background:var(--white);
    font-family:inherit;
    font-size:12px;
    font-weight:700;
    color:var(--navy);
    cursor:pointer;
  }
  .paginador button:hover:not(:disabled){ background:var(--aqua-soft); }
  .paginador button:disabled{ opacity:.45; cursor:not-allowed; }
  .paginador--mini{ justify-content:center; margin-top:8px; }
  .paginador--mini button{ width:30px; padding:0; font-size:15px; }

  .dashboard-message,
  .dashboard-error{ margin-bottom:12px; padding:12px 14px; border-radius:var(--radius-sm); font-size:13px; font-weight:600; }
  .dashboard-message{ background:var(--aqua-soft); color:var(--steel); }
  .dashboard-error{ background:rgba(231,111,81,0.12); color:var(--danger); }

  /* ===================== RESPONSIVE ===================== */
  @media (max-width:1280px){
    .tarjetas{ grid-template-columns:repeat(3, minmax(0, 1fr)); }
  }
  @media (max-width:1100px){
    .fila-graficos,
    .fila-graficos--principal{ grid-template-columns:1fr; }
  }
  @media (max-width:760px){
    .tarjetas{ grid-template-columns:repeat(2, minmax(0, 1fr)); }
    .encabezado-filtros{ flex-wrap:wrap; }
    .mas-filtros-panel{ right:auto; left:0; }
  }
  @media (max-width:480px){
    .tarjetas{ grid-template-columns:1fr; }
    .area--conteo, .etiquetas--conteo{ gap:14px; }
  }
</style>
