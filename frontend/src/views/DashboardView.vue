<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import { obtenerIndicadoresKpi } from '../services/indicadorService'
import { obtenerMediciones } from '../services/medicionService'
import { obtenerAlertasPendientes } from '../services/alertaService'
import { obtenerPlanesEstrategicos } from '../services/planEstrategicoService'
import { obtenerPlanesAnuales } from '../services/planAnualService'
import { formatearNumero } from '../utils/formato'
import { claseColorCumplimiento, textoEstadoCumplimiento } from '../utils/cumplimiento'

// Bloque 6: el Dashboard se reconstruye sobre la jerarquía vigente
// (PlanEstrategico -> PlanAnual -> ObjetivoEspecifico -> IndicadorKPI ->
// Medicion) y sobre los campos de acumulado ya expuestos desde el Bloque 5
// (promedio_acumulado, cantidad_mediciones, estado_acumulado_*). No existe
// endpoint de agregación en el backend: se reutilizan los services ya
// existentes de cada módulo (mismo patrón que Indicadores/Mediciones), sin
// volver a golpear endpoints viejos (estrategias/, objetivos/).

const router = useRouter()

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

const planesEstrategicos = ref([])
const planesAnuales = ref([])
const indicadores = ref([])
const mediciones = ref([])
const alertasPendientes = ref([])

async function cargarDatosDashboard() {
  cargando.value = true
  error.value = ''

  try {
    const [
      planesEstrategicosData,
      planesAnualesData,
      indicadoresData,
      medicionesData,
      alertasData,
    ] = await Promise.all([
      obtenerPlanesEstrategicos(),
      obtenerPlanesAnuales(),
      obtenerIndicadoresKpi(),
      obtenerMediciones(),
      obtenerAlertasPendientes(),
    ])

    planesEstrategicos.value = planesEstrategicosData
    planesAnuales.value = planesAnualesData
    indicadores.value = indicadoresData
    mediciones.value = medicionesData
    alertasPendientes.value = alertasData
  } catch (e) {
    error.value = 'No se pudieron cargar los datos del panel de control.'
  } finally {
    cargando.value = false
  }
}

// ============================================================
// Jerarquía / estado base
// ============================================================

// Punto 32: borrador y anulado nunca representan un KPI en seguimiento.
// Todas las tarjetas y gráficos gerenciales parten de este único filtro.
const indicadoresAutorizados = computed(() => {
  return indicadores.value.filter((kpi) => kpi.estado === 'autorizado')
})

const ESTADOS_ATENCION = ['En riesgo', 'Incumplido']

// Punto 31: "en uso" es el único criterio para los contadores gerenciales;
// un PlanEstrategico Cerrado o Borrador no cuenta acá (documentado también
// en la entrega final).
const planesEstrategicosEnUso = computed(() => {
  return planesEstrategicos.value.filter((plan) => plan.estado === 'en_uso')
})

// ============================================================
// 1) Tarjetas superiores
// ============================================================

const totalPlanesEstrategicosEnUso = computed(() => planesEstrategicosEnUso.value.length)

const totalPlanesAnualesEnUso = computed(() => {
  return planesAnuales.value.filter((plan) => plan.estado === 'en_uso').length
})

const totalKpiAutorizados = computed(() => indicadoresAutorizados.value.length)

const totalKpiFavorables = computed(() => {
  return indicadoresAutorizados.value.filter((kpi) => {
    return kpi.cantidad_mediciones > 0 && kpi.estado_acumulado_nombre === 'Favorable'
  }).length
})

const totalKpiRequierenAtencion = computed(() => {
  return indicadoresAutorizados.value.filter((kpi) => {
    return ESTADOS_ATENCION.includes(kpi.estado_acumulado_nombre)
  }).length
})

const totalCierresAutomaticos = computed(() => {
  return mediciones.value.filter((medicion) => medicion.cierre_automatico).length
})

