<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import ObjetivoForm from '../components/objetivos/ObjetivoForm.vue'
import {
  actualizarObjetivo,
  crearObjetivo,
  inactivarObjetivo,
  obtenerDatosFormularioObjetivo,
  obtenerObjetivos,
  reactivarObjetivo,
} from '../services/objetivoService'
import { puedeGestionarObjetivos } from '../utils/permisos'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const puedeGestionar = computed(() => puedeGestionarObjetivos(props.usuario))

const emit = defineEmits(['logout'])

const objetivos = ref([])
const estrategias = ref([])
const busqueda = ref('')
const estrategiaSeleccionada = ref('')
const cargando = ref(false)
const error = ref('')
const mensaje = ref('')

const modalObjetivoAbierto = ref(false)
const modalDetalleAbierto = ref(false)
const objetivoSeleccionado = ref(null)
const guardandoObjetivo = ref(false)

async function cargarDatos() {
  cargando.value = true
  error.value = ''

  try {
    const [objetivosData, datosFormulario] = await Promise.all([
      obtenerObjetivos(),
      obtenerDatosFormularioObjetivo(),
    ])

    objetivos.value = objetivosData
    estrategias.value = datosFormulario.estrategias
  } catch (e) {
    error.value = 'No se pudieron cargar los objetivos.'
  } finally {
    cargando.value = false
  }
}

const objetivosFiltrados = computed(() => {
  const texto = busqueda.value.trim().toLowerCase()

  return objetivos.value.filter((objetivo) => {
    const coincideBusqueda =
      !texto ||
      objetivo.nombre?.toLowerCase().includes(texto) ||
      objetivo.descripcion?.toLowerCase().includes(texto) ||
      objetivo.estrategia_nombre?.toLowerCase().includes(texto)

    const coincideEstrategia =
      !estrategiaSeleccionada.value ||
      Number(objetivo.estrategia) === Number(estrategiaSeleccionada.value)

    return coincideBusqueda && coincideEstrategia
  })
})

const objetivosActivos = computed(() => {
  return objetivos.value.filter((objetivo) => objetivo.estado === 'activo').length
})

const objetivosRevision = computed(() => {
  return objetivos.value.filter((objetivo) => objetivo.estado === 'en_revision').length
})

const objetivosFinalizados = computed(() => {
  return objetivos.value.filter((objetivo) => objetivo.estado === 'finalizado').length
})

function textoEstado(estado) {
  const estados = {
    activo: 'Activo',
    en_revision: 'En revisión',
    finalizado: 'Finalizado',
    inactivo: 'Inactivo',
  }

  return estados[estado] || estado || 'Sin estado'
}

function estadoClase(estado) {
  const clases = {
    activo: 'ok',
    en_revision: 'warning',
    finalizado: 'finished',
    inactivo: 'neutral',
  }

  return clases[estado] || 'neutral'
}

