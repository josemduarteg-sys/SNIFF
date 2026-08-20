<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import {
  anularIndicador,
  autorizarIndicador,
  obtenerDatosFormularioIndicador,
  obtenerIndicadoresKpi,
} from '../services/indicadorService'

defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const indicadores = ref([])
const objetivos = ref([])
const frecuencias = ref([])
const tiposCalculo = ref([])
const fuentesDato = ref([])

const busqueda = ref('')
const objetivoSeleccionado = ref('')
const frecuenciaSeleccionada = ref('')
const fuenteSeleccionada = ref('')
const estadoSeleccionado = ref('')

const cargando = ref(false)
const procesandoId = ref(null)
const error = ref('')
const mensaje = ref('')

async function cargarDatos() {
  cargando.value = true
  error.value = ''
  mensaje.value = ''

  try {
    const [indicadoresData, datosFormulario] = await Promise.all([
      obtenerIndicadoresKpi(),
      obtenerDatosFormularioIndicador(),
    ])

    indicadores.value = indicadoresData
    objetivos.value = datosFormulario.objetivos
    frecuencias.value = datosFormulario.frecuencias
    tiposCalculo.value = datosFormulario.tiposCalculo
    fuentesDato.value = datosFormulario.fuentesDato
  } catch (e) {
    error.value = 'No se pudieron cargar los indicadores KPI.'
  } finally {
    cargando.value = false
  }
}

const indicadoresFiltrados = computed(() => {
  const texto = busqueda.value.trim().toLowerCase()

  return indicadores.value.filter((indicador) => {
    const coincideBusqueda =
      !texto ||
      indicador.nombre?.toLowerCase().includes(texto) ||
      indicador.descripcion?.toLowerCase().includes(texto) ||
      indicador.objetivo_nombre?.toLowerCase().includes(texto) ||
      indicador.frecuencia_nombre?.toLowerCase().includes(texto) ||
      indicador.tipo_calculo_nombre?.toLowerCase().includes(texto) ||
      indicador.fuente_dato_nombre?.toLowerCase().includes(texto) ||
      indicador.estado?.toLowerCase().includes(texto)

    const coincideObjetivo =
      !objetivoSeleccionado.value ||
      Number(indicador.objetivo) === Number(objetivoSeleccionado.value)

    const coincideFrecuencia =
      !frecuenciaSeleccionada.value ||
      Number(indicador.frecuencia) === Number(frecuenciaSeleccionada.value)

    const coincideFuente =
      !fuenteSeleccionada.value ||
      Number(indicador.fuente_dato) === Number(fuenteSeleccionada.value)

    const coincideEstado =
      !estadoSeleccionado.value ||
      indicador.estado === estadoSeleccionado.value

    return (
      coincideBusqueda &&
      coincideObjetivo &&
      coincideFrecuencia &&
      coincideFuente &&
      coincideEstado
    )
  })
})

const indicadoresBorrador = computed(() => {
  return indicadores.value.filter((indicador) => indicador.estado === 'borrador').length
})

const indicadoresAutorizados = computed(() => {
  return indicadores.value.filter((indicador) => indicador.estado === 'autorizado').length
})

const indicadoresAnulados = computed(() => {
  return indicadores.value.filter((indicador) => indicador.estado === 'anulado').length
})

const indicadoresInactivos = computed(() => {
  return indicadores.value.filter((indicador) => indicador.estado === 'inactivo').length
})

function textoEstado(estado) {
  const estados = {
    borrador: 'Borrador',
    autorizado: 'Autorizado',
    inactivo: 'Inactivo',
    anulado: 'Anulado',
  }

  return estados[estado] || estado || 'Sin estado'
}

function estadoClase(estado) {
  const clases = {
    borrador: 'warning',
    autorizado: 'ok',
    inactivo: 'neutral',
    anulado: 'danger',
  }

  return clases[estado] || 'neutral'
}

