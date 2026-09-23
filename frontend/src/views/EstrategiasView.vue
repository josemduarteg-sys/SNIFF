<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import ConfirmacionModal from '../components/common/ConfirmacionModal.vue'
import EstrategiaForm from '../components/estrategias/EstrategiaForm.vue'
import EstrategiaDetalle from '../components/estrategias/EstrategiaDetalle.vue'
import {
  activarEstrategia,
  actualizarEstrategia,
  crearEstrategia,
  finalizarEstrategia,
  inactivarEstrategia,
  obtenerDatosFormularioEstrategia,
  obtenerEstrategias,
} from '../services/estrategiaService'
import { esAdministrador, puedeGestionarEstrategias } from '../utils/permisos'
import { useConfirmacion } from '../composables/useConfirmacion'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const puedeGestionar = computed(() => puedeGestionarEstrategias(props.usuario))
const esAdmin = computed(() => esAdministrador(props.usuario))

const emit = defineEmits(['logout'])

const route = useRoute()
const idResaltado = ref(null)
let timeoutResaltado = null

const estrategias = ref([])
const areas = ref([])
const cargando = ref(false)
const error = ref('')
const mensaje = ref('')

const {
  solicitud: confirmacion,
  solicitar: solicitarConfirmacion,
  cancelar: cancelarConfirmacion,
  confirmar: confirmarAccionPendiente,
} = useConfirmacion()

const modalEstrategiaAbierto = ref(false)
const estrategiaSeleccionada = ref(null)
const guardandoEstrategia = ref(false)
const errorModalEstrategia = ref('')

const modalDetalleAbierto = ref(false)
const estrategiaDetalle = ref(null)

const estrategiasActivas = computed(() => {
  return estrategias.value.filter((item) => item.estado === 'activa' || item.estado === true).length
})

async function cargarEstrategias() {
  cargando.value = true
  error.value = ''

  try {
    const [estrategiasData, datosFormulario] = await Promise.all([
      obtenerEstrategias(),
      obtenerDatosFormularioEstrategia(),
    ])

    estrategias.value = estrategiasData
    areas.value = datosFormulario.areas
  } catch (e) {
    error.value = 'No se pudieron cargar las estrategias.'
  } finally {
    cargando.value = false
  }
}

async function aplicarResaltadoDesdeRuta() {
  const idQuery = Number(route.query.resaltar)

  if (!idQuery) {
    return
  }

  idResaltado.value = idQuery

  await nextTick()

  const fila = document.getElementById(`fila-${idQuery}`)

  if (fila) {
    fila.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    })
  }

  if (timeoutResaltado) {
    window.clearTimeout(timeoutResaltado)
  }

  timeoutResaltado = window.setTimeout(() => {
    if (idResaltado.value === idQuery) {
      idResaltado.value = null
    }
  }, 3500)
}

watch(
  () => route.query.resaltar,
  () => {
    aplicarResaltadoDesdeRuta()
  }
)

function estadoClase(estado) {
  if (estado === 'activa' || estado === true) return 'active'
  if (estado === 'finalizada') return 'finished'
  if (estado === 'en_revision') return 'warning'
  return 'inactive'
}

function textoEstado(estado) {
  if (estado === true) return 'Activa'
  if (estado === false) return 'Inactiva'

  const estados = {
    activa: 'Activa',
    en_revision: 'En revisión',
    finalizada: 'Finalizada',
    inactiva: 'Inactiva',
  }

  return estados[estado] || estado || 'Sin estado'
}

function abrirNuevaEstrategia() {
  estrategiaSeleccionada.value = null
  modalEstrategiaAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalEstrategia.value = ''
}

function abrirEditarEstrategia(estrategia) {
  estrategiaSeleccionada.value = estrategia
  modalEstrategiaAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalEstrategia.value = ''
}

function cerrarModalEstrategia() {
  modalEstrategiaAbierto.value = false
  estrategiaSeleccionada.value = null
  guardandoEstrategia.value = false
  errorModalEstrategia.value = ''
}

function abrirDetalleEstrategia(estrategia) {
  estrategiaDetalle.value = estrategia
  modalDetalleAbierto.value = true
}