// ============================================================
// Colores: SIEMPRE derivados de estado_acumulado_color /
// estado_acumulado_hasta_medicion_color reales (nunca thresholds). Como
// los gráficos agregan por NOMBRE de estado (no por una fila puntual), se
// arma un mapa nombre -> color real tomado de los propios datos cargados.
// "Sin mediciones" es la única categoría sin equivalente backend (no hay
// EstadoCumplimiento para "todavía no se midió"): usa la clase neutral ya
// existente en cumplimiento.js, igual que el resto del sistema.
// ============================================================

const coloresPorNombreEstado = computed(() => {
  const mapa = new Map()

  indicadores.value.forEach((kpi) => {
    if (kpi.estado_acumulado_nombre && kpi.estado_acumulado_color) {
      mapa.set(kpi.estado_acumulado_nombre, kpi.estado_acumulado_color)
    }
  })

  mediciones.value.forEach((medicion) => {
    if (medicion.estado_acumulado_hasta_medicion_nombre && medicion.estado_acumulado_hasta_medicion_color) {
      mapa.set(medicion.estado_acumulado_hasta_medicion_nombre, medicion.estado_acumulado_hasta_medicion_color)
    }
  })

  return mapa
})

function claseEstadoNombre(nombre) {
  if (!nombre || nombre === 'Sin mediciones') return 'neutral'

  return claseColorCumplimiento(coloresPorNombreEstado.value.get(nombre))
}

// Punto 26: "Sin mediciones" (cantidad_mediciones === 0) y "Pendiente de
// actualización" (sí hay mediciones pero ningún RangoKPI aplica) son dos
// categorías distintas — nunca se tratan como la misma cosa.
function categorizarKpi(kpi) {
  if (!kpi.cantidad_mediciones) return 'Sin mediciones'

  return kpi.estado_acumulado_nombre || 'Pendiente de actualización'
}

// ============================================================
// 2) Primer gráfico — Estado de KPI por Plan estratégico
// ============================================================

const CATEGORIAS_ESTADO = ['Favorable', 'En riesgo', 'Incumplido', 'Pendiente de actualización', 'Sin mediciones']

const distribucionPorPlan = computed(() => {
  return planesEstrategicosEnUso.value
    .map((plan) => {
      // Punto 30: relación por FK/id real (IndicadorKPISerializer expone
      // plan_estrategico como id), nunca por nombre.
      const kpisDelPlan = indicadoresAutorizados.value.filter((kpi) => {
        return Number(kpi.plan_estrategico) === Number(plan.id)
      })

      const conteos = {}
      CATEGORIAS_ESTADO.forEach((categoria) => { conteos[categoria] = 0 })
      kpisDelPlan.forEach((kpi) => { conteos[categorizarKpi(kpi)] += 1 })

      const total = kpisDelPlan.length

      const segmentos = CATEGORIAS_ESTADO
        .filter((categoria) => conteos[categoria] > 0)
        .map((categoria) => ({
          nombre: categoria,
          cantidad: conteos[categoria],
          porcentaje: total ? (conteos[categoria] / total) * 100 : 0,
          clase: claseEstadoNombre(categoria),
        }))

      return {
        id: plan.id,
        nombre: plan.titulo,
        total,
        segmentos,
      }
    })
    // Punto 8: se muestran TODOS los planes en uso, incluidos los que
    // tienen 0 KPI o 0 mediciones — nunca se ocultan.
    .sort((a, b) => a.nombre.localeCompare(b.nombre))
})

// ============================================================
// 3) Segundo gráfico — Evolución mensual del estado de KPI
// ============================================================

// Solo mediciones de KPI actualmente autorizados (punto 32), y solo las
// que tienen fecha_medicion (siempre la tienen, pero se guarda como
// defensa ante datos incompletos).
const medicionesAutorizadas = computed(() => {
  const idsAutorizados = new Set(indicadoresAutorizados.value.map((kpi) => kpi.id))

  return mediciones.value.filter((medicion) => {
    return idsAutorizados.has(medicion.indicador) && medicion.fecha_medicion
  })
})

// Punto 13: fecha_medicion, NUNCA fecha_registro (una medición de enero
// registrada en febrero sigue siendo de enero). Las claves 'YYYY-MM' se
// comparan como texto: el orden alfabético coincide con el cronológico.
function obtenerClaveMes(fechaMedicion) {
  return fechaMedicion.slice(0, 7)
}

