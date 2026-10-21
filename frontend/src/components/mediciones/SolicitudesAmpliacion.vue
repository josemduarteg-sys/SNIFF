<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import ModalBase from '../ui/ModalBase.vue'
import {
  autorizarSolicitudAmpliacion,
  obtenerSolicitudesAmpliacion,
  rechazarSolicitudAmpliacion,
  retirarSolicitudAmpliacion,
} from '../../services/solicitudAmpliacionService'
import {
  ESTADOS_AMPLIACION,
  contarPorEstado,
  datosEstadoAmpliacion,
  diasValidos,
  formatearFechaIso,
  sumarDias,
} from '../../utils/ampliaciones'

// Etapa 5: el Administrador de planificación ve y resuelve todas las
// solicitudes; el Ejecutor operativo ve solo las suyas (el backend filtra)
// y puede retirar las pendientes.

const props = defineProps({
  esAdmin: {
    type: Boolean,
    required: true,
  },
  resaltarId: {
    type: Number,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['actualizado'])

const solicitudes = ref([])
const cargando = ref(false)
const error = ref('')
const mensaje = ref('')
const filtroEstado = ref(props.esAdmin ? 'pendiente' : '')
const resaltada = ref(null)

const resolucion = reactive({
  abierta: false,
  tipo: '',
  solicitud: null,
  dias: 1,
  observacion: '',
  guardando: false,
  error: '',
})

const conteos = computed(() => contarPorEstado(solicitudes.value))

const solicitudesFiltradas = computed(() => {
  if (!filtroEstado.value) return solicitudes.value
  return solicitudes.value.filter((solicitud) => solicitud.estado === filtroEstado.value)
})

const nuevoPlazoAutorizado = computed(() => {
  const solicitud = resolucion.solicitud
  if (!solicitud || !diasValidos(resolucion.dias, 1, solicitud.dias_solicitados)) return null
  return sumarDias(solicitud.fecha_limite_ordinaria, resolucion.dias)
})

const puedeConfirmar = computed(() => {
  if (resolucion.guardando || !resolucion.solicitud) return false

  if (resolucion.tipo === 'rechazar') return resolucion.observacion.trim() !== ''

  const minimo = resolucion.solicitud.dias_minimos_autorizables || 1
  return diasValidos(resolucion.dias, minimo, resolucion.solicitud.dias_solicitados)
})

async function cargar() {
  cargando.value = true
  error.value = ''

  try {
    solicitudes.value = await obtenerSolicitudesAmpliacion()
    emit('actualizado', contarPorEstado(solicitudes.value))
  } catch (e) {
    error.value = 'No se pudieron cargar las solicitudes de días adicionales.'
  } finally {
    cargando.value = false
  }
}

function sePuedeResolver(solicitud) {
  return solicitud.estado === 'pendiente' && !solicitud.plazo_resolucion_vencido
}

function abrirResolucion(tipo, solicitud) {
  mensaje.value = ''
  Object.assign(resolucion, {
    abierta: true,
    tipo,
    solicitud,
    dias: solicitud.dias_solicitados,
    observacion: '',
    guardando: false,
    error: '',
  })
}

function cerrarResolucion() {
  resolucion.abierta = false
  resolucion.solicitud = null
}

function mensajeDeError(e, porDefecto) {
  const data = e.response?.data
  if (data?.detail) return data.detail
  if (data && typeof data === 'object') return Object.values(data).flat().join(' ')
  return porDefecto
}

async function confirmarResolucion() {
  if (!puedeConfirmar.value) return

  resolucion.guardando = true
  resolucion.error = ''

  try {
    if (resolucion.tipo === 'autorizar') {
      await autorizarSolicitudAmpliacion(resolucion.solicitud.id, {
        dias_autorizados: Number(resolucion.dias),
        observacion: resolucion.observacion.trim(),
      })
      mensaje.value = 'Solicitud autorizada. Se avisó al solicitante con el nuevo plazo.'
    } else {
      await rechazarSolicitudAmpliacion(resolucion.solicitud.id, {
        observacion: resolucion.observacion.trim(),
      })
      mensaje.value = 'Solicitud rechazada. Se avisó al solicitante.'
    }

    cerrarResolucion()
    await cargar()
  } catch (e) {
    resolucion.error = mensajeDeError(e, 'No se pudo resolver la solicitud.')
  } finally {
    resolucion.guardando = false
  }
}

async function retirar(solicitud) {
  if (!window.confirm(`¿Retirar la solicitud de días adicionales del KPI "${solicitud.indicador_nombre}"?`)) return

  error.value = ''
  mensaje.value = ''

  try {
    await retirarSolicitudAmpliacion(solicitud.id)
    mensaje.value = 'Solicitud retirada. Queda en el historial como "Retirada".'
    await cargar()
  } catch (e) {
    error.value = mensajeDeError(e, 'No se pudo retirar la solicitud.')
  }
}

async function resaltarDesdeRuta() {
  if (!props.resaltarId) return

  filtroEstado.value = ''
  resaltada.value = props.resaltarId
  await nextTick()
  document.getElementById(`fila-ampliacion-${props.resaltarId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

onMounted(async () => {
  await cargar()
  await resaltarDesdeRuta()
})

defineExpose({ cargar })
</script>

<template>
  <div class="solicitudes-ampliacion">
    <div class="filtros-estado">
      <button
        type="button"
        class="chip-estado"
        :class="{ active: filtroEstado === '' }"
        @click="filtroEstado = ''"
      >
        Todas ({{ solicitudes.length }})
      </button>
      <button
        v-for="estadoItem in ESTADOS_AMPLIACION"
        :key="estadoItem.valor"
        type="button"
        class="chip-estado"
        :class="{ active: filtroEstado === estadoItem.valor }"
        @click="filtroEstado = estadoItem.valor"
      >
        {{ estadoItem.nombre }} ({{ conteos[estadoItem.valor] }})
      </button>
    </div>

    <div v-if="mensaje" class="alert success">{{ mensaje }}</div>
    <div v-if="error" class="alert error">{{ error }}</div>

    <section class="card-panel">
      <div v-if="cargando" class="message">Cargando solicitudes...</div>

      <div v-else-if="!solicitudes.length" class="message">
        {{ esAdmin ? 'Todavía no hay solicitudes de días adicionales.' : 'Todavía no hiciste solicitudes de días adicionales.' }}
      </div>

      <div v-else-if="!solicitudesFiltradas.length" class="message">
        No hay solicitudes con este estado.
      </div>

      <div v-else class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>KPI y periodo</th>
              <th v-if="esAdmin">Solicitante</th>
              <th>Días</th>
              <th>Plazo original</th>
              <th>Plazo solicitado</th>
              <th>Plazo autorizado</th>
              <th>Estado</th>
              <th>Motivo y resolución</th>
              <th class="th-acciones">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="solicitud in solicitudesFiltradas"
              :id="`fila-ampliacion-${solicitud.id}`"
              :key="solicitud.id"
              :class="{ 'highlight-row': resaltada === solicitud.id }"
            >
              <td>
                <div class="cell-main" :title="solicitud.indicador_nombre">{{ solicitud.indicador_nombre }}</div>
                <div class="cell-sub">
                  {{ solicitud.periodo_nombre }} · cierre {{ formatearFechaIso(solicitud.periodo_fecha_cierre) }}
                </div>
              </td>
              <td v-if="esAdmin">
                <div class="cell-main">{{ solicitud.solicitante_nombre }}</div>
                <div class="cell-sub">{{ formatearFechaIso(solicitud.fecha_solicitud) }}</div>
              </td>
              <td>
                <div class="cell-main">{{ solicitud.dias_solicitados }} pedido(s)</div>
                <div v-if="solicitud.dias_autorizados" class="cell-sub">{{ solicitud.dias_autorizados }} autorizado(s)</div>
              </td>
              <td>{{ formatearFechaIso(solicitud.fecha_limite_ordinaria) }}</td>
              <td>{{ formatearFechaIso(solicitud.fecha_limite_solicitada) }}</td>
              <td>
                <strong v-if="solicitud.fecha_limite_extraordinaria">
                  {{ formatearFechaIso(solicitud.fecha_limite_extraordinaria) }}
                </strong>
                <span v-else class="cell-sub">—</span>
              </td>
              <td>
                <span class="badge" :class="datosEstadoAmpliacion(solicitud.estado).clase">
                  <span class="badge-dot"></span>
                  {{ solicitud.estado_nombre }}
                </span>
                <div v-if="solicitud.estado === 'pendiente'" class="cell-sub">
                  <template v-if="solicitud.plazo_resolucion_vencido">
                    Venció el plazo para resolverla
                  </template>
                  <template v-else>
                    Resolver hasta el {{ formatearFechaIso(solicitud.fecha_limite_maxima) }}
                  </template>
                </div>
              </td>
              <td>
                <div class="cell-texto" :title="solicitud.motivo">{{ solicitud.motivo }}</div>
                <div v-if="solicitud.observacion_revision" class="cell-sub" :title="solicitud.observacion_revision">
                  {{ solicitud.revisado_por_username ? `${solicitud.revisado_por_username}: ` : '' }}{{ solicitud.observacion_revision }}
                </div>
              </td>
              <td class="td-acciones">
                <div class="actions-cell">
                  <template v-if="esAdmin && sePuedeResolver(solicitud)">
                    <button class="btn-accion ok" type="button" @click="abrirResolucion('autorizar', solicitud)">
                      Autorizar
                    </button>
                    <button class="btn-accion danger" type="button" @click="abrirResolucion('rechazar', solicitud)">
                      Rechazar
                    </button>
                  </template>
                  <button
                    v-else-if="!esAdmin && sePuedeResolver(solicitud)"
                    class="btn-accion"
                    type="button"
                    @click="retirar(solicitud)"
                  >
                    Retirar
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <ModalBase
      :abierto="resolucion.abierta"
      :titulo="resolucion.tipo === 'autorizar' ? 'Autorizar días adicionales' : 'Rechazar solicitud'"
      :subtitulo="resolucion.solicitud ? `${resolucion.solicitud.indicador_nombre} — ${resolucion.solicitud.periodo_nombre}` : ''"
      ancho="560px"
      @cerrar="cerrarResolucion"
    >
      <form v-if="resolucion.solicitud" class="resolucion-form" @submit.prevent="confirmarResolucion">
        <section class="contexto">
          <div><span>Solicitante</span><strong>{{ resolucion.solicitud.solicitante_nombre }}</strong></div>
          <div><span>Días solicitados</span><strong>{{ resolucion.solicitud.dias_solicitados }}</strong></div>
          <div><span>Plazo original</span><strong>{{ formatearFechaIso(resolucion.solicitud.fecha_limite_ordinaria) }}</strong></div>
          <div><span>Plazo solicitado</span><strong>{{ formatearFechaIso(resolucion.solicitud.fecha_limite_solicitada) }}</strong></div>
          <div class="full"><span>Motivo</span><strong class="texto-largo">{{ resolucion.solicitud.motivo }}</strong></div>
        </section>

        <template v-if="resolucion.tipo === 'autorizar'">
          <label for="dias-autorizados">Días a autorizar</label>
          <input
            id="dias-autorizados"
            v-model.number="resolucion.dias"
            type="number"
            :min="resolucion.solicitud.dias_minimos_autorizables || 1"
            :max="resolucion.solicitud.dias_solicitados"
            step="1"
          />
          <small>
            Entre {{ resolucion.solicitud.dias_minimos_autorizables || 1 }} y {{ resolucion.solicitud.dias_solicitados }}.
            Nuevo plazo de registro:
            <strong>{{ nuevoPlazoAutorizado ? formatearFechaIso(nuevoPlazoAutorizado) : '—' }}</strong>.
            <template v-if="(resolucion.solicitud.dias_minimos_autorizables || 1) > 1">
              El plazo ordinario ya venció: con menos días el nuevo plazo ya habría pasado.
            </template>
          </small>

          <label for="observacion-autorizar">Observación (opcional)</label>
          <textarea id="observacion-autorizar" v-model="resolucion.observacion" maxlength="2000"></textarea>
        </template>

        <template v-else>
          <label for="observacion-rechazo">Motivo del rechazo</label>
          <textarea
            id="observacion-rechazo"
            v-model="resolucion.observacion"
            maxlength="2000"
            placeholder="Obligatorio: el solicitante lo recibe en su aviso."
          ></textarea>
        </template>

        <div v-if="resolucion.error" class="alert error">{{ resolucion.error }}</div>

        <div class="form-actions">
          <button class="btn-secondary" type="button" :disabled="resolucion.guardando" @click="cerrarResolucion">
            Cancelar
          </button>
          <button
            class="btn-primary"
            :class="{ peligro: resolucion.tipo === 'rechazar' }"
            type="submit"
            :disabled="!puedeConfirmar"
          >
            {{ resolucion.guardando ? 'Guardando...' : resolucion.tipo === 'autorizar' ? 'Autorizar' : 'Rechazar' }}
          </button>
        </div>
      </form>
    </ModalBase>
  </div>
</template>

<style scoped>
.filtros-estado {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.chip-estado {
  height: 32px;
  padding: 0 12px;
  border-radius: 16px;
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
  font-family: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.chip-estado.active {
  background: #1d3557;
  border-color: #1d3557;
  color: #ffffff;
}

.alert {
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 16px;
}

.alert.success { background: rgba(42, 157, 143, 0.12); color: #2a9d8f; }
.alert.error { background: rgba(231, 111, 81, 0.12); color: #e76f51; }

.card-panel {
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 14px;
  box-shadow: 0 2px 10px rgba(29, 53, 87, 0.05), 0 1px 2px rgba(29, 53, 87, 0.04);
  padding: 20px 22px 18px;
  margin-bottom: 20px;
}

.message {
  padding: 16px;
  border-radius: 12px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 13px;
  font-weight: 700;
}

.table-scroll { overflow-x: auto; }
table { width: 100%; min-width: 980px; border-collapse: collapse; }

thead th {
  text-align: left;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: #9aa8b8;
  padding: 0 10px 10px;
  border-bottom: 1px solid #e4eaef;
  white-space: nowrap;
}

tbody td {
  padding: 12px 10px;
  font-size: 13px;
  color: #1d3557;
  border-bottom: 1px solid #f1f4f7;
  vertical-align: top;
}

tbody tr:last-child td { border-bottom: none; }

.cell-main { font-weight: 800; max-width: 240px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cell-sub { font-size: 11.5px; color: #9aa8b8; font-weight: 500; margin-top: 3px; }
.cell-texto { max-width: 260px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.th-acciones, .td-acciones { text-align: right; white-space: nowrap; }
.actions-cell { display: flex; justify-content: flex-end; gap: 6px; }

.btn-accion {
  height: 30px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
  font-family: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.btn-accion.ok { color: #2a9d8f; border-color: rgba(42, 157, 143, 0.35); }
.btn-accion.danger { color: #e76f51; border-color: rgba(231, 111, 81, 0.35); }
.btn-accion:hover { background: #f4f7f9; }

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

.badge.ok { background: rgba(42, 157, 143, 0.12); color: #2a9d8f; }
.badge.warning { background: rgba(244, 162, 97, 0.16); color: #b9701e; }
.badge.danger { background: rgba(231, 111, 81, 0.12); color: #e76f51; }
.badge.neutral { background: rgba(154, 168, 184, 0.16); color: #5e6e82; }
.badge-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

.resolucion-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resolucion-form label {
  color: #1d3557;
  font-size: 12px;
  font-weight: 800;
  margin-top: 6px;
}

.resolucion-form input,
.resolucion-form textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  padding: 0 12px;
  font-family: inherit;
  color: #1d3557;
  outline: none;
}

.resolucion-form input { height: 40px; max-width: 140px; }
.resolucion-form textarea { min-height: 84px; padding-top: 10px; resize: vertical; }
.resolucion-form small { color: #7f8fa3; font-size: 11.5px; font-weight: 600; line-height: 1.4; }

.contexto {
  display: grid;
  grid-template-columns: repeat(2, minmax(140px, 1fr));
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  background: #f6f9fa;
  border: 1px solid #e4eaef;
}

.contexto div { display: flex; flex-direction: column; gap: 3px; }
.contexto .full { grid-column: 1 / -1; }
.contexto span { color: #9aa8b8; font-size: 11px; font-weight: 800; text-transform: uppercase; }
.contexto strong { color: #1d3557; font-size: 13px; }
.texto-largo { font-weight: 600; white-space: pre-wrap; }

.form-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px; }

.btn-primary,
.btn-secondary {
  height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.btn-primary { border: none; background: #1d3557; color: #ffffff; }
.btn-primary.peligro { background: #e76f51; }
.btn-secondary { border: 1.5px solid #e4eaef; background: #ffffff; color: #5e6e82; }
.btn-primary:disabled, .btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }

.highlight-row { animation: resaltar 3.5s ease; }

@keyframes resaltar {
  0%, 45% { background: rgba(244, 162, 97, 0.2); box-shadow: inset 4px 0 0 #f4a261; }
  100% { background: transparent; box-shadow: none; }
}

@media (max-width: 640px) {
  .contexto { grid-template-columns: 1fr; }
}
</style>
