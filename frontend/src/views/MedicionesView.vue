<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '../components/layout/AppLayout.vue'
import ModalBase from '../components/ui/ModalBase.vue'
import MedicionForm from '../components/mediciones/MedicionForm.vue'
import MedicionDetalle from '../components/mediciones/MedicionDetalle.vue'
import SolicitudAmpliacionForm from '../components/mediciones/SolicitudAmpliacionForm.vue'
import SolicitudesAmpliacion from '../components/mediciones/SolicitudesAmpliacion.vue'
import { obtenerSolicitudesAmpliacion } from '../services/solicitudAmpliacionService'
import { obtenerAlerta } from '../services/alertaService'
import {
  alertaCorresponde,
  kpiDisponible,
  leerParametrosNotificacion,
} from '../utils/navegacionNotificaciones'
import {
  obtenerDatosFormularioMedicion,
  obtenerMediciones,
} from '../services/medicionService'
import {
  actualizarConfiguracionMediciones,
  obtenerConfiguracionMediciones,
} from '../services/configuracionMedicionesService'
import {
  esAdministradorPlanificacion,
  puedeEditarMedicion,
  puedeRegistrarMedicion,
  puedeSolicitarAmpliacion,
  puedeVerSolicitudesAmpliacion,
} from '../utils/permisos'
import { formatearNumero, formatearDiferencia } from '../utils/formato'
import {
  SIN_REGISTRO,
  claseColorCumplimiento,
  esMedicionSinRegistro,
  textoEstadoCumplimiento,
} from '../utils/cumplimiento'
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

const route = useRoute()
const { idResaltado, aplicarResaltadoDesdeRuta } = useResaltado(route)

const emit = defineEmits(['logout'])

const mediciones = ref([])
const indicadores = ref([])
const estadosCumplimiento = ref([])

const busqueda = ref('')
const indicadorSeleccionado = ref('')
const estadoSeleccionado = ref('')

const cargando = ref(false)
const error = ref('')
const mostrarModal = ref(false)
const medicionSeleccionada = ref(null)
const mensajeExito = ref('')
const mostrarModalDetalle = ref(false)
const medicionDetalle = ref(null)

const puedeRegistrar = computed(() => puedeRegistrarMedicion(props.usuario))
const esAdmin = computed(() => esAdministradorPlanificacion(props.usuario))

// Etapa 5: días adicionales. Pestaña propia en esta misma pantalla, solo
// para Ejecutor operativo (sus solicitudes) y Administrador de
// planificación (todas); los demás roles no la ven.
const router = useRouter()
const puedeSolicitar = computed(() => puedeSolicitarAmpliacion(props.usuario))
const verSolicitudes = computed(() => puedeVerSolicitudesAmpliacion(props.usuario))
const tabActiva = ref('mediciones')
const solicitudesPendientes = ref(0)
const mostrarModalAmpliacion = ref(false)
const claveSolicitudes = ref(0)
const solicitudResaltada = computed(() => Number(route.query.solicitud) || null)
const tituloTabSolicitudes = computed(() => (esAdmin.value ? 'Solicitudes de ampliación' : 'Mis solicitudes'))

async function contarSolicitudesPendientes() {
  if (!verSolicitudes.value) return

  try {
    solicitudesPendientes.value = (await obtenerSolicitudesAmpliacion({ estado: 'pendiente' })).length
  } catch (e) {
    solicitudesPendientes.value = 0
  }
}

function actualizarConteoSolicitudes(conteos) {
  solicitudesPendientes.value = conteos.pendiente
}

async function cambiarTab(tab) {
  tabActiva.value = tab
  await router.replace({ path: '/mediciones', query: tab === 'solicitudes' ? { tab: 'solicitudes' } : {} })
}

function abrirModalAmpliacion() {
  mensajeExito.value = ''
  mostrarModalAmpliacion.value = true
}

async function manejarSolicitudEnviada() {
  mostrarModalAmpliacion.value = false
  mensajeExito.value = 'Solicitud de días adicionales enviada. Te vamos a avisar cuando se resuelva.'
  await contarSolicitudesPendientes()
  claveSolicitudes.value += 1
  await cambiarTab('solicitudes')
}

