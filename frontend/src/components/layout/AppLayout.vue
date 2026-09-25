<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarMenu from './SidebarMenu.vue'
import ProfileDropdown from './ProfileDropdown.vue'
import {
  marcarAlertaRevisada,
  marcarTodasAlertasRevisadas,
  obtenerAlertasPendientes,
} from '../../services/alertaService'
import {
  obtenerNotificacionesNoLeidas,
  marcarNotificacionLeida,
  marcarTodasNotificacionesLeidas,
} from '../../services/notificacionService'
import { puedeGestionarPlaneacion } from '../../utils/permisos'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
  titulo: {
    type: String,
    required: true,
  },
  subtitulo: {
    type: String,
    required: false,
    default: '',
  },
  breadcrumbActual: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['logout'])

const router = useRouter()

const sidebarContraido = ref(false)

const alertasPendientes = ref([])
const notificacionesNoLeidas = ref([])
const cargandoAlertas = ref(false)
const errorAlertas = ref('')
const menuAlertasAbierto = ref(false)

let intervaloAlertas = null

const puedeVerAlertasKpi = computed(() => puedeGestionarPlaneacion(props.usuario))

const alertasParaHeader = computed(() => {
  if (!puedeVerAlertasKpi.value) {
    return []
  }

  return alertasPendientes.value
})

const totalNotificacionesHeader = computed(() => {
  return notificacionesNoLeidas.value.length + alertasParaHeader.value.length
})

const elementosMenuNotificaciones = computed(() => {
  const notificaciones = notificacionesNoLeidas.value.map((notificacion) => ({
    id: `notificacion-${notificacion.id}`,
    tipoElemento: 'notificacion',
    idOriginal: notificacion.id,
    titulo: notificacion.titulo || 'Notificación',
    mensaje: notificacion.mensaje,
    fecha: notificacion.fecha_creacion,
    tipo: notificacion.tipo,
    enlace: notificacion.enlace,
  }))

  const alertas = alertasParaHeader.value.map((alerta) => ({
    id: `alerta-${alerta.id}`,
    tipoElemento: 'alerta',
    idOriginal: alerta.id,
    titulo: alerta.tipo_alerta || 'Alerta KPI',
    mensaje: alerta.mensaje,
    fecha: alerta.fecha_generacion,
    tipo: alerta.tipo_alerta,
    enlace: alerta.indicador
      ? `/indicadores?resaltar=${alerta.indicador}`
      : '/dashboard',
  }))

  return [...notificaciones, ...alertas]
    .sort((a, b) => new Date(b.fecha || 0) - new Date(a.fecha || 0))
    .slice(0, 6)
})

function alternarSidebar() {
  sidebarContraido.value = !sidebarContraido.value
}

async function cargarCentroNotificaciones() {
  cargandoAlertas.value = true
  errorAlertas.value = ''

  try {
    const [notificacionesData, alertasData] = await Promise.all([
      obtenerNotificacionesNoLeidas(),
      puedeVerAlertasKpi.value ? obtenerAlertasPendientes() : Promise.resolve([]),
    ])

    notificacionesNoLeidas.value = notificacionesData
    alertasPendientes.value = alertasData
  } catch (e) {
    console.error('No se pudo cargar el centro de notificaciones:', e)
    errorAlertas.value = 'No se pudieron cargar las notificaciones.'
    notificacionesNoLeidas.value = []
    alertasPendientes.value = []
  } finally {
    cargandoAlertas.value = false
  }
}

function alternarMenuAlertas() {
  menuAlertasAbierto.value = !menuAlertasAbierto.value

  if (menuAlertasAbierto.value) {
    cargarCentroNotificaciones()
  }
}

function cerrarMenuAlertas() {
  menuAlertasAbierto.value = false
}