const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
const MESES_LARGOS = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

function formatearMesCorto(claveMes) {
  const [anio, mes] = claveMes.split('-')
  return `${MESES_CORTOS[Number(mes) - 1]} ${anio.slice(2)}`
}

function formatearMesLargo(claveMes) {
  const [anio, mes] = claveMes.split('-')
  return `${MESES_LARGOS[Number(mes) - 1]} ${anio}`
}

// Punto 14/15: máximo 12 meses, orden cronológico ascendente, solo meses
// con al menos una medición real (no se inventan meses vacíos en medio).
const mesesEvolucion = computed(() => {
  const claves = new Set(medicionesAutorizadas.value.map((medicion) => obtenerClaveMes(medicion.fecha_medicion)))

  return Array.from(claves).sort().slice(-12)
})

const CATEGORIAS_EVOLUCION = ['Favorable', 'En riesgo', 'Incumplido', 'Pendiente de actualización']

const evolucionPorMes = computed(() => {
  return mesesEvolucion.value.map((mesClave) => {
    // Punto 15: denominador = KPI que YA tenían al menos una medición
    // acumulada hasta ese mes (arrastra el último estado conocido de cada
    // KPI, no solo los medidos ese mes puntual).
    const ultimaMedicionPorKpi = new Map()

    medicionesAutorizadas.value.forEach((medicion) => {
      const claveMedicion = obtenerClaveMes(medicion.fecha_medicion)

      if (claveMedicion > mesClave) return

      const anterior = ultimaMedicionPorKpi.get(medicion.indicador)

      if (!anterior || medicion.fecha_medicion > anterior.fecha_medicion) {
        ultimaMedicionPorKpi.set(medicion.indicador, medicion)
      }
    })

    const conteos = {}
    CATEGORIAS_EVOLUCION.forEach((categoria) => { conteos[categoria] = 0 })

    ultimaMedicionPorKpi.forEach((medicion) => {
      const nombre = medicion.estado_acumulado_hasta_medicion_nombre

      if (nombre && Object.prototype.hasOwnProperty.call(conteos, nombre)) {
        conteos[nombre] += 1
      }
    })

    const total = ultimaMedicionPorKpi.size

    const segmentos = CATEGORIAS_EVOLUCION
      .filter((categoria) => conteos[categoria] > 0)
      .map((categoria) => ({
        nombre: categoria,
        cantidad: conteos[categoria],
        porcentaje: total ? (conteos[categoria] / total) * 100 : 0,
        clase: claseEstadoNombre(categoria),
      }))

    return {
      clave: mesClave,
      etiqueta: formatearMesCorto(mesClave),
      etiquetaCompleta: formatearMesLargo(mesClave),
      total,
      segmentos,
    }
  })
})

// ============================================================
// 4) KPI que requieren atención
// ============================================================

function ultimaFechaMedicionDeKpi(kpiId) {
  let ultima = ''

  mediciones.value.forEach((medicion) => {
    if (medicion.indicador === kpiId && medicion.fecha_medicion > ultima) {
      ultima = medicion.fecha_medicion
    }
  })

  return ultima
}

// Punto 17: se ordena por SEVERIDAD (Incumplido antes que En riesgo),
// nunca por promedio_acumulado bruto (unidades distintas no son
// comparables). Dentro del mismo estado, por actualización más reciente.
const SEVERIDAD_ATENCION = { Incumplido: 0, 'En riesgo': 1 }

const kpiRequierenAtencionLista = computed(() => {
  return indicadoresAutorizados.value
    .filter((kpi) => ESTADOS_ATENCION.includes(kpi.estado_acumulado_nombre))
    .map((kpi) => ({ ...kpi, _ultimaMedicion: ultimaFechaMedicionDeKpi(kpi.id) }))
    .sort((a, b) => {
      const severidadA = SEVERIDAD_ATENCION[a.estado_acumulado_nombre] ?? 99
      const severidadB = SEVERIDAD_ATENCION[b.estado_acumulado_nombre] ?? 99

      if (severidadA !== severidadB) return severidadA - severidadB

      return b._ultimaMedicion.localeCompare(a._ultimaMedicion)
    })
})

