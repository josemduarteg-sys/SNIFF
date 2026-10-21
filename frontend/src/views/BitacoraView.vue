<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import { obtenerBitacora } from '../services/bitacoraService'
import { puedeVerBitacora } from '../utils/permisos'
import { usePaginacion } from '../composables/usePaginacion'
import Paginacion from '../components/common/Paginacion.vue'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const puedeVer = computed(() => puedeVerBitacora(props.usuario))

const registros = ref([])
const cargando = ref(false)
const error = ref('')

const busqueda = ref('')
const filtroModulo = ref('')
const filtroAccion = ref('')
const filtroUsuario = ref('')
// Etapa 4 (M7): acciones de usuarios frente a eventos automáticos del sistema.
const filtroOrigen = ref('')
const fechaInicio = ref('')
const fechaFin = ref('')

function autorRegistro(item) {
  if (item.origen === 'sistema') return 'Sistema'

  return item.usuario_username || item.autor || 'Sin usuario'
}

function normalizarLista(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

async function cargarBitacora() {
  if (!puedeVer.value) {
    return
  }

  cargando.value = true
  error.value = ''

  try {
    const data = await obtenerBitacora()
    registros.value = normalizarLista(data)
  } catch (e) {
    error.value = 'No se pudo cargar la bitácora.'
    registros.value = []
  } finally {
    cargando.value = false
  }
}

const modulosDisponibles = computed(() => {
  const modulos = new Set(registros.value.map((item) => item.modulo).filter(Boolean))
  return Array.from(modulos).sort()
})

const accionesDisponibles = computed(() => {
  const acciones = new Set(registros.value.map((item) => item.accion).filter(Boolean))
  return Array.from(acciones).sort()
})

function soloFecha(fechaHora) {
  if (!fechaHora) {
    return null
  }

  return fechaHora.split('T')[0]
}

const registrosFiltrados = computed(() => {
  const termino = busqueda.value.trim().toLowerCase()
  const usuarioTermino = filtroUsuario.value.trim().toLowerCase()

  return registros.value.filter((item) => {
    const username = autorRegistro(item).toLowerCase()
    const modulo = String(item.modulo || '').toLowerCase()
    const accionTexto = textoAccion(item.accion, item).toLowerCase()
    const descripcion = String(item.descripcion || '').toLowerCase()

    const coincideBusqueda =
      !termino ||
      username.includes(termino) ||
      modulo.includes(termino) ||
      accionTexto.includes(termino) ||
      item.accion?.toLowerCase().includes(termino) ||
      descripcion.includes(termino)

    const coincideModulo = !filtroModulo.value || item.modulo === filtroModulo.value
    const coincideAccion = !filtroAccion.value || item.accion === filtroAccion.value
    const coincideUsuario = !usuarioTermino || username.includes(usuarioTermino)
    const coincideOrigen = !filtroOrigen.value || (item.origen || 'usuario') === filtroOrigen.value

    const fechaRegistro = soloFecha(item.fecha_hora)
    const coincideFechaInicio = !fechaInicio.value || (fechaRegistro && fechaRegistro >= fechaInicio.value)
    const coincideFechaFin = !fechaFin.value || (fechaRegistro && fechaRegistro <= fechaFin.value)

    return (
      coincideBusqueda &&
      coincideModulo &&
      coincideAccion &&
      coincideUsuario &&
      coincideOrigen &&
      coincideFechaInicio &&
      coincideFechaFin
    )
  })
})

const hayFiltrosActivos = computed(() => {
  return (
    busqueda.value.trim() !== '' ||
    filtroModulo.value !== '' ||
    filtroAccion.value !== '' ||
    filtroUsuario.value.trim() !== '' ||
    filtroOrigen.value !== '' ||
    fechaInicio.value !== '' ||
    fechaFin.value !== ''
  )
})

function limpiarFiltros() {
  busqueda.value = ''
  filtroModulo.value = ''
  filtroAccion.value = ''
  filtroUsuario.value = ''
  filtroOrigen.value = ''
  fechaInicio.value = ''
  fechaFin.value = ''
}

const {
  paginaActual,
  porPagina,
  totalResultados,
  totalPaginas,
  elementosVisibles: registrosPagina,
  rangoInicio,
  rangoFin,
  irAPagina,
} = usePaginacion(registrosFiltrados)

function cambiarPorPagina(valor) {
  porPagina.value = valor
}

const totalRegistros = computed(() => registros.value.length)

const registrosHoy = computed(() => {
  const hoy = new Date().toISOString().split('T')[0]
  return registros.value.filter((item) => soloFecha(item.fecha_hora) === hoy).length
})

// Solo personas: los eventos del "Sistema" no cuentan como usuario.
const totalUsuariosUnicos = computed(() => {
  return new Set(
    registros.value
      .filter((item) => item.origen !== 'sistema')
      .map((item) => item.usuario_username)
      .filter(Boolean)
  ).size
})

const totalModulosUnicos = computed(() => modulosDisponibles.value.length)

function textoAccion(accion, registro = null) {
  const descripcion = String(registro?.descripcion || '').toLowerCase()

  if (accion === 'eliminar') {
    if (descripcion.includes('inactivó')) return 'Inactivar'
    if (descripcion.includes('anuló')) return 'Anular'
    return 'Eliminar'
  }

  const mapa = {
    crear: 'Crear',
    actualizar: 'Actualizar',
    consultar: 'Consultar',
    importar_csv: 'Importar CSV',
    consulta_dw: 'Consulta al almacén de datos',
    inicio_sesion: 'Inicio de sesión',
    cierre_sesion: 'Cierre de sesión',
    error: 'Error',
  }

  return mapa[accion] || accion || 'Sin acción'
}

function textoAccionFiltro(accion) {
  if (accion === 'eliminar') {
    return 'Eliminar / Inactivar / Anular'
  }

  return textoAccion(accion)
}

function claseAccion(accion) {
  const mapa = {
    crear: 'success',
    actualizar: 'info',
    eliminar: 'danger',
    error: 'danger',
    inicio_sesion: 'neutral',
    cierre_sesion: 'neutral',
    consultar: 'neutral',
    importar_csv: 'neutral',
    consulta_dw: 'neutral',
  }

  return mapa[accion] || 'neutral'
}

function formatearFechaHora(fechaHora) {
  if (!fechaHora) {
    return 'Sin fecha'
  }

  const fecha = new Date(fechaHora)

  if (Number.isNaN(fecha.getTime())) {
    return fechaHora
  }

  return fecha.toLocaleString('es-GT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function cerrarSesion() {
  emit('logout')
}

onMounted(() => {
  cargarBitacora()
})
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Bitácora"
    subtitulo="Consulta las acciones registradas dentro del sistema."
    breadcrumb-actual="Bitácora"
    @logout="cerrarSesion"
  >
    <div v-if="!puedeVer" class="card-panel restricted-panel">
      <h2>No tenés permisos para consultar la bitácora.</h2>
      <p>Esta sección está disponible únicamente para administración del sistema.</p>
    </div>

    <template v-else>
      <div v-if="error" class="alert error">
        {{ error }}
      </div>

      <section class="summary-grid">
        <article class="summary-card">
          <span>Total de registros</span>
          <strong>{{ totalRegistros }}</strong>
          <p>Acciones registradas en el sistema</p>
        </article>

        <article class="summary-card">
          <span>Hoy</span>
          <strong>{{ registrosHoy }}</strong>
          <p>Acciones registradas en el día de hoy</p>
        </article>

        <article class="summary-card">
          <span>Usuarios</span>
          <strong>{{ totalUsuariosUnicos }}</strong>
          <p>Personas distintas con actividad (sin contar al Sistema)</p>
        </article>

        <article class="summary-card">
          <span>Módulos</span>
          <strong>{{ totalModulosUnicos }}</strong>
          <p>Módulos distintos con actividad</p>
        </article>
      </section>

      <section class="card-panel">
        <div class="panel-head">
          <div>
            <h2>Registros de bitácora</h2>
            <p>Historial de solo lectura de acciones administrativas y de seguridad.</p>
          </div>

          <button
            class="action-btn"
            type="button"
            :disabled="cargando"
            @click="cargarBitacora"
          >
            Actualizar
          </button>
        </div>

        <div class="filtros-grid">
          <div class="search-box field-full">
            <input
              v-model="busqueda"
              type="text"
              placeholder="Buscar por usuario, módulo, acción o descripción..."
            />
          </div>

          <label class="field">
            <span>Módulo</span>

            <select v-model="filtroModulo">
              <option value="">Todos los módulos</option>

              <option
                v-for="modulo in modulosDisponibles"
                :key="modulo"
                :value="modulo"
              >
                {{ modulo }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>Acción</span>

            <select v-model="filtroAccion">
              <option value="">Todas las acciones</option>

              <option
                v-for="accion in accionesDisponibles"
                :key="accion"
                :value="accion"
              >
                {{ textoAccionFiltro(accion) }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>Usuario</span>

            <input
              v-model="filtroUsuario"
              type="text"
              placeholder="usuario..."
            />
          </label>

          <label class="field">
            <span>Origen</span>

            <select v-model="filtroOrigen">
              <option value="">Usuarios y sistema</option>
              <option value="usuario">Usuarios</option>
              <option value="sistema">Sistema</option>
            </select>
          </label>

          <label class="field">
            <span>Desde</span>

            <input v-model="fechaInicio" type="date" />
          </label>

          <label class="field">
            <span>Hasta</span>

            <input v-model="fechaFin" type="date" />
          </label>

          <button
            v-if="hayFiltrosActivos"
            class="btn-limpiar-filtros field-full"
            type="button"
            @click="limpiarFiltros"
          >
            Limpiar filtros
          </button>
        </div>

        <div v-if="cargando" class="message">
          Cargando bitácora...
        </div>

        <div v-else-if="!registros.length" class="empty-state">
          No hay registros de bitácora para mostrar.
        </div>

        <div v-else-if="!registrosFiltrados.length" class="empty-state">
          No se encontraron resultados con los filtros aplicados.
        </div>

        <div v-else class="table-scroll">
        <table>
          <colgroup>
            <col style="width: 14%">
            <col style="width: 14%">
            <col style="width: 12%">
            <col style="width: 14%">
            <col style="width: 34%">
            <col style="width: 12%">
          </colgroup>
          <thead>
            <tr>
              <th>Fecha y hora</th>
              <th>Usuario ejecutor</th>
              <th>Acción</th>
              <th>Módulo</th>
              <th>Descripción</th>
              <th>IP</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="item in registrosPagina"
              :key="item.id"
            >
              <td>{{ formatearFechaHora(item.fecha_hora) }}</td>

              <td>
                <div class="cell-main" :title="autorRegistro(item)">
                  {{ autorRegistro(item) }}
                  <span v-if="item.origen === 'sistema'" class="chip-sistema">Automático</span>
                </div>
              </td>

              <td>
                <span class="action-chip" :class="claseAccion(item.accion)">
                  {{ textoAccion(item.accion, item) }}
                </span>
              </td>

              <td>
                <span class="role-chip" :title="item.modulo || 'Sin módulo'">{{ item.modulo || 'Sin módulo' }}</span>
              </td>

              <td>
                <div class="cell-sub descripcion-cell" :title="item.descripcion || 'Sin descripción'">{{ item.descripcion || 'Sin descripción' }}</div>
              </td>

              <td>{{ item.ip_usuario || 'No registrada' }}</td>
            </tr>
          </tbody>
        </table>
        </div>

        <Paginacion
          v-if="registrosFiltrados.length"
          :pagina-actual="paginaActual"
          :total-paginas="totalPaginas"
          :por-pagina="porPagina"
          :rango-inicio="rangoInicio"
          :rango-fin="rangoFin"
          :total-resultados="totalResultados"
          etiqueta="registros"
          @cambiar-pagina="irAPagina"
          @cambiar-por-pagina="cambiarPorPagina"
        />
      </section>
    </template>
  </AppLayout>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
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
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
  gap: 12px;
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

.alert {
  padding: 13px 15px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 750;
  margin-bottom: 18px;
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

.action-btn {
  height: 36px;
  padding: 0 12px;
  border-radius: 9px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  color: #457b9d;
  font-family: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.action-btn:hover {
  background: #eaf5f5;
  border-color: #a8dadc;
}

.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.filtros-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.field-full {
  grid-column: 1 / -1;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.field span {
  font-size: 11.5px;
  font-weight: 800;
  color: #1d3557;
}

.field input,
.field select {
  width: 100%;
  height: 38px;
  padding: 0 12px;
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.field input:focus,
.field select:focus {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
}

.search-box input {
  width: 100%;
  height: 38px;
  padding: 0 12px;
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.search-box input::placeholder {
  color: #9aa8b8;
}

.search-box input:focus {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
}

.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 900px;
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

td {
  padding: 13px 10px;
  border-bottom: 1px solid #eef2f5;
  color: #1d3557;
  font-size: 13px;
  font-weight: 600;
  vertical-align: top;
  overflow: hidden;
}

/* Etapa 4 (M7): eventos ejecutados por el sistema. */
.chip-sistema {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 7px;
  border-radius: 999px;
  background: rgba(69, 123, 157, 0.12);
  color: #457b9d;
  font-size: 10.5px;
  font-weight: 800;
  vertical-align: middle;
}

.cell-main {
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-sub {
  color: #9aa8b8;
  font-size: 12px;
  font-weight: 500;
}

.descripcion-cell {
  max-width: 420px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.role-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 850;
  background: #eaf5f5;
  color: #457b9d;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.action-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 850;
}

.action-chip.success {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.action-chip.info {
  background: rgba(69, 123, 157, 0.12);
  color: #457b9d;
}

.action-chip.danger {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

.action-chip.neutral {
  background: rgba(154, 168, 184, 0.16);
  color: #5e6e82;
}

.btn-limpiar-filtros {
  height: 38px;
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
  justify-self: start;
}

.btn-limpiar-filtros:hover {
  background: rgba(231, 111, 81, 0.10);
  border-color: rgba(231, 111, 81, 0.25);
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filtros-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