function formatearFechaAlerta(fecha) {
  if (!fecha) return 'Sin fecha'

  const date = new Date(fecha)

  if (Number.isNaN(date.getTime())) {
    return fecha
  }

  return date.toLocaleString('es-GT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function claseAlerta(item) {
  if (item.tipoElemento === 'notificacion') {
    return 'info'
  }

  const texto = `${item.tipo || ''} ${item.mensaje || ''}`.toLowerCase()

  if (texto.includes('crítico') || texto.includes('critico') || texto.includes('incumplido')) {
    return 'danger'
  }

  if (texto.includes('riesgo') || texto.includes('vencido')) {
    return 'warning'
  }

  return 'info'
}

async function marcarLeida(item) {
  if (item.tipoElemento !== 'notificacion') return

  try {
    await marcarNotificacionLeida(item.idOriginal)
    await cargarCentroNotificaciones()
  } catch (e) {
    console.error('No se pudo marcar la notificación como leída:', e)
  }
}

// Bloque 5.1: acción individual de una Alerta KPI dentro del centro de
// notificaciones. Retira la alerta de la lista (recargando desde el
// backend, que ya deja de traerla al dejar de estar 'pendiente') y
// actualiza el contador de la campanita, sin necesidad de F5.
async function marcarAlertaComoRevisada(item) {
  if (item.tipoElemento !== 'alerta') return

  try {
    await marcarAlertaRevisada(item.idOriginal)
    await cargarCentroNotificaciones()
  } catch (e) {
    console.error('No se pudo marcar la alerta como revisada:', e)
  }
}

async function abrirElementoNotificacion(item) {
  const enlace = item.enlace || '/dashboard'

  try {
    if (item.tipoElemento === 'notificacion') {
      await marcarNotificacionLeida(item.idOriginal)
      await cargarCentroNotificaciones()
    }

    cerrarMenuAlertas()
    await router.push(enlace)
  } catch (e) {
    console.error('No se pudo abrir la notificación:', e)
    cerrarMenuAlertas()
    await router.push(enlace)
  }
}

// Bloque 5.1: "Marcar todas" ahora procesa TODO lo pendiente del centro,
// no solo Notificacion — Notificacion pasa a leída y Alerta KPI pendiente
// pasa a revisada. Cada tarea solo se dispara si hay algo de ese tipo, así
// que funciona igual si solo hay alertas, solo notificaciones, o ninguna.
async function marcarTodasLeidas() {
  const tareas = []

  if (notificacionesNoLeidas.value.length > 0) {
    tareas.push(marcarTodasNotificacionesLeidas())
  }

  if (puedeVerAlertasKpi.value && alertasParaHeader.value.length > 0) {
    tareas.push(marcarTodasAlertasRevisadas())
  }

  if (!tareas.length) return

  try {
    await Promise.all(tareas)
    await cargarCentroNotificaciones()
  } catch (e) {
    console.error('No se pudieron marcar todos los elementos pendientes:', e)
  }
}

function cerrarSesion() {
  emit('logout')
}

onMounted(() => {
  cargarCentroNotificaciones()
  intervaloAlertas = window.setInterval(() => {
    if (!menuAlertasAbierto.value) {
      cargarCentroNotificaciones()
    }
  }, 60000)
})

onBeforeUnmount(() => {
  if (intervaloAlertas) {
    window.clearInterval(intervaloAlertas)
  }
})
</script>

<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarContraido }">
    <SidebarMenu
      :usuario="props.usuario"
      :contraido="sidebarContraido"
      @alternar="alternarSidebar"
    />

    <div class="main-area">
      <header class="topbar">
        <div class="breadcrumb">
          <span>Sniff</span>

          <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
            <polyline points="9 18 15 12 9 6" />
          </svg>

          <span class="current">{{ breadcrumbActual }}</span>
        </div>

        <div class="topbar-search topbar-search--deshabilitado" title="Búsqueda global no disponible por el momento">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>

          <input type="text" placeholder="Búsqueda global no disponible por el momento" disabled />
        </div>

        <div class="topbar-actions">
          <div class="notification-wrapper">
            <button
              class="icon-btn notification-button"
              type="button"
              title="Alertas"
              @click="alternarMenuAlertas"
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>

              <span
                v-if="totalNotificacionesHeader > 0"
                class="notification-badge"
              >
                {{ totalNotificacionesHeader > 9 ? '9+' : totalNotificacionesHeader }}
              </span>
            </button>

            <div
              v-if="menuAlertasAbierto"
              class="notifications-dropdown"
            >
              <div class="notifications-header">
                <div>
                  <strong>Centro de notificaciones</strong>
                  <span>
                    {{ notificacionesNoLeidas.length }} notificaciones ·
                    {{ alertasParaHeader.length }} alertas KPI
                  </span>

                  <button
                    v-if="notificacionesNoLeidas.length > 0 || alertasParaHeader.length > 0"
                    class="notifications-mark-all"
                    type="button"
                    @click="marcarTodasLeidas"
                  >
                    Marcar todas
                  </button>
                </div>

                <button
                  class="notifications-close"
                  type="button"
                  @click="cerrarMenuAlertas"
                >
                  ×
                </button>
              </div>

              <div v-if="cargandoAlertas" class="notifications-empty">
                Cargando notificaciones...
              </div>

              <div v-else-if="errorAlertas" class="notifications-empty error">
                {{ errorAlertas }}
              </div>

              <div v-else-if="!elementosMenuNotificaciones.length" class="notifications-empty">
                No hay notificaciones pendientes.
              </div>

              <div v-else class="notifications-list">
                <article
                  v-for="item in elementosMenuNotificaciones"
                  :key="item.id"
                  class="notification-item notification-clickable"
                  :class="claseAlerta(item)"
                  @click="abrirElementoNotificacion(item)"
                >
                  <div class="notification-icon">
                    !
                  </div>

                  <div class="notification-content">
                    <span class="notification-type-label">
                      {{ item.tipoElemento === 'notificacion' ? 'Notificación' : 'Alerta KPI' }}
                    </span>

                    <strong>{{ item.titulo }}</strong>
                    <p>{{ item.mensaje }}</p>
                    <span>{{ formatearFechaAlerta(item.fecha) }}</span>

                    <div v-if="item.tipoElemento === 'notificacion'" class="notification-actions">
                      <button
                        class="notification-mark-read"
                        type="button"
                        @click.stop="marcarLeida(item)"
                      >
                        Marcar leída
                      </button>
                    </div>

                    <div v-else-if="item.tipoElemento === 'alerta'" class="notification-actions">
                      <button
                        class="notification-mark-read"
                        type="button"
                        title="Marcar esta alerta como revisada"
                        @click.stop="marcarAlertaComoRevisada(item)"
                      >
                        Marcar revisada
                      </button>
                    </div>
                  </div>
                </article>
              </div>

              <RouterLink
                class="notifications-link"
                to="/dashboard"
                @click="cerrarMenuAlertas"
              >
                Ver dashboard
              </RouterLink>
            </div>
          </div>

          <ProfileDropdown
            :usuario="props.usuario"
            @logout="cerrarSesion"
          />
        </div>
      </header>

      <main class="content">
        <div class="page-header">
          <div>
            <h1>{{ titulo }}</h1>
            <div v-if="subtitulo" class="subtitle">
              {{ subtitulo }}
            </div>
          </div>

          <slot name="actions"></slot>
        </div>

        <slot></slot>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  --sidebar-w: 250px;
  --navy: #1D3557;
  --navy-dark: #152840;
  --steel: #457B9D;
  --aqua: #A8DADC;
  --aqua-soft: #EAF5F5;
  --orange: #F4A261;
  --success: #2A9D8F;
  --danger: #E76F51;
  --bg: #F6F9FA;
  --white: #FFFFFF;
  --text-secondary: #5E6E82;
  --text-muted: #9AA8B8;
  --border: #E4EAEF;
  --radius-md: 14px;
  --shadow-card: 0 8px 22px rgba(29, 53, 87, 0.07);

  min-height: 100vh;
  display: flex;
  background: var(--bg);
  color: var(--navy);
  font-family: 'Montserrat', Arial, sans-serif;
}