function fuenteClase(fuente) {
  const nombre = fuente?.toLowerCase() || ''

  if (nombre.includes('manual')) return 'manual'
  if (nombre.includes('csv')) return 'csv'
  if (nombre.includes('warehouse') || nombre.includes('data')) return 'dw'

  return 'neutral'
}

function formatearFecha(fecha) {
  if (!fecha) {
    return 'No definida'
  }

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) {
    return fecha
  }

  return `${dia}/${mes}/${anio}`
}

function formatearNumero(valor) {
  if (valor === null || valor === undefined || valor === '') {
    return '-'
  }

  const numero = Number(valor)

  if (Number.isNaN(numero)) {
    return valor
  }

  return numero.toLocaleString('es-GT', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })
}

function puedeAutorizar(indicador) {
  return indicador.estado === 'borrador'
}

function puedeAnular(indicador) {
  return indicador.estado !== 'anulado'
}

function puedeEditar(indicador) {
  return indicador.puede_modificarse === true || indicador.estado === 'borrador'
}

async function manejarAutorizar(indicador) {
  if (!puedeAutorizar(indicador)) {
    return
  }

  procesandoId.value = indicador.id
  error.value = ''
  mensaje.value = ''

  try {
    await autorizarIndicador(indicador.id)
    mensaje.value = 'KPI autorizado correctamente.'
    await cargarDatos()
  } catch (e) {
    error.value =
      e.response?.data?.detail ||
      'No se pudo autorizar el KPI. Verificá que tenga meta y fechas de vigencia.'
  } finally {
    procesandoId.value = null
  }
}

async function manejarAnular(indicador) {
  if (!puedeAnular(indicador)) {
    return
  }

  const confirmar = window.confirm(
    `¿Seguro que querés anular el KPI "${indicador.nombre}"? Esta acción no elimina el registro, solo lo marca como anulado.`
  )

  if (!confirmar) {
    return
  }

  procesandoId.value = indicador.id
  error.value = ''
  mensaje.value = ''

  try {
    await anularIndicador(indicador.id)
    mensaje.value = 'KPI anulado correctamente.'
    await cargarDatos()
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudo anular el KPI.'
  } finally {
    procesandoId.value = null
  }
}

function manejarEditar(indicador) {
  if (!puedeEditar(indicador)) {
    mensaje.value = ''
    error.value = 'Este KPI ya está autorizado y no permite modificar sus datos principales.'
    return
  }

  mensaje.value = ''
  error.value = 'La edición del KPI se implementará en el formulario de KPI.'
}

function cerrarSesion() {
  emit('logout')
}

onMounted(() => {
  cargarDatos()
})
</script>

