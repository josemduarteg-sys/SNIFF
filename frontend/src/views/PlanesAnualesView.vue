<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import SelectorBuscable from '../components/common/SelectorBuscable.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import ConfirmacionModal from '../components/common/ConfirmacionModal.vue'
import PlanAnualForm from '../components/planes-anuales/PlanAnualForm.vue'
import PlanAnualDetalle from '../components/planes-anuales/PlanAnualDetalle.vue'
import {
  actualizarPlanAnual,
  cerrarPlanAnual,
  completarVigenciaPlanAnual,
  crearPlanAnual,
  obtenerDatosFormularioPlanAnual,
  obtenerPlanesAnuales,
  obtenerPlanesEstrategicosParaPlanAnual,
  ponerEnUsoPlanAnual,
} from '../services/planAnualService'
import { esAdministradorPlanificacion, puedeGestionarPlanesAnuales } from '../utils/permisos'
import { useConfirmacion } from '../composables/useConfirmacion'
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

const puedeGestionar = computed(() => puedeGestionarPlanesAnuales(props.usuario))
const esAdmin = computed(() => esAdministradorPlanificacion(props.usuario))

const emit = defineEmits(['logout'])

const route = useRoute()
const { idResaltado, aplicarResaltadoDesdeRuta } = useResaltado(route)

const planesAnuales = ref([])
const planesFormulario = ref([])
const planesFiltro = ref([])
const cargando = ref(false)
const error = ref('')
const mensaje = ref('')

const busqueda = ref('')
const planSeleccionadoFiltro = ref('')
const opcionesFiltroPlan = computed(() => [
  { id: '', texto: 'Todos' },
  ...planesFiltro.value.map((plan) => ({ id: plan.id, texto: plan.titulo })),
])
const estadoSeleccionadoFiltro = ref('')

const {
  solicitud: confirmacion,
  solicitar: solicitarConfirmacion,
  cancelar: cancelarConfirmacion,
  confirmar: confirmarAccionPendiente,
} = useConfirmacion()

const modalPlanAbierto = ref(false)
const planSeleccionado = ref(null)
const guardandoPlan = ref(false)
const errorModalPlan = ref('')

const modalDetalleAbierto = ref(false)
const planDetalle = ref(null)

const planesEnUso = computed(() => {
  return planesAnuales.value.filter((item) => item.estado === 'en_uso').length
})

const planesFiltrados = computed(() => {
  const texto = busqueda.value.trim().toLowerCase()

  return planesAnuales.value.filter((plan) => {
    // Bloque 7: la búsqueda ya no filtra solo por año — también busca en
    // el nombre visible ("Plan 2026") y en el título del plan estratégico
    // asociado, igual que las demás vistas del sistema.
    const nombrePlan = (plan.nombre || `Plan ${plan.anio}`).toLowerCase()
    const tituloPlanEstrategico = (plan.plan_estrategico_titulo || '').toLowerCase()

    const coincideBusqueda =
      !texto ||
      String(plan.anio).includes(texto) ||
      nombrePlan.includes(texto) ||
      tituloPlanEstrategico.includes(texto)

    const coincidePlan =
      !planSeleccionadoFiltro.value ||
      Number(plan.plan_estrategico) === Number(planSeleccionadoFiltro.value)

    const coincideEstado = !estadoSeleccionadoFiltro.value || plan.estado === estadoSeleccionadoFiltro.value

    return coincideBusqueda && coincidePlan && coincideEstado
  })
})

const hayFiltrosActivos = computed(() => {
  return busqueda.value.trim() !== '' || planSeleccionadoFiltro.value !== '' || estadoSeleccionadoFiltro.value !== ''
})

function limpiarFiltros() {
  busqueda.value = ''
  planSeleccionadoFiltro.value = ''
  estadoSeleccionadoFiltro.value = ''
}

const {
  paginaActual,
  porPagina,
  totalResultados,
  totalPaginas,
  elementosVisibles: planesPagina,
  rangoInicio,
  rangoFin,
  irAPagina,
} = usePaginacion(planesFiltrados)

function cambiarPorPagina(valor) {
  porPagina.value = valor
}

async function cargarDatos() {
  cargando.value = true
  error.value = ''

  try {
    const [planesData, datosFormulario, planesTodos] = await Promise.all([
      obtenerPlanesAnuales(),
      obtenerDatosFormularioPlanAnual(),
      obtenerPlanesEstrategicosParaPlanAnual(),
    ])

    planesAnuales.value = planesData
    planesFormulario.value = datosFormulario.planes
    planesFiltro.value = planesTodos
  } catch (e) {
    error.value = 'No se pudieron cargar los planes anuales.'
  } finally {
    cargando.value = false
  }
}