* {
  box-sizing: border-box;
}

.main-area {
  flex: 1;
  min-width: 0;
}

.topbar {
  height: 72px;
  background: var(--white);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  gap: 18px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 600;
}

.breadcrumb svg {
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2.5;
}

.breadcrumb .current {
  color: var(--navy);
  font-weight: 800;
}

.topbar-search {
  max-width: 380px;
  width: 100%;
  height: 38px;
  border: 1.5px solid var(--border);
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 12px;
  background: #fbfcfd;
}

.topbar-search svg {
  stroke: var(--text-muted);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.topbar-search input {
  border: none;
  outline: none;
  background: transparent;
  width: 100%;
  font-family: inherit;
  font-size: 13px;
  color: var(--navy);
}

.topbar-search input::placeholder {
  color: var(--text-muted);
}

.topbar-search--deshabilitado {
  opacity: 0.55;
  cursor: not-allowed;
}

.topbar-search--deshabilitado input {
  cursor: not-allowed;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}

.icon-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 1.5px solid var(--border);
  background: var(--white);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  position: relative;
}

.icon-btn svg {
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.notification-wrapper {
  position: relative;
}

.notification-button {
  position: relative;
  cursor: pointer;
}

.notification-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #e76f51;
  color: #ffffff;
  font-size: 10px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #ffffff;
}