// Etapa 6: enlaces de las notificaciones (/mediciones?indicador=X&alerta=Y).
// Aplica el filtro del KPI y muestra la alerta relacionada. Un parámetro
// inválido, un KPI que el usuario no ve o una alerta inexistente (o de otro
// KPI) solo producen un aviso genérico: no se muestra nada que no esté ya
// disponible para el usuario.
const alertaNotificacion = ref(null)
const avisoNotificacion = ref('')

async function aplicarParametrosNotificacion() {
  const parametros = leerParametrosNotificacion(route.query)

  alertaNotificacion.value = null
  avisoNotificacion.value = ''

  if (!parametros.hayParametros) return

  if (parametros.invalidos) {
    avisoNotificacion.value = 'El enlace de la notificación no es válido. Se muestran todas las mediciones.'
    return
  }

  if (parametros.indicador) {
    if (kpiDisponible(parametros.indicador, indicadores.value, mediciones.value)) {
      indicadorSeleccionado.value = parametros.indicador
    } else {
      avisoNotificacion.value = 'El KPI de la notificación no está disponible. Se muestran todas las mediciones.'
      return
    }
  }

  if (parametros.alerta) {
    try {
      const alerta = await obtenerAlerta(parametros.alerta)

      if (alertaCorresponde(alerta, parametros.indicador)) {
        alertaNotificacion.value = alerta
      } else {
        avisoNotificacion.value = 'La alerta de la notificación no corresponde a este KPI.'
      }
    } catch (e) {
      avisoNotificacion.value = 'La alerta de la notificación ya no está disponible.'
    }
  }
}

function cerrarContextoNotificacion() {
  alertaNotificacion.value = null
  avisoNotificacion.value = ''
  limpiarFiltros()

  const { indicador, alerta, ...resto } = route.query
  router.replace({ path: '/mediciones', query: resto })
}

// Nombre del KPI filtrado desde la notificación (de los datos ya cargados).
const kpiNotificacionNombre = computed(() => {
  const id = leerParametrosNotificacion(route.query).indicador

  if (!id || Number(indicadorSeleccionado.value) !== id) return ''

  const kpi = indicadores.value.find((item) => Number(item.id) === id)
  const medicion = mediciones.value.find((item) => Number(item.indicador) === id)

  return kpi?.nombre || medicion?.indicador_nombre || ''
})

// Si se abre otra notificación estando ya en Mediciones. La carga inicial
// la hace onMounted, cuando ya están los datos.
watch(
  () => [route.query.indicador, route.query.alerta],
  async () => {
    if (!cargando.value) await aplicarParametrosNotificacion()
  },
)

watch(
  () => route.query.tab,
  (tab) => {
    tabActiva.value = tab === 'solicitudes' && verSolicitudes.value ? 'solicitudes' : 'mediciones'
  },
  { immediate: true },
)

// Bloque 4 (periodos y plazos): plazo de registro configurable, singleton.
const configuracionMediciones = ref(null)
const edicionPlazoRegistro = ref('')
const guardandoPlazoRegistro = ref(false)
const errorPlazoRegistro = ref('')

function puedeEditar(medicion) {
  return puedeEditarMedicion(props.usuario, medicion)
}

const tituloModal = computed(() => {
  return medicionSeleccionada.value?.id ? 'Editar medición' : 'Nueva medición'
})

const subtituloModal = computed(() => {
  if (medicionSeleccionada.value?.id) {
    return 'Actualizá el resultado medido. El sistema recalculará el cumplimiento y el estado automáticamente.'
  }

  return 'Registrá una medición para que el sistema calcule el cumplimiento y asigne el estado correspondiente.'
})