function estadoClase(estado) {
  if (estado === 'en_uso') return 'active'
  if (estado === 'cerrado') return 'finished'
  return 'warning'
}

function textoEstado(estado) {
  const estados = {
    borrador: 'Borrador',
    en_uso: 'En uso',
    cerrado: 'Cerrado',
  }

  return estados[estado] || estado || 'Sin estado'
}

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

function planPadreCerrado(plan) {
  return plan.plan_estrategico_estado === 'cerrado'
}

function puedeEditar(plan) {
  return puedeGestionar.value && plan.estado === 'borrador' && !planPadreCerrado(plan)
}

function puedePonerEnUso(plan) {
  return esAdmin.value && plan.estado === 'borrador' && !planPadreCerrado(plan)
}

function puedeCerrar(plan) {
  return esAdmin.value && plan.estado === 'en_uso' && !planPadreCerrado(plan)
}

// Etapa 1 (M9): planes anuales antiguos En uso sin fechas de vigencia.
function puedeCompletarVigencia(plan) {
  return esAdmin.value && plan.puede_completar_vigencia === true
}

function abrirCompletarVigencia(plan) {
  if (!puedeCompletarVigencia(plan)) {
    return
  }

  planSeleccionado.value = plan
  modalPlanAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalPlan.value = ''
}

async function guardarVigencia(payload) {
  guardandoPlan.value = true
  errorModalPlan.value = ''
  mensaje.value = ''

  try {
    await completarVigenciaPlanAnual(planSeleccionado.value.id, payload)
    mensaje.value = 'Vigencia del plan anual registrada correctamente.'
    cerrarModalPlan()
    await cargarDatos()
  } catch (e) {
    errorModalPlan.value = obtenerMensajeError(e, 'No se pudo registrar la vigencia del plan anual.')
  } finally {
    guardandoPlan.value = false
  }
}

function abrirNuevoPlan() {
  planSeleccionado.value = null
  modalPlanAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalPlan.value = ''
}

function abrirEditarPlan(plan) {
  if (!puedeEditar(plan)) {
    return
  }

  planSeleccionado.value = plan
  modalPlanAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalPlan.value = ''
}

function cerrarModalPlan() {
  modalPlanAbierto.value = false
  planSeleccionado.value = null
  guardandoPlan.value = false
  errorModalPlan.value = ''
}

function abrirDetallePlan(plan) {
  planDetalle.value = plan
  modalDetalleAbierto.value = true
}

