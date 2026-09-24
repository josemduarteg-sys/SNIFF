<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import ConfirmacionModal from '../components/common/ConfirmacionModal.vue'
import AreaForm from '../components/areas/AreaForm.vue'
import {
  obtenerAreas,
  crearArea,
  actualizarArea,
  activarArea,
  inactivarArea,
} from '../services/areaService'
import { puedeGestionarAreas } from '../utils/permisos'
import { useConfirmacion } from '../composables/useConfirmacion'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const puedeGestionar = computed(() => puedeGestionarAreas(props.usuario))

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

const modalAreaAbierto = ref(false)
const areaSeleccionada = ref(null)
const guardandoArea = ref(false)
const errorModalArea = ref('')

const totalAreas = computed(() => areas.value.length)

const areasActivas = computed(() => {
  return areas.value.filter((area) => area.estado === true).length
})

const areasInactivas = computed(() => {
  return areas.value.filter((area) => area.estado === false).length
})

async function cargarAreas() {
  if (!puedeGestionar.value) {
    return
  }

  cargando.value = true
  error.value = ''

  try {
    areas.value = await obtenerAreas()
  } catch (e) {
    error.value = 'No se pudieron cargar las áreas.'
  } finally {
    cargando.value = false
  }
}

function abrirNuevaArea() {
  areaSeleccionada.value = null
  modalAreaAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalArea.value = ''
}

function abrirEditarArea(area) {
  areaSeleccionada.value = area
  modalAreaAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalArea.value = ''
}

function cerrarModalArea() {
  modalAreaAbierto.value = false
  areaSeleccionada.value = null
  guardandoArea.value = false
  errorModalArea.value = ''
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

async function guardarArea(payload) {
  guardandoArea.value = true
  errorModalArea.value = ''
  mensaje.value = ''

  try {
    if (areaSeleccionada.value?.id) {
      await actualizarArea(areaSeleccionada.value.id, payload)
      mensaje.value = 'Área actualizada correctamente.'
    } else {
      await crearArea(payload)
      mensaje.value = 'Área creada correctamente.'
    }

    cerrarModalArea()
    await cargarAreas()
  } catch (e) {
    errorModalArea.value = obtenerMensajeError(
      e,
      areaSeleccionada.value?.id
        ? 'No se pudo actualizar el área.'
        : 'No se pudo crear el área.'
    )
  } finally {
    guardandoArea.value = false
  }
}

function manejarInactivarArea(area) {
  solicitarConfirmacion({
    titulo: 'Inactivar área',
    mensaje: `¿Deseás inactivar el área "${area.nombre}"?`,
    textoSecundario: 'El área dejará de estar disponible para su uso.',
    textoConfirmar: 'Inactivar',
    variante: 'peligrosa',
    accion: async () => {
      error.value = ''
      mensaje.value = ''

      try {
        await inactivarArea(area.id)
        mensaje.value = 'Área inactivada correctamente.'
        await cargarAreas()
      } catch (e) {
        error.value = obtenerMensajeError(e, 'No se pudo inactivar el área.')
      }
    },
  })
}

async function manejarReactivarArea(area) {
  error.value = ''
  mensaje.value = ''

  try {
    await activarArea(area.id)
    mensaje.value = 'Área reactivada correctamente.'
    await cargarAreas()
  } catch (e) {
    error.value = obtenerMensajeError(e, 'No se pudo reactivar el área.')
  }
}

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

function cerrarSesion() {
  emit('logout')
}

onMounted(() => {
  cargarAreas()
})
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Gestión de áreas"
    subtitulo="Administra las áreas o departamentos de la cooperativa utilizados en la planificación estratégica."
    breadcrumb-actual="Áreas"
    @logout="cerrarSesion"
  >
    <template v-if="puedeGestionar" #actions>
      <button class="btn-primary" type="button" @click="abrirNuevaArea">
        + Nueva área
      </button>
    </template>

    <div v-if="!puedeGestionar" class="card-panel restricted-panel">
      <h2>No tenés permisos para gestionar áreas.</h2>
      <p>Esta sección está disponible únicamente para administración del sistema.</p>
    </div>

    <template v-else>
      <div v-if="mensaje" class="alert success">
        {{ mensaje }}
      </div>

      <div v-if="error" class="alert error">
        {{ error }}
      </div>

      <section class="summary-grid">
        <article class="summary-card">
          <span>Total de áreas</span>
          <strong>{{ totalAreas }}</strong>
          <p>Áreas registradas en el sistema</p>
        </article>

        <article class="summary-card">
          <span>Activas</span>
          <strong>{{ areasActivas }}</strong>
          <p>Áreas disponibles para su uso</p>
        </article>

        <article class="summary-card">
          <span>Inactivas</span>
          <strong>{{ areasInactivas }}</strong>
          <p>Conservadas para historial</p>
        </article>
      </section>

      <section class="card-panel">
        <div class="panel-head">
          <div>
            <h2>Listado de áreas</h2>
            <p>Consulta general de áreas registradas.</p>
          </div>
        </div>

        <div v-if="cargando" class="message">
          Cargando áreas...
        </div>

        <div v-else-if="!areas.length" class="empty-state">
          No hay áreas registradas todavía.
        </div>

        <table v-else>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Descripción</th>
              <th>Estado</th>
              <th>Fecha creación</th>
              <th style="text-align: right;">Acciones</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="area in areas"
              :key="area.id"
            >
              <td>
                <div class="cell-main">{{ area.nombre }}</div>
              </td>

              <td>
                <div class="cell-sub">{{ area.descripcion || 'Sin descripción' }}</div>
              </td>

              <td>
                <span class="badge" :class="area.estado ? 'active' : 'inactive'">
                  {{ area.estado ? 'Activa' : 'Inactiva' }}
                </span>
              </td>

              <td>{{ formatearFecha(area.fecha_creacion) }}</td>

              <td>
                <div class="actions-cell">
                  <button
                    class="action-icon-btn"
                    type="button"
                    title="Editar"
                    aria-label="Editar"
                    @click="abrirEditarArea(area)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" />
                    </svg>
                  </button>

                  <button
                    v-if="area.estado"
                    class="action-btn danger"
                    type="button"
                    @click="manejarInactivarArea(area)"
                  >
                    Inactivar
                  </button>

                  <button
                    v-else
                    class="action-btn"
                    type="button"
                    @click="manejarReactivarArea(area)"
                  >
                    Reactivar
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <ModalBase
        :abierto="modalAreaAbierto"
        :titulo="areaSeleccionada ? 'Editar área' : 'Nueva área'"
        :subtitulo="
          areaSeleccionada
            ? 'Actualiza los datos generales del área.'
            : 'Registra un área de la cooperativa.'
        "
        @cerrar="cerrarModalArea"
      >
        <div v-if="errorModalArea" class="alert error">
          {{ errorModalArea }}
        </div>

        <AreaForm
          :area="areaSeleccionada"
          @guardar="guardarArea"
          @cancelar="cerrarModalArea"
        />

        <div v-if="guardandoArea" class="saving-message">
          Guardando área...
        </div>
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
    </template>
  </AppLayout>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
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

.restricted-panel {
  text-align: center;
  padding: 40px 22px;
}

.restricted-panel h2 {
  margin: 0 0 8px;
  color: #1d3557;
  font-size: 17px;
  font-weight: 800;
}

.restricted-panel p {
  margin: 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 600;
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
}

.cell-sub {
  color: #9aa8b8;
  font-size: 12px;
  font-weight: 500;
  max-width: 420px;
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
</style>
