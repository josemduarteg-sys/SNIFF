<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import ConfirmacionModal from '../components/common/ConfirmacionModal.vue'
import IndicadorForm from '../components/indicadores/IndicadorForm.vue'
import IndicadorDetalle from '../components/indicadores/IndicadorDetalle.vue'
import {
  actualizarIndicador,
  actualizarPonderacionIndicador,
  anularIndicador,
  autorizarIndicador,
  crearIndicador,
  obtenerDatosFormularioIndicador,
  obtenerIndicadoresKpi,
  obtenerRangosKpi,
} from '../services/indicadorService'
import { formatearNumero } from '../utils/formato'
import { claseColorCumplimiento, textoEstadoCumplimiento } from '../utils/cumplimiento'
import { useConfirmacion } from '../composables/useConfirmacion'
import { usePaginacion } from '../composables/usePaginacion'
import Paginacion from '../components/common/Paginacion.vue'
import {
  puedeAnularKpi,
  puedeAutorizarKpi,
  puedeCrearKpi,
  puedeEditarKpi,
} from '../utils/permisos'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const route = useRoute()
const idResaltado = ref(null)
let timeoutResaltado = null

const indicadores = ref([])
const planesAnuales = ref([])
const objetivosGenerales = ref([])
const objetivosEspecificos = ref([])
const frecuencias = ref([])
const rangosKpi = ref([])

const busqueda = ref('')
const objetivoSeleccionado = ref('')
const frecuenciaSeleccionada = ref('')
const estadoSeleccionado = ref('')

const cargando = ref(false)
const procesandoId = ref(null)
const error = ref('')
const mensaje = ref('')

const {
  solicitud: confirmacion,
  solicitar: solicitarConfirmacion,
  cancelar: cancelarConfirmacion,
  confirmar: confirmarAccionPendiente,
} = useConfirmacion()

const modalAbierto = ref(false)
const indicadorSeleccionado = ref(null)
const guardando = ref(false)
const errorModalIndicador = ref('')

const modalDetalleAbierto = ref(false)
const indicadorDetalle = ref(null)

const puedeCrear = computed(() => puedeCrearKpi(props.usuario))
const puedeAutorizarRol = computed(() => puedeAutorizarKpi(props.usuario))
const puedeAnularRol = computed(() => puedeAnularKpi(props.usuario))
const puedeEditarRol = computed(() => puedeEditarKpi(props.usuario))
const mostrarAccionesKpi = computed(() => {
  return puedeAutorizarRol.value || puedeEditarRol.value || puedeAnularRol.value
})