function cerrarModalDetalle() {
  modalDetalleAbierto.value = false
  planDetalle.value = null
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

async function guardarPlan(payload) {
  guardandoPlan.value = true
  errorModalPlan.value = ''
  mensaje.value = ''

  try {
    if (planSeleccionado.value?.id) {
      await actualizarPlanAnual(planSeleccionado.value.id, payload)
      mensaje.value = 'Plan anual actualizado correctamente.'
    } else {
      await crearPlanAnual(payload)
      mensaje.value = 'Plan anual creado correctamente.'
    }

    cerrarModalPlan()
    await cargarDatos()
  } catch (e) {
    errorModalPlan.value = obtenerMensajeError(
      e,
      planSeleccionado.value?.id
        ? 'No se pudo actualizar el plan anual.'
        : 'No se pudo crear el plan anual.'
    )
  } finally {
    guardandoPlan.value = false
  }
}

function manejarPonerEnUso(plan) {
  solicitarConfirmacion({
    titulo: 'Pasar a En uso',
    mensaje: `¿Deseás poner en uso el ${plan.nombre || `Plan ${plan.anio}`}?`,
    textoSecundario: 'El plan estratégico relacionado y el año quedarán bloqueados.',
    textoConfirmar: 'Pasar a En uso',
    variante: 'normal',
    accion: async () => {
      error.value = ''
      mensaje.value = ''

      try {
        await ponerEnUsoPlanAnual(plan.id)
        mensaje.value = 'Plan anual puesto En uso correctamente.'
        await cargarDatos()
      } catch (e) {
        error.value = obtenerMensajeError(e, 'No se pudo poner en uso el plan anual.')
      }
    },
  })
}

function manejarCerrar(plan) {
  solicitarConfirmacion({
    titulo: 'Cerrar plan anual',
    mensaje: `¿Deseás cerrar el ${plan.nombre || `Plan ${plan.anio}`}?`,
    textoSecundario: 'Esta acción es definitiva: el plan anual y sus objetivos específicos quedarán inmutables.',
    textoConfirmar: 'Cerrar',
    variante: 'peligrosa',
    accion: async () => {
      error.value = ''
      mensaje.value = ''

      try {
        await cerrarPlanAnual(plan.id)
        mensaje.value = 'Plan anual cerrado correctamente.'
        await cargarDatos()
      } catch (e) {
        error.value = obtenerMensajeError(e, 'No se pudo cerrar el plan anual.')
      }
    },
  })
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
    titulo="Gestión de Planes anuales"
    subtitulo="Administra los planes anuales derivados de cada plan estratégico."
    breadcrumb-actual="Planes anuales"
    @logout="cerrarSesion"
  >
    <template v-if="puedeGestionar" #actions>
      <button class="btn-primary" type="button" @click="abrirNuevoPlan">
        + Nuevo plan anual
      </button>
    </template>

    <div v-if="mensaje" class="alert success">
      {{ mensaje }}
    </div>

    <div v-if="error" class="alert error">
      {{ error }}
    </div>

    <section class="summary-grid">
      <article class="summary-card">
        <span>Total registrados</span>
        <strong>{{ planesAnuales.length }}</strong>
        <p>Planes anuales creados en el sistema</p>
      </article>

      <article class="summary-card">
        <span>En uso</span>
        <strong>{{ planesEnUso }}</strong>
        <p>Planes anuales actualmente en ejecución</p>
      </article>
    </section>

    <div class="toolbar">
      <div class="toolbar-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>

        <input v-model="busqueda" type="text" placeholder="Buscar por año o plan estratégico..." />
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">Plan estratégico:</span>

        <SelectorBuscable
          v-model="planSeleccionadoFiltro"
          :opciones="opcionesFiltroPlan"
          variante="toolbar"
          etiqueta="Filtrar por plan estratégico"
          placeholder="Todos"
          placeholder-busqueda="Buscar plan estratégico..."
        />
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">Estado:</span>

        <select v-model="estadoSeleccionadoFiltro">
          <option value="">Todos</option>
          <option value="borrador">Borrador</option>
          <option value="en_uso">En uso</option>
          <option value="cerrado">Cerrado</option>
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
        {{ planesFiltrados.length }} planes
      </div>
    </div>

    <section class="card-panel">
      <div v-if="cargando" class="message">
        Cargando planes anuales...
      </div>

      <div v-else-if="!planesAnuales.length" class="empty-state">
        No hay planes anuales para mostrar.
      </div>

      <div v-else-if="!planesFiltrados.length" class="empty-state">
        No se encontraron resultados con los filtros aplicados.
      </div>

      <div v-else class="table-scroll">
      <table>
        <colgroup>
          <col style="width: 15%">
          <col style="width: 24%">
          <col style="width: 11%">
          <col style="width: 14%">
          <col style="width: 20%">
          <col style="width: 16%">
        </colgroup>
        <thead>
          <tr>
            <th>Plan anual</th>
            <th>Plan estratégico</th>
            <th>Estado</th>
            <th>Creado por</th>
            <th>Vigencia</th>
            <th class="th-acciones" style="text-align: right;">Acciones</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="plan in planesPagina"
            :key="plan.id"
            :id="`fila-${plan.id}`"
            :class="{ 'highlight-row': idResaltado === Number(plan.id) }"
          >
            <td>
              <div class="cell-main" :title="plan.nombre || `Plan ${plan.anio}`">{{ plan.nombre || `Plan ${plan.anio}` }}</div>
            </td>

            <td>
              <span class="code-chip">{{ plan.plan_estrategico_titulo || 'Sin plan' }}</span>
            </td>

            <td>
              <span class="badge" :class="estadoClase(plan.estado)">
                {{ textoEstado(plan.estado) }}
              </span>
            </td>

            <td>{{ plan.creado_por_username || 'Sin usuario' }}</td>
            <td>
              <span v-if="plan.fecha_inicio && plan.fecha_fin">
                {{ formatearFecha(plan.fecha_inicio) }} – {{ formatearFecha(plan.fecha_fin) }}
              </span>
              <span v-else>Sin definir</span>
            </td>

            <td class="td-acciones">
              <div class="actions-cell">
                <button
                  class="action-icon-btn"
                  type="button"
                  title="Ver detalle"
                  aria-label="Ver detalle"
                  @click="abrirDetallePlan(plan)"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>

                <button
                  v-if="puedeEditar(plan)"
                  class="action-icon-btn"
                  type="button"
                  title="Editar"
                  aria-label="Editar"
                  @click="abrirEditarPlan(plan)"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" />
                  </svg>
                </button>

                <button
                  v-if="puedeCompletarVigencia(plan)"
                  class="action-btn"
                  type="button"
                  @click="abrirCompletarVigencia(plan)"
                >
                  Completar vigencia
                </button>

                <button
                  v-if="puedePonerEnUso(plan)"
                  class="action-btn"
                  type="button"
                  @click="manejarPonerEnUso(plan)"
                >
                  Pasar a En uso
                </button>

                <button
                  v-if="puedeCerrar(plan)"
                  class="action-btn danger"
                  type="button"
                  @click="manejarCerrar(plan)"
                >
                  Cerrar
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <Paginacion
        v-if="planesFiltrados.length"
        :pagina-actual="paginaActual"
        :total-paginas="totalPaginas"
        :por-pagina="porPagina"
        :rango-inicio="rangoInicio"
        :rango-fin="rangoFin"
        :total-resultados="totalResultados"
        etiqueta="planes"
        @cambiar-pagina="irAPagina"
        @cambiar-por-pagina="cambiarPorPagina"
      />
    </section>

    <ModalBase
      :abierto="modalPlanAbierto"
      :titulo="
        planSeleccionado?.puede_completar_vigencia
          ? 'Completar vigencia del plan anual'
          : planSeleccionado ? 'Editar plan anual' : 'Nuevo plan anual'
      "
      :subtitulo="
        planSeleccionado?.puede_completar_vigencia
          ? 'Registra por única vez las fechas de vigencia de este plan anual En uso.'
          : planSeleccionado
            ? 'Actualiza el plan estratégico y el año del plan anual.'
            : 'Registra un plan anual sobre un plan estratégico En uso.'
      "
      @cerrar="cerrarModalPlan"
    >
      <div v-if="errorModalPlan" class="alert error">
        {{ errorModalPlan }}
      </div>

      <PlanAnualForm
        :plan-anual="planSeleccionado"
        :planes="planesFormulario"
        @guardar="guardarPlan"
        @completar-vigencia="guardarVigencia"
        @cancelar="cerrarModalPlan"
      />

      <div v-if="guardandoPlan" class="saving-message">
        Guardando plan anual...
      </div>
    </ModalBase>

    <ModalBase
      :abierto="modalDetalleAbierto"
      titulo="Detalle de plan anual"
      subtitulo="Información completa del plan anual registrado."
      @cerrar="cerrarModalDetalle"
    >
      <PlanAnualDetalle v-if="planDetalle" :plan-anual="planDetalle" />
    </ModalBase>

    <ConfirmacionModal
      :abierto="!!confirmacion"
      :titulo="confirmacion?.titulo"
      :mensaje="confirmacion?.mensaje"
      :texto-secundario="confirmacion?.textoSecundario"
      :texto-confirmar="confirmacion?.textoConfirmar"
      :texto-cancelar="confirmacion?.textoCancelar"
      :variante="confirmacion?.variante"
      @confirmar="confirmarAccionPendiente"
      @cancelar="cancelarConfirmacion"
    />
  </AppLayout>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card,
.card-panel {
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 14px;
  box-shadow: 0 8px 22px rgba(29, 53, 87, 0.07);
}

.summary-card {
  padding: 20px;
}

.summary-card span {
  color: #457b9d;
  font-size: 13px;
  font-weight: 800;
}

.summary-card strong {
  display: block;
  color: #1d3557;
  font-size: 34px;
  margin-top: 10px;
}

.summary-card p {
  margin: 6px 0 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 600;
}

.btn-primary {
  height: 40px;
  padding: 0 16px;
  border: none;
  border-radius: 10px;
  background: #1d3557;
  color: #ffffff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.btn-primary:hover {
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
  min-width: 200px;
  max-width: 340px;
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
  max-width: 220px;
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
  padding: 22px;
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

.actions-cell {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}

.action-btn {
  height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  color: #457b9d;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
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

.action-btn:hover {
  background: #eaf5f5;
  border-color: #a8dadc;
}

.action-btn.danger {
  color: #e76f51;
}

.action-btn.danger:hover {
  background: rgba(231, 111, 81, 0.10);
  border-color: rgba(231, 111, 81, 0.25);
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

table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  table-layout: fixed;
}

th {
  text-align: left;
  color: #9aa8b8;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 12px 10px;
  border-bottom: 1px solid #e4eaef;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.th-acciones,
.td-acciones {
  white-space: nowrap;
}

td {
  padding: 13px 10px;
  border-bottom: 1px solid #eef2f5;
  color: #1d3557;
  font-size: 13px;
  font-weight: 600;
  vertical-align: middle;
  overflow: hidden;
}

.cell-main {
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.badge.active {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.badge.warning {
  background: rgba(244, 162, 97, 0.16);
  color: #b86520;
}

.badge.finished {
  background: rgba(69, 123, 157, 0.12);
  color: #457b9d;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
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