// ============================================================
// 5) Últimas mediciones y alertas pendientes
// ============================================================

function obtenerFechaOrden(item) {
  return item?.fecha_registro || item?.fecha_generacion || ''
}

const ultimasMediciones = computed(() => {
  return [...mediciones.value]
    .sort((a, b) => new Date(obtenerFechaOrden(b)) - new Date(obtenerFechaOrden(a)))
    .slice(0, 5)
})

const alertasRecientes = computed(() => {
  return [...alertasPendientes.value]
    .sort((a, b) => new Date(obtenerFechaOrden(b)) - new Date(obtenerFechaOrden(a)))
    .slice(0, 5)
})

function claseAlerta(alerta) {
  const texto = `${alerta.tipo_alerta || ''} ${alerta.mensaje || ''}`.toLowerCase()

  if (texto.includes('incumplido')) return 'danger'
  if (texto.includes('riesgo') || texto.includes('vencido')) return 'warning'

  return 'neutral'
}

function tipoRegistroMedicion(medicion) {
  return medicion.cierre_automatico ? 'Automático' : 'Manual'
}

// ============================================================
// Formato / presentación (siempre vía formato.js, nunca Math.round)
// ============================================================

function formatearValorUnidad(valor, unidad) {
  if (valor === null || valor === undefined) return 'Sin mediciones'

  return formatearNumero(valor, { unidad: unidad || '' })
}

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

// ============================================================
// Navegación (reutiliza el patrón ?resaltar= ya existente en
// Indicadores/Mediciones/Planes estratégicos — useResaltado)
// ============================================================

