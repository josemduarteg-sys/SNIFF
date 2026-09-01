<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import api from '../services/api'

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
  return estrategias.value.filter((item) => item.estado === 'activa' || item.estado === true).length
})

const objetivosRegistrados = computed(() => objetivos.value.length)

const indicadoresActivos = computed(() => {
  return indicadores.value.filter((item) => item.estado === 'autorizado').length
})

const alertasPendientes = computed(() => {
  return alertas.value.filter((item) => item.estado_alerta === 'pendiente').length
})

const cumplimientoGeneral = computed(() => {
  if (!mediciones.value.length) return 0

  const total = mediciones.value.reduce((acumulado, medicion) => {
    return acumulado + Number(medicion.porcentaje_cumplimiento || 0)
  }, 0)

  return Math.round(total / mediciones.value.length)
})

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

function formatearPorcentaje(valor) {
  const numero = Number(valor)

  if (Number.isNaN(numero)) return '0%'

  return `${Math.round(numero)}%`
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

function claseCumplimiento(porcentaje) {
  const valor = Number(porcentaje)

  if (valor >= 85) return 'ok'
  if (valor >= 70) return 'warning'
  return 'critical'
}

function colorPorPorcentaje(porcentaje) {
  const valor = Number(porcentaje)

  if (valor >= 85) return 'var(--success)'
  if (valor >= 70) return 'var(--orange)'
  return 'var(--danger)'
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

const cumplimientoPorEstrategia = computed(() => {
  const mapaUltimaMedicion = obtenerUltimaMedicionPorIndicador()

  return estrategias.value
    .map((estrategia) => {
      const idsObjetivos = objetivos.value
        .filter((objetivo) => Number(objetivo.estrategia) === Number(estrategia.id))
        .map((objetivo) => objetivo.id)

      const porcentajes = indicadores.value
        .filter((indicador) => idsObjetivos.includes(indicador.objetivo))
        .map((indicador) => mapaUltimaMedicion.get(indicador.id))
        .filter(Boolean)
        .map((medicion) => Number(medicion.porcentaje_cumplimiento))
        .filter((valor) => !Number.isNaN(valor))

      if (!porcentajes.length) {
        return null
      }

      const promedio = porcentajes.reduce((acumulado, valor) => acumulado + valor, 0) / porcentajes.length

      return {
        id: estrategia.id,
        nombre: estrategia.nombre,
        porcentaje: Math.round(promedio),
      }
    })
    .filter(Boolean)
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
      promedio: Math.round(valores.reduce((acumulado, valor) => acumulado + valor, 0) / valores.length),
    }))
    .sort((a, b) => a.clave.localeCompare(b.clave))
    .slice(-6)
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
      api.get('estrategias/'),
      api.get('objetivos/'),
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
    errorDashboard.value = 'No se pudieron cargar los datos del dashboard.'
  } finally {
    cargandoDashboard.value = false
  }
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
    :usuario="usuario"
    titulo="Dashboard Principal"
    subtitulo="Resumen general del cumplimiento estratégico"
    breadcrumb-actual="Dashboard"
    @logout="cerrarSesion"
  >
    <template #actions>
      <div class="period-select">
        <svg class="cal" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        Datos actualizados del sistema
      </div>
    </template>

    <div class="dashboard-content">

      <div v-if="cargandoDashboard" class="dashboard-message">Cargando datos del dashboard...</div>
      <div v-if="errorDashboard" class="dashboard-error">{{ errorDashboard }}</div>

      <!-- ================= SUMMARY CARDS ================= -->
      <section class="summary-grid">

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon navy">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            </div>
          </div>
          <div class="kpi-value">{{ cumplimientoGeneral }}%</div>
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
          <div class="kpi-value">{{ alertasPendientes }}</div>
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
            Aún no hay mediciones suficientes para calcular cumplimiento por estrategia.
          </div>

          <template v-else>
            <div class="bar-chart">
              <div
                v-for="item in cumplimientoPorEstrategia"
                :key="item.id"
                class="bar-col"
              >
                <div class="bar-val">{{ formatearPorcentaje(item.porcentaje) }}</div>
                <div
                  class="bar-shape"
                  :style="{ height: `${Math.min(item.porcentaje, 100) * 1.6}px`, background: colorPorPorcentaje(item.porcentaje) }"
                ></div>
                <div class="bar-name">{{ item.nombre }}</div>
              </div>
            </div>

            <div class="chart-legend">
              <div class="legend-item"><span class="legend-dot" style="background:var(--success);"></span>En meta (≥85%)</div>
              <div class="legend-item"><span class="legend-dot" style="background:var(--orange);"></span>En riesgo (70–84%)</div>
              <div class="legend-item"><span class="legend-dot" style="background:var(--danger);"></span>Crítico (&lt;70%)</div>
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

          <div v-else class="bar-chart">
            <div
              v-for="item in evolucionMediciones"
              :key="item.clave"
              class="bar-col"
            >
              <div class="bar-val">{{ formatearPorcentaje(item.promedio) }}</div>
              <div
                class="bar-shape"
                :style="{ height: `${Math.min(item.promedio, 100) * 1.6}px`, background: colorPorPorcentaje(item.promedio) }"
              ></div>
              <div class="bar-name">{{ item.etiqueta }}</div>
            </div>
          </div>

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
              <th>Actual</th>
              <th>Cumplimiento</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="medicion in indicadoresMenorCumplimiento" :key="medicion.id">
              <td>
                <div class="cell-main">{{ obtenerNombreIndicador(medicion) }}</div>
                <div class="cell-sub">{{ obtenerObjetivoDeIndicador(medicion.indicador) || 'Sin objetivo' }}</div>
              </td>
              <td>{{ medicion.valor_meta ?? 'Sin meta' }}</td>
              <td>{{ medicion.valor_resultado }}</td>
              <td>
                <div class="mini-progress">
                  <div class="track">
                    <div
                      class="fill"
                      :style="{ width: `${Math.min(Number(medicion.porcentaje_cumplimiento) || 0, 100)}%`, background: colorPorPorcentaje(medicion.porcentaje_cumplimiento) }"
                    ></div>
                  </div>
                  <span class="pct">{{ formatearPorcentaje(medicion.porcentaje_cumplimiento) }}</span>
                </div>
              </td>
              <td>
                <span class="badge" :class="claseCumplimiento(medicion.porcentaje_cumplimiento)">
                  <span class="badge-dot"></span>
                  {{ medicion.estado_cumplimiento_nombre || 'Sin estado' }}
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
              class="alert-item"
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

          <div class="link-see-all">Ver todas las alertas</div>
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
              class="meas-item"
            >
              <div class="meas-left">
                <div class="meas-avatar">{{ obtenerIniciales(medicion.registrado_por_username) }}</div>
                <div>
                  <div class="meas-name">{{ obtenerNombreIndicador(medicion) }}</div>
                  <div class="meas-sub">{{ medicion.registrado_por_username || 'Sistema' }} · {{ formatearFecha(medicion.fecha_registro) }}</div>
                </div>
              </div>
              <div class="meas-value">{{ medicion.valor_resultado }}</div>
            </div>
          </template>

          <div class="link-see-all">Ver todas las mediciones</div>
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

  .bar-chart{ display:flex; align-items:flex-end; gap:22px; height:210px; padding-top:6px; }
  .bar-col{ flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; }
  .bar-val{ font-size:12px; font-weight:700; color:var(--navy); margin-bottom:6px; }
  .bar-shape{ width:100%; max-width:38px; border-radius:8px 8px 4px 4px; }
  .bar-name{ font-size:10.5px; font-weight:600; color:var(--text-muted); margin-top:10px; text-align:center; line-height:1.3; }

  .chart-legend{ display:flex; gap:16px; margin-top:16px; flex-wrap:wrap; }
  .legend-item{ display:flex; align-items:center; gap:6px; font-size:11px; font-weight:600; color:var(--text-secondary); }
  .legend-dot{ width:8px; height:8px; border-radius:50%; }

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

  .cell-main{ font-weight:700; font-size:13px; color:var(--navy); }
  .cell-sub{ font-size:11.5px; color:var(--text-muted); font-weight:500; margin-top:2px; }

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
  .badge.critical{ background:rgba(231,111,81,0.12); color:var(--danger); }
  .badge.warning{ background:rgba(244,162,97,0.16); color:#B9701E; }
  .badge.ok{ background:rgba(42,157,143,0.12); color:var(--success); }
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
  }


  .topbar-profile {
    border: none;
    background: transparent;
    font-family: inherit;
  }

</style>