function cerrarModalDetalle() {
  modalDetalleAbierto.value = false
  estrategiaDetalle.value = null
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

async function guardarEstrategia(payload) {
  guardandoEstrategia.value = true
  errorModalEstrategia.value = ''
  mensaje.value = ''

  try {
    if (estrategiaSeleccionada.value?.id) {
      await actualizarEstrategia(estrategiaSeleccionada.value.id, payload)
      mensaje.value = 'Estrategia actualizada correctamente.'
    } else {
      await crearEstrategia(payload)
      mensaje.value = 'Estrategia creada correctamente.'
    }

    cerrarModalEstrategia()
    await cargarEstrategias()
  } catch (e) {
    errorModalEstrategia.value = obtenerMensajeError(
      e,
      estrategiaSeleccionada.value?.id
        ? 'No se pudo actualizar la estrategia.'
        : 'No se pudo crear la estrategia.'
    )
  } finally {
    guardandoEstrategia.value = false
  }
}

async function manejarActivarEstrategia(estrategia) {
  error.value = ''
  mensaje.value = ''

  try {
    await activarEstrategia(estrategia.id)
    mensaje.value = 'Estrategia activada correctamente.'
    await cargarEstrategias()
  } catch (e) {
    error.value = obtenerMensajeError(e, 'No se pudo activar la estrategia.')
  }
}

function manejarFinalizarEstrategia(estrategia) {
  solicitarConfirmacion({
    titulo: 'Finalizar estrategia',
    mensaje: `¿Deseás finalizar la estrategia "${estrategia.nombre}"?`,
    textoSecundario: 'Una vez finalizada, ya no se podrá seguir editando su seguimiento activo.',
    textoConfirmar: 'Finalizar',
    variante: 'advertencia',
    accion: async () => {
      error.value = ''
      mensaje.value = ''

      try {
        await finalizarEstrategia(estrategia.id)
        mensaje.value = 'Estrategia finalizada correctamente.'
        await cargarEstrategias()
      } catch (e) {
        error.value = obtenerMensajeError(e, 'No se pudo finalizar la estrategia.')
      }
    },
  })
}

function manejarInactivarEstrategia(estrategia) {
  solicitarConfirmacion({
    titulo: 'Inactivar estrategia',
    mensaje: `¿Deseás inactivar la estrategia "${estrategia.nombre}"?`,
    textoSecundario: 'La estrategia dejará de estar disponible para seguimiento activo.',
    textoConfirmar: 'Inactivar',
    variante: 'peligrosa',
    accion: async () => {
      error.value = ''
      mensaje.value = ''

      try {
        await inactivarEstrategia(estrategia.id)
        mensaje.value = 'Estrategia inactivada correctamente.'
        await cargarEstrategias()
      } catch (e) {
        error.value = obtenerMensajeError(e, 'No se pudo inactivar la estrategia.')
      }
    },
  })
}

function cerrarSesion() {
  emit('logout')
}

onMounted(async () => {
  await cargarEstrategias()
  await aplicarResaltadoDesdeRuta()
})

onBeforeUnmount(() => {
  if (timeoutResaltado) {
    window.clearTimeout(timeoutResaltado)
  }
})
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Gestión de Estrategias"
    subtitulo="Administra las estrategias empresariales vinculadas al seguimiento de indicadores KPI."
    breadcrumb-actual="Estrategias"
    @logout="cerrarSesion"
  >
    <template v-if="puedeGestionar" #actions>
      <button class="btn-primary" type="button" @click="abrirNuevaEstrategia">
        + Nueva estrategia
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
        <span>Total registradas</span>
        <strong>{{ estrategias.length }}</strong>
        <p>Estrategias creadas en el sistema</p>
      </article>

      <article class="summary-card">
        <span>Activas</span>
        <strong>{{ estrategiasActivas }}</strong>
        <p>Estrategias actualmente en seguimiento</p>
      </article>
    </section>

    <section class="card-panel">
      <div class="panel-head">
        <div>
          <h2>Listado de estrategias</h2>
          <p>Consulta general de estrategias registradas.</p>
        </div>
      </div>

      <div v-if="cargando" class="message">
        Cargando estrategias...
      </div>

      <div v-else-if="!estrategias.length" class="empty-state">
        No hay estrategias registradas todavía.
      </div>

      <table v-else>
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Área</th>
            <th>Fecha inicio</th>
            <th>Fecha fin</th>
            <th>Estado</th>
            <th style="text-align: right;">Acciones</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="estrategia in estrategias"
            :key="estrategia.id"
            :id="`fila-${estrategia.id}`"
            :class="{ 'highlight-row': idResaltado === Number(estrategia.id) }"
          >
            <td>
              <div class="cell-main" :title="estrategia.nombre">{{ estrategia.nombre }}</div>
              <div class="cell-sub" :title="estrategia.descripcion || 'Sin descripción'">{{ estrategia.descripcion || 'Sin descripción' }}</div>
            </td>

            <td>{{ estrategia.area_nombre || 'Sin área' }}</td>
            <td>{{ estrategia.fecha_inicio || 'No definida' }}</td>
            <td>{{ estrategia.fecha_fin || 'No definida' }}</td>

            <td>
              <span class="badge" :class="estadoClase(estrategia.estado)">
                {{ textoEstado(estrategia.estado) }}
              </span>
            </td>

            <td>
              <div class="actions-cell">
                <button
                  class="action-icon-btn"
                  type="button"
                  title="Ver detalle"
                  aria-label="Ver detalle"
                  @click="abrirDetalleEstrategia(estrategia)"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>

                <button
                  v-if="puedeGestionar && (esAdmin || estrategia.estado === 'en_revision')"
                  class="action-icon-btn"
                  type="button"
                  title="Editar"
                  aria-label="Editar"
                  @click="abrirEditarEstrategia(estrategia)"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" />
                  </svg>
                </button>

                <template v-if="puedeGestionar && esAdmin">
                  <button
                    v-if="estrategia.estado !== 'activa'"
                    class="action-btn"
                    type="button"
                    @click="manejarActivarEstrategia(estrategia)"
                  >
                    Activar
                  </button>

                  <button
                    v-if="estrategia.estado !== 'finalizada'"
                    class="action-btn"
                    type="button"
                    @click="manejarFinalizarEstrategia(estrategia)"
                  >
                    Finalizar
                  </button>

                  <button
                    v-if="estrategia.estado !== 'inactiva'"
                    class="action-btn danger"
                    type="button"
                    @click="manejarInactivarEstrategia(estrategia)"
                  >
                    Inactivar
                  </button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <ModalBase
      :abierto="modalEstrategiaAbierto"
      :titulo="estrategiaSeleccionada ? 'Editar estrategia' : 'Nueva estrategia'"
      :subtitulo="
        estrategiaSeleccionada
          ? 'Actualiza los datos generales de la estrategia.'
          : 'Registra una estrategia para agrupar objetivos e indicadores KPI.'
      "
      @cerrar="cerrarModalEstrategia"
    >
      <div v-if="errorModalEstrategia" class="alert error">
        {{ errorModalEstrategia }}
      </div>

      <EstrategiaForm
        :estrategia="estrategiaSeleccionada"
        :areas="areas"
        @guardar="guardarEstrategia"
        @cancelar="cerrarModalEstrategia"
      />

      <div v-if="guardandoEstrategia" class="saving-message">
        Guardando estrategia...
      </div>
    </ModalBase>

    <ModalBase
      :abierto="modalDetalleAbierto"
      titulo="Detalle de estrategia"
      subtitulo="Información completa de la estrategia registrada."
      @cerrar="cerrarModalDetalle"
    >
      <EstrategiaDetalle v-if="estrategiaDetalle" :estrategia="estrategiaDetalle" />
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

.card-panel {
  padding: 22px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.panel-head h2 {
  margin: 0;
  color: #1d3557;
  font-size: 17px;
  font-weight: 800;
}

.panel-head p {
  margin: 4px 0 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 500;
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
  border-collapse: collapse;
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
}

td {
  padding: 13px 10px;
  border-bottom: 1px solid #eef2f5;
  color: #1d3557;
  font-size: 13px;
  font-weight: 600;
  vertical-align: top;
}

.cell-main {
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-sub {
  color: #9aa8b8;
  font-size: 12px;
  font-weight: 500;
  margin-top: 2px;
  max-width: 520px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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

.badge.inactive {
  background: rgba(154, 168, 184, 0.16);
  color: #5e6e82;
}

@media (max-width: 800px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  table {
    display: block;
    overflow-x: auto;
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