<template>
  <AppLayout
    :usuario="usuario"
    titulo="Gestión de Indicadores KPI"
    subtitulo="Administra indicadores, metas, vigencia y estado de autorización."
    breadcrumb-actual="Indicadores KPI"
    @logout="cerrarSesion"
  >
    <template #actions>
      <button class="btn-primary-page" type="button">
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.4"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>

        Nuevo KPI
      </button>
    </template>

    <section class="summary-grid">
      <article class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon navy">
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ indicadores.length }}</div>
        <div class="kpi-label">KPI registrados</div>
        <div class="kpi-foot">Total creado en el sistema</div>
      </article>

      <article class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon orange">
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 8v5" />
              <path d="M12 17h.01" />
              <circle cx="12" cy="12" r="9" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ indicadoresBorrador }}</div>
        <div class="kpi-label">En borrador</div>
        <div class="kpi-foot">Pueden modificarse antes de autorizar</div>
      </article>

      <article class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon aqua">
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M8 12l2.5 2.5L16 9" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ indicadoresAutorizados }}</div>
        <div class="kpi-label">Autorizados</div>
        <div class="kpi-foot">Listos para seguimiento mensual</div>
      </article>

      <article class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon steel">
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M4 4v16h16" />
              <path d="M7 16l4-4 3 3 5-7" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ indicadoresInactivos + indicadoresAnulados }}</div>
        <div class="kpi-label">Inactivos/anulados</div>
        <div class="kpi-foot">Conservados para historial</div>
      </article>
    </section>

    <div v-if="mensaje" class="alert success">
      {{ mensaje }}
    </div>

    <div v-if="error" class="alert error">
      {{ error }}
    </div>

    <div class="toolbar">
      <div class="toolbar-search">
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>

        <input
          v-model="busqueda"
          type="text"
          placeholder="Buscar KPI..."
        />
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">Objetivo:</span>

        <select v-model="objetivoSeleccionado">
          <option value="">Todos</option>

          <option
            v-for="objetivo in objetivos"
            :key="objetivo.id"
            :value="objetivo.id"
          >
            {{ objetivo.nombre }}
          </option>
        </select>
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">Frecuencia:</span>

        <select v-model="frecuenciaSeleccionada">
          <option value="">Todas</option>

          <option
            v-for="frecuencia in frecuencias"
            :key="frecuencia.id"
            :value="frecuencia.id"
          >
            {{ frecuencia.nombre }}
          </option>
        </select>
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">Fuente:</span>

        <select v-model="fuenteSeleccionada">
          <option value="">Todas</option>

          <option
            v-for="fuente in fuentesDato"
            :key="fuente.id"
            :value="fuente.id"
          >
            {{ fuente.nombre }}
          </option>
        </select>
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">Estado:</span>

        <select v-model="estadoSeleccionado">
          <option value="">Todos</option>
          <option value="borrador">Borrador</option>
          <option value="autorizado">Autorizado</option>
          <option value="inactivo">Inactivo</option>
          <option value="anulado">Anulado</option>
        </select>
      </div>

      <div class="toolbar-count">
        {{ indicadoresFiltrados.length }} KPI
      </div>
    </div>

    <section class="card-panel table-card">
      <div v-if="cargando" class="message">
        Cargando indicadores KPI...
      </div>

      <div v-else-if="!indicadoresFiltrados.length" class="empty-state">
        No hay indicadores KPI para mostrar.
      </div>

      <table v-else>
        <thead>
          <tr>
            <th>Indicador KPI</th>
            <th>Objetivo asociado</th>
            <th>Meta</th>
            <th>Vigencia</th>
            <th>Frecuencia</th>
            <th>Fuente</th>
            <th>Estado</th>
            <th style="text-align: right;">Acciones</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="indicador in indicadoresFiltrados"
            :key="indicador.id"
          >
            <td>
              <div class="cell-main">
                {{ indicador.nombre }}
              </div>

              <div class="cell-sub">
                {{ indicador.descripcion || 'Sin descripción' }}
              </div>

              <div class="cell-extra">
                Tipo: {{ indicador.tipo_calculo_nombre || 'Sin tipo' }} · Unidad:
                {{ indicador.unidad_medida || '-' }}
              </div>
            </td>

            <td>
              <span class="code-chip">
                {{ indicador.objetivo_nombre || 'Sin objetivo' }}
              </span>
            </td>

            <td>
              <div class="meta-value">
                {{ formatearNumero(indicador.valor_meta) }}
              </div>
              <div class="cell-sub">
                {{ indicador.unidad_medida || 'unidad' }}
              </div>
            </td>

            <td>
              <div class="date-range">
                <span>{{ formatearFecha(indicador.fecha_inicio) }}</span>
                <small>al</small>
                <span>{{ formatearFecha(indicador.fecha_fin) }}</span>
              </div>
            </td>

            <td>
              {{ indicador.frecuencia_nombre || 'Sin frecuencia' }}
            </td>

            <td>
              <span
                class="source-chip"
                :class="fuenteClase(indicador.fuente_dato_nombre)"
              >
                {{ indicador.fuente_dato_nombre || 'Sin fuente' }}
              </span>
            </td>

            <td>
              <span class="badge" :class="estadoClase(indicador.estado)">
                <span class="badge-dot"></span>
                {{ textoEstado(indicador.estado) }}
              </span>

              <div v-if="indicador.autorizado_por_username" class="cell-sub">
                Por {{ indicador.autorizado_por_username }}
              </div>
            </td>

            <td>
              <div class="actions-cell">
                <button
                  class="action-text-btn ok"
                  type="button"
                  title="Autorizar KPI"
                  :disabled="!puedeAutorizar(indicador) || procesandoId === indicador.id"
                  @click="manejarAutorizar(indicador)"
                >
                  Autorizar
                </button>

                <button
                  class="action-icon-btn"
                  type="button"
                  title="Editar"
                  :class="{ disabled: !puedeEditar(indicador) }"
                  :disabled="procesandoId === indicador.id"
                  @click="manejarEditar(indicador)"
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" />
                  </svg>
                </button>

                <button
                  class="action-icon-btn danger"
                  type="button"
                  title="Anular"
                  :disabled="!puedeAnular(indicador) || procesandoId === indicador.id"
                  @click="manejarAnular(indicador)"
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <circle cx="12" cy="12" r="9" />
                    <line x1="9" y1="9" x2="15" y2="15" />
                    <line x1="15" y1="9" x2="9" y2="15" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="table-footer">
        <div class="showing">
          Mostrando {{ indicadoresFiltrados.length }} de {{ indicadores.length }} KPI
        </div>
      </div>
    </section>
  </AppLayout>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.kpi-card,