const medicionesFiltradas = computed(() => {
  const texto = busqueda.value.trim().toLowerCase()

  return mediciones.value.filter((medicion) => {
    const coincideBusqueda =
      !texto ||
      medicion.indicador_nombre?.toLowerCase().includes(texto) ||
      medicion.periodo_nombre?.toLowerCase().includes(texto) ||
      medicion.estado_cumplimiento_nombre?.toLowerCase().includes(texto) ||
      medicion.observacion?.toLowerCase().includes(texto) ||
      medicion.observaciones?.toLowerCase().includes(texto) ||
      (medicion.evidencias || []).some((evidencia) => evidencia.nombre_original?.toLowerCase().includes(texto))

    const coincideIndicador =
      !indicadorSeleccionado.value ||
      Number(medicion.indicador) === Number(indicadorSeleccionado.value)

    const coincideEstado =
      !estadoSeleccionado.value ||
      Number(medicion.estado_cumplimiento) === Number(estadoSeleccionado.value)

    return coincideBusqueda && coincideIndicador && coincideEstado
  })
})

const hayFiltrosActivos = computed(() => {
  return busqueda.value.trim() !== '' || indicadorSeleccionado.value !== '' || estadoSeleccionado.value !== ''
})

function limpiarFiltros() {
  busqueda.value = ''
  indicadorSeleccionado.value = ''
  estadoSeleccionado.value = ''
}

const {
  paginaActual,
  porPagina,
  totalResultados,
  totalPaginas,
  elementosVisibles: medicionesPagina,
  rangoInicio,
  rangoFin,
  irAPagina,
} = usePaginacion(medicionesFiltradas)

function cambiarPorPagina(valor) {
  porPagina.value = valor
}

const totalMediciones = computed(() => mediciones.value.length)

// Bloque 5, punto 20: se elimina el promedio que mezclaba
// porcentaje_cumplimiento de mediciones de distintos KPI (unidades, metas
// y rangos distintos entre sí — un promedio así no significa nada). Se
// reemplaza por conteos neutrales; el promedio acumulado real, por KPI, se
// consulta en Indicadores KPI.
const medicionesManuales = computed(() => {
  return mediciones.value.filter((medicion) => !medicion.cierre_automatico).length
})

const medicionesAutomaticas = computed(() => {
  return mediciones.value.filter((medicion) => medicion.cierre_automatico).length
})

async function cargarDatos() {
  cargando.value = true
  error.value = ''

  try {
    const [medicionesResponse, datosFormulario, configuracion] = await Promise.all([
      obtenerMediciones(),
      obtenerDatosFormularioMedicion(),
      obtenerConfiguracionMediciones(),
    ])

    mediciones.value = medicionesResponse
    indicadores.value = datosFormulario.indicadores
    estadosCumplimiento.value = datosFormulario.estadosCumplimiento
    configuracionMediciones.value = configuracion
    edicionPlazoRegistro.value = configuracion.dias_plazo_registro
  } catch (e) {
    error.value = 'No se pudieron cargar las mediciones.'
  } finally {
    cargando.value = false
  }
}

async function guardarPlazoRegistro() {
  errorPlazoRegistro.value = ''
  guardandoPlazoRegistro.value = true

  try {
    configuracionMediciones.value = await actualizarConfiguracionMediciones(edicionPlazoRegistro.value)
    edicionPlazoRegistro.value = configuracionMediciones.value.dias_plazo_registro
  } catch (e) {
    const data = e.response?.data

    errorPlazoRegistro.value =
      data?.dias_plazo_registro?.join(' ') || data?.detail || 'No se pudo guardar el plazo.'
  } finally {
    guardandoPlazoRegistro.value = false
  }
}

function abrirModalCrear() {
  mensajeExito.value = ''
  medicionSeleccionada.value = null
  mostrarModal.value = true
}

function abrirModalEditar(medicion) {
  if (!puedeEditar(medicion)) {
    return
  }

  mensajeExito.value = ''
  medicionSeleccionada.value = { ...medicion }
  mostrarModal.value = true
}

function textoTipoRegistro(medicion) {
  return medicion.cierre_automatico ? 'Automático' : 'Manual'
}

function textoRegistradoPor(medicion) {
  if (medicion.cierre_automatico && !medicion.registrado_por_username) {
    return 'Sistema'
  }

  return medicion.registrado_por_username || 'Sistema'
}

function abrirModalDetalle(medicion) {
  medicionDetalle.value = { ...medicion }
  mostrarModalDetalle.value = true
}