async function cargarDatos() {
  cargando.value = true
  error.value = ''
  mensaje.value = ''

  try {
    const [indicadoresData, datosFormulario, rangosData] = await Promise.all([
      obtenerIndicadoresKpi(),
      obtenerDatosFormularioIndicador(),
      obtenerRangosKpi(),
    ])

    indicadores.value = indicadoresData
    planesAnuales.value = datosFormulario.planesAnuales
    objetivosGenerales.value = datosFormulario.objetivosGenerales
    objetivosEspecificos.value = datosFormulario.objetivosEspecificos
    frecuencias.value = datosFormulario.frecuencias
    rangosKpi.value = rangosData
  } catch (e) {
    error.value = 'No se pudieron cargar los indicadores KPI.'
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

const indicadoresFiltrados = computed(() => {
  const texto = busqueda.value.trim().toLowerCase()

  return indicadores.value.filter((indicador) => {
    const coincideBusqueda =
      !texto ||
      indicador.nombre?.toLowerCase().includes(texto) ||
      indicador.descripcion?.toLowerCase().includes(texto) ||
      indicador.objetivo_especifico_texto?.toLowerCase().includes(texto) ||
      indicador.plan_anual_nombre?.toLowerCase().includes(texto) ||
      indicador.frecuencia_nombre?.toLowerCase().includes(texto) ||
      indicador.estado?.toLowerCase().includes(texto)

    const coincideObjetivo =
      !objetivoSeleccionado.value ||
      Number(indicador.objetivo_especifico) === Number(objetivoSeleccionado.value)

    const coincideFrecuencia =
      !frecuenciaSeleccionada.value ||
      Number(indicador.frecuencia) === Number(frecuenciaSeleccionada.value)

    const coincideEstado =
      !estadoSeleccionado.value ||
      indicador.estado === estadoSeleccionado.value

    return (
      coincideBusqueda &&
      coincideObjetivo &&
      coincideFrecuencia &&
      coincideEstado
    )
  })
})

const hayFiltrosActivos = computed(() => {
  return (
    busqueda.value.trim() !== '' ||
    objetivoSeleccionado.value !== '' ||
    frecuenciaSeleccionada.value !== '' ||
    estadoSeleccionado.value !== ''
  )
})

function limpiarFiltros() {
  busqueda.value = ''
  objetivoSeleccionado.value = ''
  frecuenciaSeleccionada.value = ''
  estadoSeleccionado.value = ''
}

const {
  paginaActual,
  porPagina,
  totalResultados,
  totalPaginas,
  elementosVisibles: indicadoresPagina,
  rangoInicio,
  rangoFin,
  irAPagina,
} = usePaginacion(indicadoresFiltrados)

function cambiarPorPagina(valor) {
  porPagina.value = valor
}

const indicadoresBorrador = computed(() => {
  return indicadores.value.filter((indicador) => indicador.estado === 'borrador').length
})

const indicadoresAutorizados = computed(() => {
  return indicadores.value.filter((indicador) => indicador.estado === 'autorizado').length
})

const indicadoresAnulados = computed(() => {
  return indicadores.value.filter((indicador) => indicador.estado === 'anulado').length
})

function textoPromedioAcumulado(indicador) {
  if (indicador.promedio_acumulado === null || indicador.promedio_acumulado === undefined) {
    return 'Sin mediciones'
  }

  return formatearNumero(indicador.promedio_acumulado, { unidad: indicador.unidad_medida })
}

function textoEstado(estado) {
  const estados = {
    borrador: 'Borrador',
    autorizado: 'Autorizado',
    anulado: 'Anulado',
  }

  return estados[estado] || estado || 'Sin estado'
}

function estadoClase(estado) {
  const clases = {
    borrador: 'warning',
    autorizado: 'ok',
    anulado: 'danger',
  }

  return clases[estado] || 'neutral'
}

function puedeAutorizar(indicador) {
  return indicador.estado === 'borrador'
}

function puedeAnular(indicador) {
  return indicador.estado !== 'anulado'
}

function puedeEditar(indicador) {
  return puedeEditarKpi(props.usuario, indicador)
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
      'No se pudo autorizar el KPI. Verificá que tenga una meta configurada.'
  } finally {
    procesandoId.value = null
  }
}

function manejarAnular(indicador) {
  if (!puedeAnular(indicador)) {
    return
  }

  solicitarConfirmacion({
    titulo: 'Anular KPI',
    mensaje: `¿Deseás anular el KPI "${indicador.nombre}"?`,
    textoSecundario: 'Esta acción no elimina el registro, solo lo marca como anulado.',
    textoConfirmar: 'Anular',
    variante: 'peligrosa',
    accion: () => ejecutarAnular(indicador),
  })
}

async function ejecutarAnular(indicador) {
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

function abrirNuevoIndicador() {
  indicadorSeleccionado.value = null
  modalAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalIndicador.value = ''
}

function abrirEditarIndicador(indicador) {
  if (!puedeEditar(indicador)) {
    mensaje.value = ''
    error.value = 'Este KPI ya está autorizado y no permite modificar sus datos principales.'
    return
  }

  indicadorSeleccionado.value = indicador
  modalAbierto.value = true
  error.value = ''
  mensaje.value = ''
  errorModalIndicador.value = ''
}

function cerrarModal() {
  modalAbierto.value = false
  indicadorSeleccionado.value = null
  guardando.value = false
  errorModalIndicador.value = ''
}

const rangosDelIndicadorDetalle = computed(() => {
  if (!indicadorDetalle.value) {
    return []
  }

  return rangosKpi.value.filter((rango) => {
    return Number(rango.indicador) === Number(indicadorDetalle.value.id)
  })
})

function abrirDetalleIndicador(indicador) {
  indicadorDetalle.value = indicador
  modalDetalleAbierto.value = true
}

function cerrarModalDetalle() {
  modalDetalleAbierto.value = false
  indicadorDetalle.value = null
}

async function guardarIndicador(payload) {
  guardando.value = true
  errorModalIndicador.value = ''
  mensaje.value = ''

  try {
    if (payload.soloPonderacion) {
      // KPI ya autorizado: solo se reenvía la ponderación (Bloque 3,
      // segunda parte — ver IndicadorForm.vue).
      await actualizarPonderacionIndicador(indicadorSeleccionado.value.id, payload.ponderacion)
      mensaje.value = 'Ponderación actualizada correctamente.'
    } else if (indicadorSeleccionado.value?.id) {
      await actualizarIndicador(indicadorSeleccionado.value.id, payload)
      mensaje.value = 'KPI actualizado correctamente.'
    } else {
      await crearIndicador(payload)
      mensaje.value = 'KPI creado correctamente.'
    }

    cerrarModal()
    await cargarDatos()
  } catch (e) {
    // El error se muestra DENTRO del modal (no en la vista principal) para
    // que el usuario vea qué falló sin perder el modal ni lo ya escrito:
    // el modal solo se cierra en el bloque de éxito de arriba.
    const data = e.response?.data

    if (data?.non_field_errors) {
      errorModalIndicador.value = data.non_field_errors.join(' ')
    } else if (data?.detail) {
      errorModalIndicador.value = data.detail
    } else if (typeof data === 'object' && data !== null) {
      const primerCampo = Object.keys(data)[0]
      const mensajeCampo = data[primerCampo]
      errorModalIndicador.value = Array.isArray(mensajeCampo)
        ? mensajeCampo.join(' ')
        : String(mensajeCampo)
    } else {
      errorModalIndicador.value = indicadorSeleccionado.value?.id
        ? 'No se pudo actualizar el KPI.'
        : 'No se pudo crear el KPI.'
    }
  } finally {
    guardando.value = false
  }
}

function cerrarSesion() {
  emit('logout')
}

onMounted(async () => {
  await cargarDatos()
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
    titulo="Gestión de Indicadores KPI"
    subtitulo="Administra indicadores, fórmulas de medición, metas, frecuencia y estado de autorización."
    breadcrumb-actual="Indicadores KPI"
    @logout="cerrarSesion"
  >
    <template #actions>
      <button v-if="puedeCrear" class="btn-primary-page" type="button" @click="abrirNuevoIndicador">
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
        <div class="kpi-label">Activos</div>
        <div class="kpi-foot">Listos para seguimiento</div>
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

        <div class="kpi-value">{{ indicadoresAnulados }}</div>
        <div class="kpi-label">Anulados</div>
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
        <span class="filter-label">Objetivo específico:</span>

        <select v-model="objetivoSeleccionado">
          <option value="">Todos</option>

          <option
            v-for="objetivo in objetivosEspecificos"
            :key="objetivo.id"
            :value="objetivo.id"
          >
            {{ objetivo.texto_objetivo }}
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
        <span class="filter-label">Estado:</span>

        <select v-model="estadoSeleccionado">
          <option value="">Todos</option>
          <option value="borrador">Borrador</option>
          <option value="autorizado">Autorizado</option>
          <option value="anulado">Anulado</option>
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
        {{ indicadoresFiltrados.length }} KPI
      </div>
    </div>

    <section class="card-panel table-card">
      <div v-if="cargando" class="message">
        Cargando indicadores KPI...
      </div>

      <div v-else-if="!indicadores.length" class="empty-state">
        No hay indicadores KPI para mostrar.
      </div>

      <div v-else-if="!indicadoresFiltrados.length" class="empty-state">
        No se encontraron resultados con los filtros aplicados.
      </div>

      <div v-else class="table-scroll">
      <table>
        <colgroup>
          <col style="width: 18%">
          <col style="width: 13%">
          <col style="width: 9%">
          <col style="width: 11%">
          <col style="width: 8%">
          <col style="width: 10%">
          <col style="width: 9%">
          <col style="width: 22%">
        </colgroup>
        <thead>
          <tr>
            <th>Indicador KPI</th>
            <th>Objetivo específico</th>
            <th>Meta</th>
            <th>Plan anual</th>
            <th>Frecuencia</th>
            <th title="Promedio directo de los resultados registrados de este KPI, con su estado según sus propios rangos de cumplimiento.">Promedio acumulado</th>
            <th>Estado</th>
            <th class="th-acciones" style="text-align: right;">Acciones</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="indicador in indicadoresPagina"
            :key="indicador.id"
            :id="`fila-${indicador.id}`"
            :class="{ 'highlight-row': idResaltado === Number(indicador.id) }"
          >
            <td>
              <div class="cell-main" :title="indicador.nombre">
                {{ indicador.nombre }}
              </div>

              <div class="cell-sub" :title="indicador.descripcion || 'Sin descripción'">
                {{ indicador.descripcion || 'Sin descripción' }}
              </div>

              <div class="cell-extra">
                Unidad: {{ indicador.unidad_medida || '-' }}
              </div>
            </td>

            <td>
              <span class="code-chip" :title="indicador.objetivo_especifico_texto || 'Sin objetivo'">
                {{ indicador.objetivo_especifico_texto || 'Sin objetivo' }}
              </span>
              <div class="cell-sub" :title="indicador.objetivo_general_texto || ''">
                {{ indicador.objetivo_general_texto || '' }}
              </div>
            </td>

            <td>
              <div class="meta-value">
                {{ formatearNumero(indicador.valor_meta) }}
              </div>
              <div class="cell-sub">
                {{ indicador.unidad_medida || 'unidad' }}
              </div>
              <div class="cell-extra">
                Ponderación: {{ indicador.ponderacion != null ? `${indicador.ponderacion}%` : 'Sin ponderar' }}
              </div>
            </td>

            <td>
              <div class="date-range">
                <span>{{ indicador.plan_anual_nombre || 'Sin plan anual' }}</span>
                <small>{{ indicador.plan_estrategico_titulo || '' }}</small>
              </div>
            </td>

            <td>
              {{ indicador.frecuencia_nombre || 'Sin frecuencia' }}
            </td>

            <td>
              <div class="meta-value">
                {{ textoPromedioAcumulado(indicador) }}
              </div>

              <span
                v-if="indicador.promedio_acumulado !== null && indicador.promedio_acumulado !== undefined"
                class="badge"
                :class="claseColorCumplimiento(indicador.estado_acumulado_color)"
                :title="textoEstadoCumplimiento(indicador.estado_acumulado_nombre)"
              >
                <span class="badge-dot"></span>
                <span class="badge-text">{{ textoEstadoCumplimiento(indicador.estado_acumulado_nombre) }}</span>
              </span>

              <div v-else class="cell-sub">
                {{ indicador.cantidad_mediciones }} mediciones
              </div>
            </td>

            <td>
              <span class="badge" :class="estadoClase(indicador.estado)" :title="textoEstado(indicador.estado)">
                <span class="badge-dot"></span>
                <span class="badge-text">{{ textoEstado(indicador.estado) }}</span>
              </span>

              <div v-if="indicador.autorizado_por_username" class="cell-sub">
                Por {{ indicador.autorizado_por_username }}
              </div>
            </td>

            <td class="td-acciones">
              <div class="actions-cell">
                <button
                  class="action-icon-btn"
                  type="button"
                  title="Ver detalle"
                  aria-label="Ver detalle"
                  @click="abrirDetalleIndicador(indicador)"
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
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>

                <button
                  v-if="puedeAutorizarRol"
                  class="action-text-btn ok"
                  type="button"
                  title="Autorizar KPI"
                  :disabled="!puedeAutorizar(indicador) || procesandoId === indicador.id"
                  @click="manejarAutorizar(indicador)"
                >
                  Autorizar
                </button>

                <button
                  v-if="puedeEditarRol"
                  class="action-icon-btn"
                  type="button"
                  title="Editar"
                  aria-label="Editar"
                  :class="{ disabled: !puedeEditar(indicador) }"
                  :disabled="procesandoId === indicador.id"
                  @click="abrirEditarIndicador(indicador)"
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
                  v-if="puedeAnularRol"
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

                <span v-if="!mostrarAccionesKpi" class="readonly-chip">
                  Solo lectura
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <Paginacion
        v-if="indicadoresFiltrados.length"
        :pagina-actual="paginaActual"
        :total-paginas="totalPaginas"
        :por-pagina="porPagina"
        :rango-inicio="rangoInicio"
        :rango-fin="rangoFin"
        :total-resultados="totalResultados"
        etiqueta="KPI"
        @cambiar-pagina="irAPagina"
        @cambiar-por-pagina="cambiarPorPagina"
      />
    </section>

    <ModalBase
      :abierto="modalAbierto"
      :titulo="indicadorSeleccionado ? 'Editar KPI' : 'Nuevo KPI'"
      :subtitulo="
        indicadorSeleccionado
          ? 'Actualiza los datos principales del indicador mientras esté en borrador.'
          : 'Registra un KPI con fórmula de medición, meta y frecuencia.'
      "
      @cerrar="cerrarModal"
    >
      <div v-if="errorModalIndicador" class="alert error">
        {{ errorModalIndicador }}
      </div>

      <IndicadorForm
        :indicador="indicadorSeleccionado"
        :planes-anuales="planesAnuales"
        :objetivos-generales="objetivosGenerales"
        :objetivos-especificos="objetivosEspecificos"
        :frecuencias="frecuencias"
        :indicadores="indicadores"
        @guardar="guardarIndicador"
        @cancelar="cerrarModal"
      />

      <div v-if="guardando" class="saving-message">
        Guardando KPI...
      </div>
    </ModalBase>

    <ModalBase
      :abierto="modalDetalleAbierto"
      titulo="Detalle de KPI"
      subtitulo="Información completa del indicador y sus criterios de cumplimiento."
      @cerrar="cerrarModalDetalle"
    >
      <IndicadorDetalle
        v-if="indicadorDetalle"
        :indicador="indicadorDetalle"
        :rangos="rangosDelIndicadorDetalle"
      />
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

.table-scroll {
  /* Red de seguridad: table-layout:fixed + colgroup ya reparte el 100%
     del ancho disponible entre columnas (Acciones incluida) sin que la
     tabla se salga del card en anchos normales (>=1366px). Este scroll
     solo se activa si min-width fuerza a la tabla a ser más angosta que
     el contenedor (ventanas muy angostas), en vez de cortar botones. */
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 860px;
  border-collapse: collapse;
  table-layout: fixed;
}

.th-acciones,
.td-acciones {
  /* El ancho real lo define el <colgroup> (22%, calculado para alcanzar
     siempre a Ver + Autorizar + Editar + Anular sin cortarse). white-space
     evita que los botones bajen a una segunda línea y deformen la fila. */
  white-space: nowrap;
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
  /* table-layout:fixed no recorta por sí solo el contenido más ancho que
     su columna: sin esto, un valor que no entra se dibuja encima de la
     columna vecina en vez de truncarse dentro de la suya. */
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
  max-width: 280px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-sub {
  font-size: 11.5px;
  color: #9aa8b8;
  font-weight: 500;
  margin-top: 3px;
  max-width: 460px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.readonly-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 9px;
  background: rgba(154, 168, 184, 0.16);
  color: #5e6e82;
  font-size: 11.5px;
  font-weight: 800;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  min-width: 0;
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 20px;
  white-space: nowrap;
}

.badge-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
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
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.actions-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: nowrap;
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

.saving-message {
  margin-top: 12px;
  padding: 11px 13px;
  border-radius: 11px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 12.5px;
  font-weight: 800;
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