function formatearFecha(fecha) {
  if (!fecha) {
    return 'No definida'
  }

  const [anio, mes, dia] = fecha.split('-')
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

function abrirNuevoObjetivo() {
  objetivoSeleccionado.value = null
  modalObjetivoAbierto.value = true
  error.value = ''
  mensaje.value = ''
}

function abrirEditarObjetivo(objetivo) {
  objetivoSeleccionado.value = objetivo
  modalObjetivoAbierto.value = true
  error.value = ''
  mensaje.value = ''
}

function abrirDetalleObjetivo(objetivo) {
  objetivoSeleccionado.value = objetivo
  modalDetalleAbierto.value = true
}

function cerrarModalObjetivo() {
  modalObjetivoAbierto.value = false
  objetivoSeleccionado.value = null
  guardandoObjetivo.value = false
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
  error.value = ''
  mensaje.value = ''

  try {
    if (objetivoSeleccionado.value?.id) {
      await actualizarObjetivo(objetivoSeleccionado.value.id, payload)
      mensaje.value = 'Objetivo actualizado correctamente.'
    } else {
      await crearObjetivo(payload)
      mensaje.value = 'Objetivo creado correctamente.'
    }

    cerrarModalObjetivo()
    await cargarDatos()
  } catch (e) {
    error.value = obtenerMensajeError(
      e,
      objetivoSeleccionado.value?.id
        ? 'No se pudo actualizar el objetivo.'
        : 'No se pudo crear el objetivo.'
    )
  } finally {
    guardandoObjetivo.value = false
  }
}

async function manejarInactivarObjetivo(objetivo) {
  const confirmar = window.confirm(
    `¿Seguro que querés inactivar el objetivo "${objetivo.nombre}"?`
  )

  if (!confirmar) return

  error.value = ''
  mensaje.value = ''

  try {
    await inactivarObjetivo(objetivo.id)
    mensaje.value = 'Objetivo inactivado correctamente.'
    await cargarDatos()
  } catch (e) {
    error.value = obtenerMensajeError(e, 'No se pudo inactivar el objetivo.')
  }
}

async function manejarReactivarObjetivo(objetivo) {
  error.value = ''
  mensaje.value = ''

  try {
    await reactivarObjetivo(objetivo.id)
    mensaje.value = 'Objetivo reactivado correctamente.'
    await cargarDatos()
  } catch (e) {
    error.value = obtenerMensajeError(e, 'No se pudo reactivar el objetivo.')
  }
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
    :usuario="props.usuario"
    titulo="Gestión de Objetivos Estratégicos"
    subtitulo="Administra los objetivos derivados de cada estrategia institucional."
    breadcrumb-actual="Objetivos"
    @logout="cerrarSesion"
  >
    <template v-if="puedeGestionar" #actions>
      <button class="btn-primary-page" type="button" @click="abrirNuevoObjetivo">
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

        Nuevo Objetivo
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
              <path d="M4 21V4a1 1 0 0 1 1-1h9l4 4v14" />
              <path d="M8 11h8" />
              <path d="M8 15h6" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ objetivos.length }}</div>
        <div class="kpi-label">Objetivos registrados</div>
        <div class="kpi-foot">Total creado en el sistema</div>
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

        <div class="kpi-value">{{ objetivosActivos }}</div>
        <div class="kpi-label">Activos</div>
        <div class="kpi-foot">En seguimiento actualmente</div>
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

        <div class="kpi-value">{{ objetivosRevision }}</div>
        <div class="kpi-label">En revisión</div>
        <div class="kpi-foot">Requieren validación</div>
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
              <path d="M20 6L9 17l-5-5" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ objetivosFinalizados }}</div>
        <div class="kpi-label">Finalizados</div>
        <div class="kpi-foot">Cumplieron su ciclo</div>
      </article>
    </section>

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
          placeholder="Buscar objetivo..."
        />
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">Estrategia:</span>

        <select v-model="estrategiaSeleccionada">
          <option value="">Todas</option>

          <option
            v-for="estrategia in estrategias"
            :key="estrategia.id"
            :value="estrategia.id"
          >
            {{ estrategia.nombre }}
          </option>
        </select>
      </div>

      <div class="toolbar-count">
        {{ objetivosFiltrados.length }} objetivos
      </div>
    </div>

    <section class="card-panel table-card">
      <div v-if="cargando" class="message">
        Cargando objetivos...
      </div>

      <div v-else-if="!objetivosFiltrados.length" class="empty-state">
        No hay objetivos para mostrar.
      </div>

      <table v-else>
        <thead>
          <tr>
            <th>Objetivo</th>
            <th>Estrategia asociada</th>
            <th>Creado por</th>
            <th>Estado</th>
            <th>Fecha inicio</th>
            <th>Fecha fin</th>
            <th style="text-align: right;">Acciones</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="objetivo in objetivosFiltrados"
            :key="objetivo.id"
          >
            <td>
              <div class="cell-main">
                {{ objetivo.nombre }}
              </div>

              <div class="cell-sub">
                {{ objetivo.descripcion || 'Sin descripción' }}
              </div>
            </td>

            <td>
              <span class="code-chip">
                {{ objetivo.estrategia_nombre || 'Sin estrategia' }}
              </span>
            </td>

            <td>
              <div class="owner-cell">
                <div class="avatar-table">
                  {{ inicialesUsuario(objetivo.creado_por_username) }}
                </div>

                {{ objetivo.creado_por_username || 'Sin usuario' }}
              </div>
            </td>

            <td>
              <span class="badge" :class="estadoClase(objetivo.estado)">
                <span class="badge-dot"></span>
                {{ textoEstado(objetivo.estado) }}
              </span>
            </td>

            <td>{{ formatearFecha(objetivo.fecha_inicio) }}</td>
            <td>{{ formatearFecha(objetivo.fecha_fin) }}</td>

            <td>
              <div class="actions-cell">
                <button
                  class="action-btn"
                  type="button"
                  @click="abrirDetalleObjetivo(objetivo)"
                >
                  Ver detalle
                </button>

                <button
                  v-if="puedeGestionar"
                  class="action-btn"
                  type="button"
                  @click="abrirEditarObjetivo(objetivo)"
                >
                  Editar
                </button>

                <button
                  v-if="puedeGestionar && objetivo.estado !== 'inactivo'"
                  class="action-btn danger"
                  type="button"
                  @click="manejarInactivarObjetivo(objetivo)"
                >
                  Inactivar
                </button>

                <button
                  v-if="puedeGestionar && objetivo.estado === 'inactivo'"
                  class="action-btn"
                  type="button"
                  @click="manejarReactivarObjetivo(objetivo)"
                >
                  Reactivar
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="table-footer">
        <div class="showing">
          Mostrando {{ objetivosFiltrados.length }} de {{ objetivos.length }} objetivos
        </div>

        <div class="pagination">
          <button class="page-btn" type="button" disabled>
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.4"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>

          <button class="page-btn active" type="button">
            1
          </button>

          <button class="page-btn" type="button" disabled>
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.4"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </div>
      </div>
    </section>

    <ModalBase
      :abierto="modalObjetivoAbierto"
      :titulo="objetivoSeleccionado ? 'Editar objetivo' : 'Nuevo objetivo'"
      :subtitulo="
        objetivoSeleccionado
          ? 'Actualiza los datos generales del objetivo.'
          : 'Registra un objetivo asociado a una estrategia.'
      "
      @cerrar="cerrarModalObjetivo"
    >
      <ObjetivoForm
        :objetivo="objetivoSeleccionado"
        :estrategias="estrategias"
        @guardar="guardarObjetivo"
        @cancelar="cerrarModalObjetivo"
      />

      <div v-if="guardandoObjetivo" class="saving-message">
        Guardando objetivo...
      </div>
    </ModalBase>

    <ModalBase
      :abierto="modalDetalleAbierto"
      titulo="Detalle del objetivo"
      subtitulo="Información general del objetivo seleccionado."
      @cerrar="cerrarModalDetalle"
    >
      <div v-if="objetivoSeleccionado" class="detail-grid">
        <div class="detail-item">
          <span>Estrategia</span>
          <strong>
            {{ objetivoSeleccionado.estrategia_nombre || objetivoSeleccionado.nombre_estrategia || 'Sin especificar' }}
          </strong>
        </div>

        <div class="detail-item">
          <span>Objetivo</span>
          <strong>{{ objetivoSeleccionado.nombre }}</strong>
        </div>

        <div class="detail-item">
          <span>Estado</span>
          <strong>{{ textoEstado(objetivoSeleccionado.estado) }}</strong>
        </div>

        <div class="detail-item">
          <span>Fecha inicio</span>
          <strong>{{ formatearFecha(objetivoSeleccionado.fecha_inicio) }}</strong>
        </div>

        <div class="detail-item">
          <span>Fecha fin</span>
          <strong>{{ formatearFecha(objetivoSeleccionado.fecha_fin) }}</strong>
        </div>

        <div class="detail-item detail-full">
          <span>Descripción</span>
          <strong>{{ objetivoSeleccionado.descripcion || 'Sin descripción registrada.' }}</strong>
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

.badge.finished {
  background: rgba(69, 123, 157, 0.12);
  color: #457b9d;
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
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
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

.pagination {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-btn {
  min-width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
  font-family: inherit;
  font-size: 12px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.page-btn svg {
  stroke: currentColor;
}

.page-btn.active {
  background: #1d3557;
  color: #ffffff;
  border-color: #1d3557;
}

.page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  table {
    display: block;
    overflow-x: auto;
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

  .table-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>