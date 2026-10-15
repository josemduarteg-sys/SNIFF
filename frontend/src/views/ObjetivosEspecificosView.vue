<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import ObjetivoEspecificoForm from '../components/objetivos-especificos/ObjetivoEspecificoForm.vue'
import {
  actualizarObjetivoEspecifico,
  crearObjetivoEspecifico,
  obtenerDatosFormularioObjetivoEspecifico,
  obtenerObjetivosEspecificos,
  obtenerPlanesAnualesParaObjetivoEspecifico,
} from '../services/objetivoEspecificoService'
import { esAdministradorPlanificacion, puedeGestionarObjetivosEspecificos } from '../utils/permisos'
import { useResaltado } from '../composables/useResaltado'
import { usePaginacion } from '../composables/usePaginacion'
import Paginacion from '../components/common/Paginacion.vue'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const puedeGestionar = computed(() => puedeGestionarObjetivosEspecificos(props.usuario))
const esAdmin = computed(() => esAdministradorPlanificacion(props.usuario))

const emit = defineEmits(['logout'])

const route = useRoute()
const { idResaltado, aplicarResaltadoDesdeRuta } = useResaltado(route)

const objetivos = ref([])
const planesAnualesFormulario = ref([])
const objetivosGeneralesFormulario = ref([])
const planesAnualesFiltro = ref([])
const busqueda = ref('')
const planAnualSeleccionadoFiltro = ref('')
const cargando = ref(false)
const error = ref('')
const mensaje = ref('')

const modalObjetivoAbierto = ref(false)
const modalDetalleAbierto = ref(false)
const objetivoSeleccionado = ref(null)
const guardandoObjetivo = ref(false)
const errorModalObjetivo = ref('')

async function cargarDatos() {
  cargando.value = true
  error.value = ''

  try {
    const [objetivosData, datosFormulario, planesTodos] = await Promise.all([
      obtenerObjetivosEspecificos(),
      obtenerDatosFormularioObjetivoEspecifico(),
      obtenerPlanesAnualesParaObjetivoEspecifico(),
    ])

    objetivos.value = objetivosData
    planesAnualesFormulario.value = datosFormulario.planesAnuales
    objetivosGeneralesFormulario.value = datosFormulario.objetivosGenerales
    planesAnualesFiltro.value = planesTodos
  } catch (e) {
    error.value = 'No se pudieron cargar los objetivos específicos.'
  } finally {
    cargando.value = false
  }
}

const objetivosFiltrados = computed(() => {
  const texto = busqueda.value.trim().toLowerCase()

  return objetivos.value.filter((objetivo) => {
    const coincideBusqueda =
      !texto ||
      objetivo.texto_objetivo?.toLowerCase().includes(texto) ||
      objetivo.objetivo_general_texto?.toLowerCase().includes(texto)

    const coincidePlanAnual =
      !planAnualSeleccionadoFiltro.value ||
      Number(objetivo.plan_anual) === Number(planAnualSeleccionadoFiltro.value)

    return coincideBusqueda && coincidePlanAnual
  })
})

const hayFiltrosActivos = computed(() => {
  return busqueda.value.trim() !== '' || planAnualSeleccionadoFiltro.value !== ''
})

function limpiarFiltros() {
  busqueda.value = ''
  planAnualSeleccionadoFiltro.value = ''
}

const {
  paginaActual,
  porPagina,
  totalResultados,
  totalPaginas,
  elementosVisibles: objetivosPagina,
  rangoInicio,
  rangoFin,
  irAPagina,
} = usePaginacion(objetivosFiltrados)

function cambiarPorPagina(valor) {
  porPagina.value = valor
}