function irAPlanEstrategico(id) {
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

function verTodosLosKpi() {
  router.push('/indicadores')
}

function verTodasLasMediciones() {
  router.push('/mediciones')
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
    subtitulo="Seguimiento gerencial de planes estratégicos, planes anuales y KPI"
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

      <div v-if="cargando" class="dashboard-message">Cargando datos del panel de control...</div>
      <div v-if="error" class="dashboard-error">{{ error }}</div>

      <!-- ================= TARJETAS ================= -->
      <section class="summary-grid">

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon navy">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ totalPlanesEstrategicosEnUso }}</div>
          <div class="kpi-label">Planes estratégicos en uso</div>
          <div class="kpi-foot">De {{ planesEstrategicos.length }} planes registrados</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon steel">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ totalPlanesAnualesEnUso }}</div>
          <div class="kpi-label">Planes anuales en ejecución</div>
          <div class="kpi-foot">De {{ planesAnuales.length }} planes anuales registrados</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon aqua">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ totalKpiAutorizados }}</div>
          <div class="kpi-label">KPI autorizados</div>
          <div class="kpi-foot">En seguimiento activo</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon ok">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8 12l2.5 2.5L16 9"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ totalKpiFavorables }}</div>
          <div class="kpi-label">KPI favorables</div>
          <div class="kpi-foot">Según su promedio acumulado</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon danger">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ totalKpiRequierenAtencion }}</div>
          <div class="kpi-label">Requieren atención</div>
          <div class="kpi-foot">En riesgo o incumplidos</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon steel">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ totalCierresAutomaticos }}</div>
          <div class="kpi-label">Cierres automáticos</div>
          <div class="kpi-foot">Periodos cerrados en 0.00</div>
        </div>

      </section>

      <!-- ================= GRÁFICOS ================= -->
      <section class="charts-grid">

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Estado de KPI por plan estratégico</h2>
              <div class="desc">Distribución de los KPI autorizados de cada plan en uso, según su estado acumulado</div>
            </div>
          </div>

          <div v-if="!distribucionPorPlan.length" class="dashboard-message">
            No hay planes estratégicos en uso registrados.
          </div>

          <template v-else>
            <div class="plan-rows">
              <div
                v-for="plan in distribucionPorPlan"
                :key="plan.id"
                class="plan-row"
                @click="irAPlanEstrategico(plan.id)"
              >
                <div class="plan-row-head">
                  <span class="plan-row-name" :title="plan.nombre">{{ plan.nombre }}</span>
                  <span class="plan-row-total">{{ plan.total }} KPI</span>
                </div>

                <div v-if="!plan.total" class="plan-row-track plan-row-track--vacio">
                  <span>Sin KPI autorizados</span>
                </div>

                <div v-else class="plan-row-track">
                  <div
                    v-for="segmento in plan.segmentos"
                    :key="segmento.nombre"
                    class="plan-segment"
                    :class="segmento.clase"
                    :style="{ width: `${segmento.porcentaje}%` }"
                    :title="`${segmento.nombre}: ${segmento.cantidad} KPI (${formatearNumero(segmento.porcentaje, { unidad: '%' })})`"
                  ></div>
                </div>
              </div>
            </div>

            <div class="chart-legend">
              <div v-for="categoria in CATEGORIAS_ESTADO" :key="categoria" class="legend-item">
                <span class="legend-dot" :class="claseEstadoNombre(categoria)"></span>{{ categoria }}
              </div>
            </div>
          </template>
        </div>

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Evolución mensual del estado de KPI</h2>
              <div class="desc">Distribución de estados acumulados de los KPI medidos, mes a mes</div>
            </div>
          </div>

          <div v-if="!evolucionPorMes.length" class="dashboard-message">
            No hay mediciones suficientes para mostrar una evolución mensual.
          </div>

          <template v-else>
            <div class="evolucion-scroll">
              <div class="evolucion-columnas">
                <div v-for="mes in evolucionPorMes" :key="mes.clave" class="evolucion-columna">
                  <div class="evolucion-columna-total" :title="`${mes.total} KPI medidos`">{{ mes.total }}</div>

                  <div class="evolucion-columna-track">
                    <div
                      v-for="segmento in mes.segmentos"
                      :key="segmento.nombre"
                      class="evolucion-segmento"
                      :class="segmento.clase"
                      :style="{ height: `${segmento.porcentaje}%` }"
                      :title="`${mes.etiquetaCompleta} · ${segmento.nombre}: ${segmento.cantidad} KPI (${formatearNumero(segmento.porcentaje, { unidad: '%' })})`"
                    ></div>
                  </div>

                  <div class="evolucion-columna-label">{{ mes.etiqueta }}</div>
                </div>
              </div>
            </div>

            <div class="chart-legend">
              <div v-for="categoria in CATEGORIAS_EVOLUCION" :key="categoria" class="legend-item">
                <span class="legend-dot" :class="claseEstadoNombre(categoria)"></span>{{ categoria }}
              </div>
            </div>
          </template>
        </div>

      </section>

      <!-- ================= KPI QUE REQUIEREN ATENCIÓN ================= -->
      <section class="card-panel table-card">
        <div class="panel-head">
          <div>
            <h2>KPI que requieren atención</h2>
            <div class="desc">KPI autorizados en riesgo o incumplidos, según su promedio acumulado</div>
          </div>
        </div>

        <div v-if="!kpiRequierenAtencionLista.length" class="dashboard-message">
          No hay KPI en riesgo o incumplidos actualmente.
        </div>

        <div v-else class="table-scroll">
          <table>
            <colgroup>
              <col style="width: 20%">
              <col style="width: 12%">
              <col style="width: 22%">
              <col style="width: 14%">
              <col style="width: 14%">
              <col style="width: 10%">
              <col style="width: 8%">
            </colgroup>
            <thead>
              <tr>
                <th>KPI</th>
                <th>Plan anual</th>
                <th>Objetivo específico</th>
                <th title="Promedio acumulado">Promedio acumulado</th>
                <th title="Estado acumulado">Estado acumulado</th>
                <th title="Cantidad de mediciones">Mediciones</th>
                <th class="th-acciones" style="text-align: right;">Acción</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="kpi in kpiRequierenAtencionLista" :key="kpi.id">
                <td>
                  <div class="cell-main" :title="kpi.nombre">{{ kpi.nombre }}</div>
                </td>
                <td>
                  <div class="cell-sub" :title="kpi.plan_anual_nombre">{{ kpi.plan_anual_nombre || 'Sin plan anual' }}</div>
                </td>
                <td>
                  <div class="cell-sub" :title="kpi.objetivo_especifico_texto">{{ kpi.objetivo_especifico_texto || 'Sin objetivo' }}</div>
                </td>
                <td>
                  <div class="cell-main">{{ formatearValorUnidad(kpi.promedio_acumulado, kpi.unidad_medida) }}</div>
                </td>
                <td>
                  <span class="badge" :class="claseColorCumplimiento(kpi.estado_acumulado_color)">
                    <span class="badge-dot"></span>
                    {{ textoEstadoCumplimiento(kpi.estado_acumulado_nombre) }}
                  </span>
                </td>
                <td>{{ kpi.cantidad_mediciones }} mediciones</td>
                <td class="td-acciones" style="text-align: right;">
                  <button class="btn-ver" type="button" title="Ver KPI" @click="irAIndicador(kpi.id)">Ver</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="link-see-all" @click="verTodosLosKpi">Ver todos los KPI</div>
      </section>

      <!-- ================= ALERTAS + ÚLTIMAS MEDICIONES ================= -->
      <section class="bottom-grid">

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Alertas pendientes</h2>
              <div class="desc">Alertas KPI que todavía no fueron revisadas</div>
            </div>
          </div>

          <div v-if="!alertasRecientes.length" class="dashboard-message">
            No hay alertas pendientes.
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
              <div class="alert-body">
                <span class="alert-tipo">{{ alerta.tipo_alerta }}</span>
                <div class="alert-text">{{ alerta.mensaje }}</div>
                <div class="alert-time">{{ formatearFecha(alerta.fecha_generacion) }}</div>
              </div>
            </div>
          </template>
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
              <div class="meas-main">
                <div class="meas-top">
                  <span class="meas-name" :title="medicion.indicador_nombre">{{ medicion.indicador_nombre || 'Sin KPI' }}</span>
                  <span class="source-chip" :class="medicion.cierre_automatico ? 'automatico' : 'manual'">
                    {{ tipoRegistroMedicion(medicion) }}
                  </span>
                </div>
                <div class="meas-sub">{{ medicion.periodo_nombre || 'Periodo no definido' }} · {{ formatearFecha(medicion.fecha_registro) }}</div>

                <div class="meas-valores">
                  <span>Resultado: <strong>{{ formatearValorUnidad(medicion.valor_resultado, medicion.unidad_medida) }}</strong></span>
                  <span>Acumulado: <strong>{{ formatearValorUnidad(medicion.promedio_acumulado_hasta_medicion, medicion.unidad_medida) }}</strong></span>
                </div>
              </div>

              <span
                v-if="medicion.estado_acumulado_hasta_medicion_nombre"
                class="badge"
                :class="claseColorCumplimiento(medicion.estado_acumulado_hasta_medicion_color)"
              >
                <span class="badge-dot"></span>
                {{ textoEstadoCumplimiento(medicion.estado_acumulado_hasta_medicion_nombre) }}
              </span>
            </div>
          </template>

          <div class="link-see-all" @click="verTodasLasMediciones">Ver todas las mediciones</div>
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
  }
  .dashboard-content *{ box-sizing:border-box; }
  .dashboard-content{
    font-family:'Montserrat', sans-serif;
    color:var(--navy);
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

  /* ---- tarjetas superiores ---- */
  .summary-grid{
    display:grid;
    grid-template-columns:repeat(3, 1fr);
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
  .kpi-icon.ok{ background:rgba(42,157,143,0.12); color:var(--success); }
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
    font-weight:700;
    color:var(--text-secondary);
    margin-bottom:10px;
  }
  .kpi-foot{
    font-size:11px;
    color:var(--text-muted);
    font-weight:500;
  }

  /* ---- paneles / encabezados ---- */
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
    font-weight:800;
    color:var(--navy);
  }
  .panel-head .desc{
    font-size:11.5px;
    color:var(--text-muted);
    font-weight:500;
    margin-top:3px;
  }

  /* ---- gráficos ---- */
  .charts-grid{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:18px;
    margin-bottom:20px;
    align-items:stretch;
  }

  /* Distribución de KPI por plan estratégico (barra segmentada) */
  .plan-rows{ display:flex; flex-direction:column; gap:14px; max-height:360px; overflow-y:auto; padding-right:4px; }

  .plan-row{ cursor:pointer; }
  .plan-row-head{ display:flex; align-items:baseline; justify-content:space-between; gap:10px; margin-bottom:6px; }
  .plan-row-name{
    font-size:12px; font-weight:800; color:var(--navy);
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:70%;
  }
  .plan-row-total{ font-size:10.5px; font-weight:700; color:var(--text-muted); flex-shrink:0; }

  .plan-row-track{
    display:flex;
    height:18px;
    border-radius:9px;
    overflow:hidden;
    background:var(--bg);
    gap:2px;
  }
  .plan-row-track--vacio{
    align-items:center;
    padding-left:10px;
    font-size:10.5px;
    font-weight:700;
    color:var(--text-muted);
    background:repeating-linear-gradient(45deg, var(--border), var(--border) 4px, transparent 4px, transparent 8px);
  }

  .plan-segment{ height:100%; min-width:3px; }
  .plan-segment.ok{ background:var(--success); }
  .plan-segment.warning{ background:var(--orange); }
  .plan-segment.danger{ background:var(--danger); }
  .plan-segment.neutral{ background:#C7D0D9; }

  /* Evolución mensual (columnas apiladas) */
  .evolucion-scroll{ overflow-x:auto; padding-bottom:4px; }
  .evolucion-columnas{
    display:flex;
    align-items:flex-end;
    gap:10px;
    min-height:220px;
    min-width:min-content;
  }
  .evolucion-columna{
    display:flex;
    flex-direction:column;
    align-items:center;
    width:38px;
    flex-shrink:0;
  }
  .evolucion-columna-total{
    font-size:10px;
    font-weight:800;
    color:var(--text-muted);
    margin-bottom:4px;
  }
  .evolucion-columna-track{
    width:100%;
    height:160px;
    border-radius:6px;
    overflow:hidden;
    display:flex;
    flex-direction:column-reverse;
    background:var(--bg);
  }
  .evolucion-segmento{ width:100%; }
  .evolucion-segmento.ok{ background:var(--success); }
  .evolucion-segmento.warning{ background:var(--orange); }
  .evolucion-segmento.danger{ background:var(--danger); }
  .evolucion-segmento.neutral{ background:#C7D0D9; }
  .evolucion-columna-label{
    font-size:10px;
    font-weight:700;
    color:var(--text-muted);
    margin-top:6px;
    white-space:nowrap;
  }

  .chart-legend{ display:flex; gap:16px; flex-wrap:wrap; margin-top:16px; padding-top:14px; border-top:1px solid var(--border); }
  .legend-item{ display:flex; align-items:center; gap:6px; font-size:11px; font-weight:700; color:var(--text-secondary); }
  .legend-dot{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }
  .legend-dot.ok{ background:var(--success); }
  .legend-dot.warning{ background:var(--orange); }
  .legend-dot.danger{ background:var(--danger); }
  .legend-dot.neutral{ background:#C7D0D9; }

  /* ---- tabla ---- */
  .table-card{ margin-bottom:20px; }
  .table-scroll{ overflow-x:auto; }
  table{ width:100%; border-collapse:collapse; min-width:760px; table-layout:fixed; }
  thead th{
    text-align:left;
    font-size:10.5px;
    font-weight:800;
    letter-spacing:0.5px;
    text-transform:uppercase;
    color:var(--text-muted);
    padding:0 12px 10px;
    border-bottom:1px solid var(--border);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
  }
  .th-acciones, .td-acciones{ white-space:nowrap; }
  tbody td{
    overflow:hidden;
    padding:13px 12px;
    font-size:13px;
    color:var(--navy);
    border-bottom:1px solid #F1F4F7;
    vertical-align:middle;
  }
  tbody tr:last-child td{ border-bottom:none; }
  tbody tr{ transition:background .12s ease; }
  tbody tr:hover{ background:#FAFCFD; }

  .cell-main{ font-weight:700; font-size:13px; color:var(--navy); max-width:220px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .cell-sub{ font-size:12px; color:var(--text-secondary); font-weight:500; max-width:220px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

  .btn-ver{
    height:28px;
    padding:0 14px;
    border-radius:8px;
    border:1px solid var(--border);
    background:var(--white);
    color:var(--steel);
    font-family:inherit;
    font-size:11.5px;
    font-weight:800;
    cursor:pointer;
    transition:background .15s ease, border-color .15s ease;
  }
  .btn-ver:hover{ background:var(--aqua-soft); border-color:var(--aqua); }

  .badge{
    display:inline-flex;
    align-items:center;
    gap:5px;
    font-size:11px;
    font-weight:800;
    padding:4px 10px;
    border-radius:20px;
    white-space:nowrap;
    max-width:100%;
  }
  .badge.ok{ background:rgba(42,157,143,0.12); color:var(--success); }
  .badge.warning{ background:rgba(244,162,97,0.16); color:#B9701E; }
  .badge.danger{ background:rgba(231,111,81,0.12); color:var(--danger); }
  .badge.neutral{ background:rgba(154,168,184,0.16); color:var(--text-muted); }
  .badge-dot{ width:6px; height:6px; border-radius:50%; background:currentColor; flex-shrink:0; }

  /* ---- alertas / mediciones ---- */
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
    cursor:pointer;
  }
  .alert-item:last-child{ border-bottom:none; padding-bottom:0; }
  .alert-icon{
    width:32px; height:32px; border-radius:9px;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0;
  }
  .alert-icon.danger{ background:rgba(231,111,81,0.12); color:var(--danger); }
  .alert-icon.warning{ background:rgba(244,162,97,0.16); color:#B9701E; }
  .alert-icon.neutral{ background:rgba(69,123,157,0.10); color:var(--steel); }
  .alert-body{ min-width:0; }
  .alert-tipo{
    display:block;
    font-size:10px;
    font-weight:800;
    letter-spacing:0.3px;
    text-transform:uppercase;
    color:var(--text-muted);
    margin-bottom:2px;
  }
  .alert-text{ font-size:12.5px; font-weight:600; color:var(--navy); line-height:1.4; }
  .alert-time{ font-size:11px; color:var(--text-muted); font-weight:500; margin-top:3px; }

  .meas-item{
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:12px;
    padding:12px 4px;
    border-bottom:1px solid #F1F4F7;
    cursor:pointer;
  }
  .meas-item:last-child{ border-bottom:none; padding-bottom:0; }
  .meas-main{ min-width:0; flex:1; }
  .meas-top{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .meas-name{ font-size:12.5px; font-weight:800; color:var(--navy); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:220px; }
  .meas-sub{ font-size:11px; color:var(--text-muted); font-weight:500; margin-top:2px; }
  .meas-valores{ display:flex; gap:14px; flex-wrap:wrap; margin-top:6px; font-size:11.5px; color:var(--text-secondary); font-weight:600; }
  .meas-valores strong{ color:var(--navy); font-weight:800; }

  .source-chip{
    display:inline-flex;
    align-items:center;
    padding:3px 8px;
    border-radius:8px;
    font-size:10px;
    font-weight:800;
    flex-shrink:0;
  }
  .source-chip.manual{ background:rgba(69,123,157,0.12); color:var(--steel); }
  .source-chip.automatico{ background:rgba(244,162,97,0.16); color:#B9701E; }

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
    .charts-grid{ grid-template-columns:1fr; }
  }
  @media (max-width:900px){
    .summary-grid{ grid-template-columns:repeat(2, 1fr); }
    .bottom-grid{ grid-template-columns:1fr; }
  }
  @media (max-width:640px){
    .summary-grid{ grid-template-columns:1fr; }
    .plan-row-name{ max-width:55%; }
  }
</style>