// D2: las evidencias nuevas se suman a la medición abierta y a su fila del
// listado, sin recargar todo.
function sumarEvidencias(nuevas) {
  const actualizar = (medicion) => {
    const evidencias = [...(medicion.evidencias || []), ...nuevas]

    return {
      ...medicion,
      evidencias,
      cantidad_evidencias: evidencias.length,
      tiene_evidencia: evidencias.length > 0,
      evidencia_nombre: evidencias[evidencias.length - 1]?.nombre_original || null,
    }
  }

  if (medicionDetalle.value) {
    medicionDetalle.value = actualizar(medicionDetalle.value)
  }

  mediciones.value = mediciones.value.map((medicion) => (
    medicion.id === medicionDetalle.value?.id ? actualizar(medicion) : medicion
  ))
}

function cerrarModalDetalle() {
  mostrarModalDetalle.value = false
  medicionDetalle.value = null
}

function cerrarModal() {
  mostrarModal.value = false
  medicionSeleccionada.value = null
}

async function manejarGuardado() {
  const fueEdicion = !!medicionSeleccionada.value?.id

  cerrarModal()
  await cargarDatos()

  mensajeExito.value = fueEdicion
    ? 'Medición actualizada correctamente.'
    : 'Medición registrada correctamente.'
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

onMounted(async () => {
  await Promise.all([cargarDatos(), contarSolicitudesPendientes()])
  await aplicarParametrosNotificacion()
  await aplicarResaltadoDesdeRuta()
})
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Seguimiento de KPI"
    subtitulo="Registra y consulta los resultados por periodo de los KPI autorizados."
    breadcrumb-actual="Mediciones"
    @logout="cerrarSesion"
  >
    <template #actions>
      <button v-if="puedeRegistrar" class="btn-primary-page" type="button" @click="abrirModalCrear">
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

        Nueva medición
      </button>

      <button v-if="puedeSolicitar" class="btn-secondary-page" type="button" @click="abrirModalAmpliacion">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        </svg>
        Solicitar días adicionales
      </button>
    </template>

    <div v-if="verSolicitudes" class="tabs">
      <button
        class="tab-btn"
        type="button"
        :class="{ active: tabActiva === 'mediciones' }"
        @click="cambiarTab('mediciones')"
      >
        Mediciones
      </button>
      <button
        class="tab-btn"
        type="button"
        :class="{ active: tabActiva === 'solicitudes' }"
        @click="cambiarTab('solicitudes')"
      >
        {{ tituloTabSolicitudes }}
        <span v-if="solicitudesPendientes" class="tab-count" :title="`${solicitudesPendientes} pendiente(s)`">
          {{ solicitudesPendientes }}
        </span>
      </button>
    </div>

    <div v-if="mensajeExito && tabActiva === 'solicitudes'" class="alert success">
      {{ mensajeExito }}
    </div>

    <SolicitudesAmpliacion
      v-if="verSolicitudes && tabActiva === 'solicitudes'"
      :key="claveSolicitudes"
      :es-admin="esAdmin"
      :resaltar-id="solicitudResaltada"
      @actualizado="actualizarConteoSolicitudes"
    />

    <template v-if="tabActiva === 'mediciones'">
    <section class="summary-grid">
      <article class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon navy">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="4" y="3" width="16" height="18" rx="2" />
              <path d="M9 3v3h6V3" />
              <path d="M8 13h8" />
              <path d="M8 17h5" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ totalMediciones }}</div>
        <div class="kpi-label">Mediciones registradas</div>
        <div class="kpi-foot">Total almacenado en el sistema</div>
      </article>

      <article class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon aqua">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 19V5" />
              <path d="M4 19h16" />
              <path d="M7 15l4-4 3 3 5-7" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ medicionesManuales }}</div>
        <div class="kpi-label">Registradas manualmente</div>
        <div class="kpi-foot">Registradas por un usuario</div>
      </article>

      <article class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon steel">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M8 12l2.5 2.5L16 9" />
            </svg>
          </div>
        </div>

        <div class="kpi-value">{{ medicionesAutomaticas }}</div>
        <div class="kpi-label">Periodos sin registro</div>
        <div class="kpi-foot">Cerrados por el sistema sin resultado</div>
      </article>
    </section>

    <p class="hint-acumulado">
      El promedio acumulado y el estado de cumplimiento de cada KPI se consultan en
      <router-link to="/indicadores">Indicadores KPI</router-link>.
    </p>

    <div class="plazo-registro">
      <span>
        Plazo para registrar una medición después del cierre de su periodo:
        <strong>{{ configuracionMediciones?.dias_plazo_registro ?? '—' }} día(s) calendario.</strong>
      </span>

      <template v-if="esAdmin">
        <input
          v-model="edicionPlazoRegistro"
          type="number"
          min="1"
          step="1"
          class="plazo-registro-input"
        />
        <button
          type="button"
          class="btn-secondary btn-small"
          :disabled="guardandoPlazoRegistro"
          @click="guardarPlazoRegistro"
        >
          {{ guardandoPlazoRegistro ? 'Guardando...' : 'Guardar' }}
        </button>
      </template>
    </div>

    <p v-if="errorPlazoRegistro" class="alert error plazo-registro-error">
      {{ errorPlazoRegistro }}
    </p>

    <div v-if="mensajeExito" class="alert success">
      {{ mensajeExito }}
    </div>

    <!-- Etapa 6: contexto abierto desde una notificación. -->
    <div v-if="avisoNotificacion" class="alert aviso">
      {{ avisoNotificacion }}
    </div>

    <div v-if="kpiNotificacionNombre || alertaNotificacion" class="contexto-notificacion">
      <div>
        <div v-if="kpiNotificacionNombre" class="contexto-titulo">
          Mediciones del KPI <strong>{{ kpiNotificacionNombre }}</strong>, desde una notificación.
        </div>
        <div v-if="alertaNotificacion" class="contexto-alerta">
          <span class="contexto-tipo">{{ alertaNotificacion.tipo_alerta }}</span>
          <span class="contexto-estado">
            {{ alertaNotificacion.estado_alerta === 'pendiente' ? 'Pendiente' : alertaNotificacion.estado_alerta === 'revisada' ? 'Revisada' : 'Resuelta' }}
            · {{ formatearFecha(alertaNotificacion.fecha_generacion) }}
          </span>
          <p>{{ alertaNotificacion.mensaje }}</p>
        </div>
      </div>
      <button type="button" class="btn-secondary btn-small" @click="cerrarContextoNotificacion">
        Ver todas las mediciones
      </button>
    </div>

    <div class="toolbar">
      <div class="toolbar-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>

        <input v-model="busqueda" type="text" placeholder="Buscar medición..." />
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">KPI:</span>

        <select v-model="indicadorSeleccionado">
          <option value="">Todos</option>

          <option v-for="indicador in indicadores" :key="indicador.id" :value="indicador.id">
            {{ indicador.nombre }}
          </option>
        </select>
      </div>

      <div class="toolbar-filter">
        <span class="filter-label">Estado:</span>

        <select v-model="estadoSeleccionado">
          <option value="">Todos</option>

          <option v-for="estado in estadosCumplimiento" :key="estado.id" :value="estado.id">
            {{ estado.nombre }}
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
        {{ medicionesFiltradas.length }} mediciones
      </div>
    </div>

    <section class="card-panel table-card">
      <div v-if="cargando" class="message">
        Cargando mediciones...
      </div>

      <div v-else-if="error" class="message error">
        {{ error }}
      </div>

      <div v-else-if="!mediciones.length" class="empty-state">
        No hay mediciones para mostrar.
      </div>

      <div v-else-if="!medicionesFiltradas.length" class="empty-state">
        No se encontraron resultados con los filtros aplicados.
      </div>

      <div v-else class="table-scroll">
      <table>
        <colgroup>
          <col style="width: 14%">
          <col style="width: 10%">
          <col style="width: 7%">
          <col style="width: 8%">
          <col style="width: 9%">
          <col style="width: 10%">
          <col style="width: 9%">
          <col style="width: 10%">
          <col style="width: 9%">
          <col style="width: 6%">
          <col style="width: 8%">
        </colgroup>
        <thead>
          <tr>
            <th>KPI</th>
            <th>Periodo evaluado</th>
            <th>Meta</th>
            <th>Resultado</th>
            <th title="Diferencia matemática entre el resultado obtenido y la meta del KPI.">Diferencia respecto a la meta</th>
            <th title="Estado individual de esta medición, clasificado directamente contra los rangos configurados para este KPI.">Estado del periodo</th>
            <th title="Promedio directo de los resultados del KPI hasta este periodo (no es el resultado de este periodo).">Promedio acumulado</th>
            <th title="Estado del KPI según el promedio acumulado hasta este periodo (no es el estado de esta medición individual).">Estado acumulado</th>
            <th>Registrado por</th>
            <th>Tipo</th>
            <th class="th-acciones" style="text-align: right;">Acciones</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="medicion in medicionesPagina"
            :key="medicion.id"
            :id="`fila-${medicion.id}`"
            :class="{ 'highlight-row': idResaltado === Number(medicion.id) }"
          >
            <td>
              <div class="cell-main" :title="medicion.indicador_nombre || 'Sin KPI'">{{ medicion.indicador_nombre || 'Sin KPI' }}</div>
              <div class="cell-sub" :title="medicion.observacion || medicion.observaciones || 'Sin observaciones'">{{ medicion.observacion || medicion.observaciones || 'Sin observaciones' }}</div>
            </td>

            <td>
              <div class="cell-main">
                {{ medicion.periodo_nombre || 'Periodo no definido' }}
              </div>
              <div class="cell-sub">
                Cierre: {{ formatearFecha(medicion.fecha_medicion) }}
              </div>
            </td>

            <td>
              <div class="meta-value">
                {{ formatearNumero(medicion.valor_meta, { unidad: medicion.unidad_medida }) }}
              </div>
              <div class="cell-sub">
                Meta del KPI
              </div>
            </td>

            <td>
              <!-- Etapa 3 (C3): una omisión no tiene resultado. -->
              <div v-if="esMedicionSinRegistro(medicion)" class="meta-value sin-registro">
                {{ SIN_REGISTRO }}
              </div>
              <div v-else class="meta-value">
                {{ formatearNumero(medicion.valor_resultado, { unidad: medicion.unidad_medida }) }}
              </div>
              <div class="cell-sub">
                {{ esMedicionSinRegistro(medicion) ? 'No se registró resultado' : 'Resultado del periodo' }}
              </div>
            </td>

            <td>
              <div class="meta-value">
                {{
                  esMedicionSinRegistro(medicion)
                    ? '-'
                    : formatearDiferencia(medicion.valor_resultado, medicion.valor_meta, { unidad: medicion.unidad_medida })
                }}
              </div>
              <div class="cell-sub">
                Resultado vs. meta
              </div>
            </td>

            <td>
              <span
                class="badge"
                :class="claseColorCumplimiento(medicion.estado_cumplimiento_color)"
                :title="textoEstadoCumplimiento(medicion.estado_cumplimiento_nombre)"
              >
                <span class="badge-dot"></span>
                <span class="badge-text">{{ textoEstadoCumplimiento(medicion.estado_cumplimiento_nombre) }}</span>
              </span>
            </td>

            <td>
              <div class="meta-value">
                {{ formatearNumero(medicion.promedio_acumulado_hasta_medicion, { unidad: medicion.unidad_medida }) }}
              </div>
              <div class="cell-sub">
                Hasta este periodo
              </div>
            </td>

            <td>
              <span
                class="badge"
                :class="claseColorCumplimiento(medicion.estado_acumulado_hasta_medicion_color)"
                :title="textoEstadoCumplimiento(medicion.estado_acumulado_hasta_medicion_nombre)"
              >
                <span class="badge-dot"></span>
                <span class="badge-text">{{ textoEstadoCumplimiento(medicion.estado_acumulado_hasta_medicion_nombre) }}</span>
              </span>
            </td>

            <td>
              <div class="cell-main">
                {{ textoRegistradoPor(medicion) }}
              </div>
              <div class="cell-sub">
                {{ formatearFecha(medicion.fecha_registro) }}
              </div>
            </td>

            <td>
              <span class="source-chip" :class="medicion.cierre_automatico ? 'dw' : 'manual'">
                {{ textoTipoRegistro(medicion) }}
              </span>
            </td>

            <td class="td-acciones">
              <div class="actions-cell">
                <button class="action-icon-btn" type="button" title="Ver detalle" aria-label="Ver detalle" @click="abrirModalDetalle(medicion)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>

                <button v-if="puedeEditar(medicion)" class="action-icon-btn" type="button" title="Editar" aria-label="Editar" @click="abrirModalEditar(medicion)">
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
        v-if="medicionesFiltradas.length"
        :pagina-actual="paginaActual"
        :total-paginas="totalPaginas"
        :por-pagina="porPagina"
        :rango-inicio="rangoInicio"
        :rango-fin="rangoFin"
        :total-resultados="totalResultados"
        etiqueta="mediciones"
        @cambiar-pagina="irAPagina"
        @cambiar-por-pagina="cambiarPorPagina"
      />
    </section>
    </template>

    <ModalBase
      :abierto="mostrarModalAmpliacion"
      titulo="Solicitar días adicionales"
      subtitulo="Pedí hasta 10 días calendario más para registrar la medición del periodo pendiente de un KPI. La solicitud la resuelve el Administrador de planificación."
      @cerrar="mostrarModalAmpliacion = false"
    >
      <SolicitudAmpliacionForm
        v-if="mostrarModalAmpliacion"
        :indicadores="indicadores"
        @guardado="manejarSolicitudEnviada"
        @cancelar="mostrarModalAmpliacion = false"
      />
    </ModalBase>

    <ModalBase
      :abierto="mostrarModal"
      :titulo="tituloModal"
      :subtitulo="subtituloModal"
      @cerrar="cerrarModal"
    >
      <MedicionForm
        :indicadores="indicadores"
        :medicion-editar="medicionSeleccionada"
        @guardado="manejarGuardado"
        @cancelar="cerrarModal"
      />
    </ModalBase>

    <ModalBase
      :abierto="mostrarModalDetalle"
      titulo="Detalle de medición"
      subtitulo="Información completa de la medición registrada y su cálculo de cumplimiento."
      ancho="760px"
      @cerrar="cerrarModalDetalle"
    >
      <MedicionDetalle
        v-if="medicionDetalle"
        :medicion="medicionDetalle"
        :puede-agregar-evidencia="puedeRegistrar"
        @evidencias-agregadas="sumarEvidencias"
      />
    </ModalBase>
  </AppLayout>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.hint-acumulado {
  margin: -10px 0 18px;
  font-size: 12.5px;
  color: #9aa8b8;
  font-weight: 600;
}