.notifications-dropdown {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 360px;
  max-width: calc(100vw - 32px);
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e4eaef;
  box-shadow: 0 18px 45px rgba(29, 53, 87, 0.16);
  z-index: 80;
  overflow: hidden;
}

.notifications-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 15px 16px;
  border-bottom: 1px solid #eef2f5;
}

.notifications-header strong {
  display: block;
  color: #1d3557;
  font-size: 14px;
  font-weight: 900;
}

.notifications-header span {
  display: block;
  margin-top: 2px;
  color: #8a9bb0;
  font-size: 12px;
  font-weight: 700;
}

.notifications-mark-all {
  display: block;
  margin-top: 6px;
  border: none;
  background: transparent;
  padding: 0;
  color: #457b9d;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.notifications-mark-all:hover {
  text-decoration: underline;
}

.notifications-close {
  width: 26px;
  height: 26px;
  border-radius: 999px;
  border: none;
  background: #f4f7f9;
  color: #6c7a89;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.notifications-empty {
  padding: 22px 16px;
  text-align: center;
  color: #8a9bb0;
  font-size: 13px;
  font-weight: 700;
}

.notifications-empty.error {
  color: #e76f51;
}

.notifications-list {
  max-height: 340px;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  gap: 11px;
  padding: 13px 16px;
  border-bottom: 1px solid #eef2f5;
}

.notification-clickable {
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
}

.notification-clickable:hover {
  background: #f8fafb;
}

.notification-icon {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  border-radius: 10px;
  background: #eaf5f5;
  color: #457b9d;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 900;
}

.notification-item.warning .notification-icon {
  background: rgba(244, 162, 97, 0.14);
  color: #d9822b;
}

.notification-item.danger .notification-icon {
  background: rgba(231, 111, 81, 0.14);
  color: #e76f51;
}

.notification-content {
  min-width: 0;
}

.notification-type-label {
  display: inline-block;
  margin-bottom: 3px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 9.5px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.notification-item.warning .notification-type-label,
.notification-item.danger .notification-type-label {
  background: rgba(244, 162, 97, 0.16);
  color: #b9701e;
}

.notification-content strong {
  display: block;
  color: #1d3557;
  font-size: 12.5px;
  font-weight: 900;
}

.notification-content p {
  margin: 3px 0 4px;
  color: #1d3557;
  font-size: 12px;
  line-height: 1.35;
  font-weight: 650;
}

.notification-content span {
  color: #8a9bb0;
  font-size: 11px;
  font-weight: 700;
}

.notification-actions {
  margin-top: 6px;
}

.notification-mark-read {
  border: none;
  background: transparent;
  padding: 0;
  color: #457b9d;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.notification-mark-read:hover {
  text-decoration: underline;
}

.notifications-link {
  display: block;
  padding: 12px 16px;
  text-align: center;
  color: #457b9d;
  font-size: 12px;
  font-weight: 900;
  text-decoration: none;
  background: #f8fafb;
}

.notifications-link:hover {
  background: #eaf5f5;
}

@media (max-width: 680px) {
  .notifications-dropdown {
    position: fixed;
    top: 74px;
    right: 16px;
    left: 16px;
    width: auto;
    max-width: none;
  }
}

.content {
  padding: 28px 32px 40px;
  max-width: 1400px;
  width: 100%;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 23px;
  font-weight: 800;
  letter-spacing: -0.3px;
  color: var(--navy);
  margin: 0;
}

.subtitle {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
  margin-top: 4px;
}

@media (max-width: 900px) {
  .topbar-search {
    display: none;
  }
}

@media (max-width: 760px) {
  .app-layout {
    --sidebar-w: 76px;
  }

  .content {
    padding: 20px 16px 32px;
  }
}
</style>