function formatearFecha(fecha) {
  if (!fecha) {
    return 'No definida'
  }

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

function inicialesUsuario(nombre) {
  if (!nombre) {
    return 'US'
  }

  return nombre
    .split(' ')
    .map((parte) => parte.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

function bloqueado(objetivo) {
  return objetivo.plan_anual_estado === 'cerrado' || objetivo.plan_estrategico_estado === 'cerrado'
}

function puedeEditar(objetivo) {
  return puedeGestionar.value && !bloqueado(objetivo)
}

function abrirNuevoObjetivo() {
  objetivoSeleccionado.value = null
  modalObjetivoAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalObjetivo.value = ''
}

function abrirEditarObjetivo(objetivo) {
  if (!puedeEditar(objetivo)) {
    return
  }

  objetivoSeleccionado.value = objetivo
  modalObjetivoAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalObjetivo.value = ''
}

function abrirDetalleObjetivo(objetivo) {
  objetivoSeleccionado.value = objetivo
  modalDetalleAbierto.value = true
}

function cerrarModalObjetivo() {
  modalObjetivoAbierto.value = false
  objetivoSeleccionado.value = null
  guardandoObjetivo.value = false
  errorModalObjetivo.value = ''
}

function cerrarModalDetalle() {
  modalDetalleAbierto.value = false
  objetivoSeleccionado.value = null
}

function obtenerMensajeError(e, mensajeDefault) {
  const data = e.response?.data

  if (data?.detail) {
    return data.detail
  }

  if (typeof data === 'object' && data !== null) {
    const primerCampo = Object.keys(data)[0]
    const mensajeCampo = data[primerCampo]

    return Array.isArray(mensajeCampo)
      ? mensajeCampo.join(' ')
      : String(mensajeCampo)
  }

  return mensajeDefault
}

async function guardarObjetivo(payload) {
  guardandoObjetivo.value = true
  errorModalObjetivo.value = ''
  mensaje.value = ''

  try {
    if (objetivoSeleccionado.value?.id) {
      await actualizarObjetivoEspecifico(objetivoSeleccionado.value.id, payload)
      mensaje.value = 'Objetivo específico actualizado correctamente.'
    } else {
      await crearObjetivoEspecifico(payload)
      mensaje.value = 'Objetivo específico creado correctamente.'
    }

    cerrarModalObjetivo()
    await cargarDatos()
  } catch (e) {
    errorModalObjetivo.value = obtenerMensajeError(
      e,
      objetivoSeleccionado.value?.id
        ? 'No se pudo actualizar el objetivo específico.'
        : 'No se pudo crear el objetivo específico.'
    )
  } finally {
    guardandoObjetivo.value = false
  }
}

function cerrarSesion() {
  emit('logout')
}

onMounted(async () => {
  await cargarDatos()
  await aplicarResaltadoDesdeRuta()
})
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Gestión de Objetivos específicos"
    subtitulo="Administra los objetivos específicos derivados de cada plan anual."
    breadcrumb-actual="Objetivos específicos"
    @logout="cerrarSesion"
  >
    <template v-if="puedeGestionar" #actions>
      <button class="btn-primary-page" type="button" @click="abrirNuevoObjetivo">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>

        Nuevo objetivo específico
      </button>
    </template>

    <div v-if="mensaje" class="alert success">
      {{ mensaje }}
    </div>

    <div v-if="error" class="alert error">
      {{ error }}
    </div>

    <section class="summary-grid">
      <article class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon navy">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 21V4a1 1 0 0 1 1-1h9l4 4v14" />
              <path d="M8 11h8" />
              <path d="M8 15h6" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ objetivos.length }}</div>
        <div class="kpi-label">Objetivos específicos registrados</div>
        <div class="kpi-foot">Total creado en el sistema</div>
      </article>
    </section>

    <div class="toolbar">
      <div class="toolbar-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>

        <input v-model="busqueda" type="text" placeholder="Buscar objetivo específico..." />
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">Plan anual:</span>

        <select v-model="planAnualSeleccionadoFiltro">
          <option value="">Todos</option>

          <option v-for="plan in planesAnualesFiltro" :key="plan.id" :value="plan.id">
            {{ plan.nombre || `Plan ${plan.anio}` }}
          </option>
        </select>
      </div>

      <button
        v-if="hayFiltrosActivos"
        class="btn-limpiar-filtros"
        type="button"
        @click="limpiarFiltros"
      >
        Limpiar filtros
      </button>

      <div class="toolbar-count">
        {{ objetivosFiltrados.length }} objetivos
      </div>
    </div>

    <section class="card-panel table-card">
      <div v-if="cargando" class="message">
        Cargando objetivos específicos...
      </div>

      <div v-else-if="!objetivos.length" class="empty-state">
        No hay objetivos específicos para mostrar.
      </div>

      <div v-else-if="!objetivosFiltrados.length" class="empty-state">
        No se encontraron resultados con los filtros aplicados.
      </div>

      <div v-else class="table-scroll">
      <table>
        <colgroup>
          <col style="width: 26%">
          <col style="width: 14%">
          <col style="width: 22%">
          <col style="width: 14%">
          <col style="width: 12%">
          <col style="width: 12%">
        </colgroup>
        <thead>
          <tr>
            <th>Texto del objetivo</th>
            <th>Plan anual</th>
            <th>Objetivo general</th>
            <th>Creado por</th>
            <th>Fecha de creación</th>
            <th class="th-acciones" style="text-align: right;">Acciones</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="objetivo in objetivosPagina"
            :key="objetivo.id"
            :id="`fila-${objetivo.id}`"
            :class="{ 'highlight-row': idResaltado === Number(objetivo.id) }"
          >
            <td>
              <div class="cell-main" :title="objetivo.texto_objetivo">
                {{ objetivo.texto_objetivo }}
              </div>
            </td>

            <td>
              <span class="code-chip">
                {{ objetivo.plan_anual_nombre || 'Sin plan anual' }}
              </span>
            </td>

            <td>
              <div class="cell-main" :title="objetivo.objetivo_general_texto">
                {{ objetivo.objetivo_general_texto || 'Sin objetivo general' }}
              </div>
            </td>

            <td>
              <div class="owner-cell">
                <div class="avatar-table">
                  {{ inicialesUsuario(objetivo.creado_por_username) }}
                </div>

                {{ objetivo.creado_por_username || 'Sin usuario' }}
              </div>
            </td>

            <td>{{ formatearFecha(objetivo.fecha_creacion) }}</td>

            <td class="td-acciones">
              <div class="actions-cell">
                <button
                  class="action-icon-btn"
                  type="button"
                  title="Ver detalle"
                  aria-label="Ver detalle"
                  @click="abrirDetalleObjetivo(objetivo)"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>

                <button
                  v-if="puedeEditar(objetivo)"
                  class="action-icon-btn"
                  type="button"
                  title="Editar"
                  aria-label="Editar"
                  @click="abrirEditarObjetivo(objetivo)"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <Paginacion
        v-if="objetivosFiltrados.length"
        :pagina-actual="paginaActual"
        :total-paginas="totalPaginas"
        :por-pagina="porPagina"
        :rango-inicio="rangoInicio"
        :rango-fin="rangoFin"
        :total-resultados="totalResultados"
        etiqueta="objetivos"
        @cambiar-pagina="irAPagina"
        @cambiar-por-pagina="cambiarPorPagina"
      />
    </section>

    <ModalBase
      :abierto="modalObjetivoAbierto"
      :titulo="objetivoSeleccionado ? 'Editar objetivo específico' : 'Nuevo objetivo específico'"
      :subtitulo="
        objetivoSeleccionado
          ? 'Actualiza el objetivo específico seleccionado.'
          : 'Registra un objetivo específico asociado a un plan anual En uso.'
      "
      @cerrar="cerrarModalObjetivo"
    >
      <div v-if="errorModalObjetivo" class="alert error">
        {{ errorModalObjetivo }}
      </div>

      <ObjetivoEspecificoForm
        :objetivo="objetivoSeleccionado"
        :planes-anuales="planesAnualesFormulario"
        :objetivos-generales="objetivosGeneralesFormulario"
        @guardar="guardarObjetivo"
        @cancelar="cerrarModalObjetivo"
      />

      <div v-if="guardandoObjetivo" class="saving-message">
        Guardando objetivo específico...
      </div>
    </ModalBase>

    <ModalBase
      :abierto="modalDetalleAbierto"
      titulo="Detalle del objetivo específico"
      subtitulo="Información general del objetivo seleccionado."
      @cerrar="cerrarModalDetalle"
    >
      <div v-if="objetivoSeleccionado" class="detail-grid">
        <div class="detail-item">
          <span>Plan anual</span>
          <strong>{{ objetivoSeleccionado.plan_anual_nombre || 'Sin especificar' }}</strong>
        </div>

        <div class="detail-item">
          <span>Plan estratégico</span>
          <strong>{{ objetivoSeleccionado.plan_estrategico_titulo || 'Sin especificar' }}</strong>
        </div>

        <div class="detail-item">
          <span>Objetivo general</span>
          <strong>{{ objetivoSeleccionado.objetivo_general_texto || 'Sin especificar' }}</strong>
        </div>

        <div class="detail-item">
          <span>Creado por</span>
          <strong>{{ objetivoSeleccionado.creado_por_username || 'Sin usuario' }}</strong>
        </div>

        <div class="detail-item">
          <span>Fecha de creación</span>
          <strong>{{ formatearFecha(objetivoSeleccionado.fecha_creacion) }}</strong>
        </div>

        <div class="detail-item detail-full">
          <span>Texto del objetivo</span>
          <strong>{{ objetivoSeleccionado.texto_objetivo }}</strong>
        </div>
      </div>
    </ModalBase>
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
  max-width: 420px;
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
  max-width: 260px;
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

.btn-limpiar-filtros {
  height: 40px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #e76f51;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.btn-limpiar-filtros:hover {
  background: rgba(231, 111, 81, 0.10);
  border-color: rgba(231, 111, 81, 0.25);
}

.table-scroll {
  overflow-x: auto;
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
  min-width: 760px;
  border-collapse: collapse;
  table-layout: fixed;
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.th-acciones,
.td-acciones {
  white-space: nowrap;
}

tbody td {
  padding: 13px 12px;
  font-size: 13px;
  color: #1d3557;
  border-bottom: 1px solid #f1f4f7;
  vertical-align: middle;
  overflow: hidden;
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
  max-width: 340px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.owner-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
}

.avatar-table {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: #eaf5f5;
  color: #457b9d;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 800;
  flex-shrink: 0;
}

.actions-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
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

.action-icon-btn:hover {
  background: #eaf5f5;
  color: #457b9d;
  border-color: #a8dadc;
}

.saving-message {
  margin-top: 12px;
  padding: 11px 13px;
  border-radius: 11px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 12.5px;
  font-weight: 800;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.detail-item {
  padding: 13px 14px;
  border-radius: 12px;
  background: #f4f7f9;
  border: 1px solid #e4eaef;
}

.detail-full {
  grid-column: 1 / -1;
}

.detail-item span {
  display: block;
  margin-bottom: 5px;
  font-size: 11.5px;
  font-weight: 800;
  color: #6c7a89;
}

.detail-item strong {
  display: block;
  color: #1d3557;
  font-size: 13px;
  line-height: 1.45;
  white-space: pre-line;
}

@media (max-width: 680px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 14px;
  border-top: 1px solid #f1f4f7;
  margin-top: 4px;
}

.showing {
  font-size: 12px;
  color: #9aa8b8;
  font-weight: 600;
}

@media (max-width: 1000px) {
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
    min-width: 0;
  }

  .toolbar-filter select {
    flex: 1;
    min-width: 0;
    max-width: 100%;
  }

  .table-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}

.highlight-row {
  animation: highlightPulse 3.5s ease;
}

@keyframes highlightPulse {
  0% {
    background: rgba(244, 162, 97, 0.24);
    box-shadow: inset 4px 0 0 #f4a261;
  }

  45% {
    background: rgba(244, 162, 97, 0.18);
    box-shadow: inset 4px 0 0 #f4a261;
  }

  100% {
    background: transparent;
    box-shadow: inset 0 0 0 transparent;
  }
}
</style>