.hint-acumulado a {
  color: #457b9d;
  font-weight: 800;
  text-decoration: none;
}

.hint-acumulado a:hover {
  text-decoration: underline;
}

.plazo-registro {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin: -6px 0 18px;
  padding: 10px 14px;
  border-radius: 12px;
  background: #f6f9fa;
  border: 1px solid #e4eaef;
  font-size: 12.5px;
  color: #1d3557;
}

.plazo-registro-input {
  width: 70px;
  height: 32px;
  border: 1.5px solid #e4eaef;
  border-radius: 8px;
  padding: 0 8px;
  font-family: inherit;
  font-size: 13px;
  color: #1d3557;
}

.plazo-registro-error {
  margin-top: -10px;
}

.btn-secondary {
  height: 34px;
  padding: 0 14px;
  border-radius: 9px;
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 800;
  cursor: pointer;
}

.btn-secondary:hover:not(:disabled) {
  background: #f4f7f9;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-small {
  height: 30px;
  padding: 0 10px;
  font-size: 12px;
}

.alert.error {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
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

.kpi-icon.navy { background: rgba(29, 53, 87, 0.08); color: #1d3557; }
.kpi-icon.steel { background: rgba(69, 123, 157, 0.10); color: #457b9d; }
.kpi-icon.aqua { background: #eaf5f5; color: #457b9d; }
.kpi-icon.orange { background: rgba(244, 162, 97, 0.14); color: #f4a261; }
.kpi-icon svg { stroke: currentColor; }

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

.btn-primary-page:hover { background: #152840; }

/* Etapa 6: contexto abierto desde una notificación. */
.alert.aviso {
  background: rgba(244, 162, 97, 0.14);
  color: #b9701e;
}

.contexto-notificacion {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 18px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #eaf5f5;
  border: 1px solid #a8dadc;
  color: #1d3557;
  font-size: 13px;
}

.contexto-titulo { font-weight: 600; }
.contexto-alerta { margin-top: 6px; }
.contexto-alerta p { margin: 4px 0 0; color: #5e6e82; font-size: 12.5px; }
.contexto-tipo { font-weight: 800; margin-right: 8px; }
.contexto-estado { font-size: 11.5px; color: #7f8fa3; font-weight: 700; }

/* Etapa 5: días adicionales. */
.btn-secondary-page {
  height: 40px;
  padding: 0 15px;
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary-page:hover { background: #f4f7f9; }

.tabs {
  display: flex;
  gap: 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid #e4eaef;
}

.tab-btn {
  height: 40px;
  padding: 0 4px;
  margin-bottom: -1px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: #9aa8b8;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.tab-btn:hover { color: #457b9d; }
.tab-btn.active { color: #1d3557; border-bottom-color: #1d3557; }

.tab-count {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: #f4a261;
  color: #ffffff;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.alert {
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 18px;
}

.alert.success {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
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

.toolbar-search svg { stroke: #9aa8b8; }
.toolbar-search input {
  border: none;
  outline: none;
  width: 100%;
  background: transparent;
  font-family: inherit;
  color: #1d3557;
  font-size: 13px;
}
.toolbar-search input::placeholder { color: #9aa8b8; }

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

.filter-label { color: #9aa8b8; font-size: 12px; }

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

.card-panel { padding: 20px 22px 18px; }
.table-card { margin-bottom: 20px; }

.message,
.empty-state {
  padding: 16px;
  border-radius: 12px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 13px;
  font-weight: 700;
}

.message.error { background: rgba(231, 111, 81, 0.12); color: #e76f51; }

.table-scroll { overflow-x: auto; }
table { width: 100%; min-width: 1080px; border-collapse: collapse; table-layout: fixed; }

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

tbody tr:last-child td { border-bottom: none; }
tbody tr { transition: background 0.12s ease; }
tbody tr:hover { background: #fafcfd; }

.cell-main { font-weight: 800; font-size: 13px; color: #1d3557; max-width: 260px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cell-sub { font-size: 11.5px; color: #9aa8b8; font-weight: 500; margin-top: 3px; max-width: 460px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

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
.badge.ok { background: rgba(42, 157, 143, 0.12); color: #2a9d8f; }
.badge.warning { background: rgba(244, 162, 97, 0.16); color: #b9701e; }
.badge.danger { background: rgba(231, 111, 81, 0.12); color: #e76f51; }
.badge.neutral { background: rgba(154, 168, 184, 0.16); color: #5e6e82; }
.badge-dot { flex-shrink: 0; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

.source-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 9px;
  font-size: 11.5px;
  font-weight: 800;
}
.source-chip.manual { background: rgba(69, 123, 157, 0.12); color: #457b9d; }
.source-chip.csv { background: rgba(244, 162, 97, 0.16); color: #b9701e; }

/* Etapa 3 (C3): resultado ausente de una omisión. */
.meta-value.sin-registro { color: #55657a; font-style: italic; }
.source-chip.dw { background: rgba(42, 157, 143, 0.12); color: #2a9d8f; }

.actions-cell { display: flex; align-items: center; justify-content: flex-end; gap: 6px; }
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
.action-icon-btn svg { stroke: currentColor; }
.action-icon-btn:hover { background: #eaf5f5; color: #457b9d; border-color: #a8dadc; }


@media (max-width: 1100px) {
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .summary-grid { grid-template-columns: 1fr; }
  .toolbar { align-items: stretch; }
  .toolbar-search,
  .toolbar-filter,
  .toolbar-count { width: 100%; max-width: none; min-width: 0; }
  .toolbar-filter select { flex: 1; min-width: 0; max-width: 100%; }
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