.card-panel {
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 14px;
  box-shadow: 0 2px 10px rgba(29, 53, 87, 0.05), 0 1px 2px rgba(29, 53, 87, 0.04);
}

.kpi-card {
  padding: 18px 18px 16px;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.kpi-card:hover {
  box-shadow: 0 10px 26px rgba(29, 53, 87, 0.10);
  transform: translateY(-2px);
}

.kpi-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.kpi-icon {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-icon.navy {
  background: rgba(29, 53, 87, 0.08);
  color: #1d3557;
}

.kpi-icon.steel {
  background: rgba(69, 123, 157, 0.10);
  color: #457b9d;
}

.kpi-icon.aqua {
  background: #eaf5f5;
  color: #457b9d;
}

.kpi-icon.orange {
  background: rgba(244, 162, 97, 0.14);
  color: #f4a261;
}

.kpi-icon svg {
  stroke: currentColor;
}

.kpi-value {
  font-size: 26px;
  font-weight: 800;
  color: #1d3557;
  letter-spacing: -0.4px;
  line-height: 1;
  margin-bottom: 6px;
}

.kpi-label {
  font-size: 12.5px;
  font-weight: 700;
  color: #5e6e82;
  margin-bottom: 10px;
}

.kpi-foot {
  font-size: 11px;
  color: #9aa8b8;
  font-weight: 500;
}

.btn-primary-page {
  height: 40px;
  padding: 0 15px;
  border: none;
  border-radius: 10px;
  background: #1d3557;
  color: #ffffff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 8px 18px rgba(29, 53, 87, 0.14);
}

.btn-primary-page:hover {
  background: #152840;
}

.alert {
  padding: 13px 15px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 750;
  margin-bottom: 18px;
}

.alert.success {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.alert.error {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.toolbar-search {
  flex: 1;
  min-width: 240px;
  max-width: 360px;
  height: 40px;
  border-radius: 10px;
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 12px;
}

.toolbar-search svg {
  stroke: #9aa8b8;
}

.toolbar-search input {
  border: none;
  outline: none;
  width: 100%;
  background: transparent;
  font-family: inherit;
  color: #1d3557;
  font-size: 13px;
}

.toolbar-search input::placeholder {
  color: #9aa8b8;
}

.toolbar-filter {
  height: 40px;
  border-radius: 10px;
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  color: #1d3557;
  font-size: 13px;
  font-weight: 700;
}

.toolbar-filter select {
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  color: #1d3557;
  font-weight: 700;
  max-width: 190px;
}

.filter-label {
  color: #9aa8b8;
  font-size: 12px;
}

.toolbar-count {
  height: 40px;
  border-radius: 10px;
  background: #eaf5f5;
  color: #457b9d;
  padding: 0 13px;
  display: flex;
  align-items: center;
  font-size: 12.5px;
  font-weight: 800;
}

.card-panel {
  padding: 20px 22px 18px;
}

.table-card {
  margin-bottom: 20px;
}

.message,
.empty-state {
  padding: 16px;
  border-radius: 12px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 13px;
  font-weight: 700;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead th {
  text-align: left;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: #9aa8b8;
  padding: 0 12px 10px;
  border-bottom: 1px solid #e4eaef;
}

tbody td {
  padding: 13px 12px;
  font-size: 13px;
  color: #1d3557;
  border-bottom: 1px solid #f1f4f7;
  vertical-align: middle;
}

tbody tr:last-child td {
  border-bottom: none;
}

tbody tr {
  transition: background 0.12s ease;
}

tbody tr:hover {
  background: #fafcfd;
}

.cell-main {
  font-weight: 800;
  font-size: 13px;
  color: #1d3557;
}

.cell-sub {
  font-size: 11.5px;
  color: #9aa8b8;
  font-weight: 500;
  margin-top: 3px;
  max-width: 460px;
}

.cell-extra {
  font-size: 11.5px;
  color: #5e6e82;
  font-weight: 600;
  margin-top: 5px;
}

.meta-value {
  font-weight: 800;
  color: #1d3557;
}

.date-range {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: #1d3557;
  font-size: 12px;
  font-weight: 700;
}

.date-range small {
  color: #9aa8b8;
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
}

.code-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 9px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 11.5px;
  font-weight: 800;
  max-width: 260px;
}

.source-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 9px;
  font-size: 11.5px;
  font-weight: 800;
}

.source-chip.manual {
  background: rgba(69, 123, 157, 0.12);
  color: #457b9d;
}

.source-chip.csv {
  background: rgba(244, 162, 97, 0.16);
  color: #b9701e;
}

.source-chip.dw {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.source-chip.neutral {
  background: rgba(154, 168, 184, 0.16);
  color: #5e6e82;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 20px;
  white-space: nowrap;
}

.badge.ok {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.badge.warning {
  background: rgba(244, 162, 97, 0.16);
  color: #b9701e;
}

.badge.danger {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

.badge.neutral {
  background: rgba(154, 168, 184, 0.16);
  color: #5e6e82;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.actions-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.action-text-btn {
  min-width: 78px;
  height: 30px;
  border-radius: 9px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.action-text-btn.ok {
  color: #2a9d8f;
}

.action-text-btn.ok:hover:not(:disabled) {
  background: rgba(42, 157, 143, 0.12);
  border-color: rgba(42, 157, 143, 0.25);
}

.action-icon-btn {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.action-icon-btn svg {
  stroke: currentColor;
}

.action-icon-btn:hover:not(:disabled) {
  background: #eaf5f5;
  color: #457b9d;
  border-color: #a8dadc;
}

.action-icon-btn.danger:hover:not(:disabled) {
  background: rgba(231, 111, 81, 0.10);
  color: #e76f51;
  border-color: rgba(231, 111, 81, 0.25);
}

.action-icon-btn.disabled,
.action-icon-btn:disabled,
.action-text-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 14px;
  border-top: 1px solid #f7f1f5;
  margin-top: 4px;
}

.showing {
  font-size: 12px;
  color: #9aa8b8;
  font-weight: 600;
}

@media (max-width: 1200px) {
  table {
    display: block;
    overflow-x: auto;
  }
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .toolbar {
    align-items: stretch;
  }

  .toolbar-search,
  .toolbar-filter,
  .toolbar-count {
    width: 100%;
    max-width: none;
  }
}
</style>
