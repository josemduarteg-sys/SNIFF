<script setup>
import { computed } from 'vue'
import sniffLogo from '../../assets/images/sniff-logo.png'

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

const inicialesUsuario = computed(() => {
  const nombre = props.usuario?.username || 'Usuario'
  return nombre.slice(0, 2).toUpperCase()
})

function cerrarSesion() {
  emit('logout')
}
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <img :src="sniffLogo" alt="Sniff" />
        <div class="wordmark">Sniff<span>.</span></div>
      </div>

      <nav class="nav-section">
        <div class="nav-label">General</div>

        <RouterLink
          to="/dashboard"
          class="nav-item"
          active-class="active"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="7" height="9" rx="1.5" />
            <rect x="14" y="3" width="7" height="5" rx="1.5" />
            <rect x="14" y="12" width="7" height="9" rx="1.5" />
            <rect x="3" y="16" width="7" height="5" rx="1.5" />
          </svg>
          <span>Dashboard</span>
        </RouterLink>

        <div class="nav-label top-space">Planeación</div>

        <RouterLink
          to="/estrategias"
          class="nav-item"
          active-class="active"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" />
            <circle cx="12" cy="12" r="5" />
            <circle cx="12" cy="12" r="1" />
          </svg>
          <span>Estrategias</span>
        </RouterLink>

        <RouterLink
          to="/objetivos"
          class="nav-item"
          active-class="active"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 21V4a1 1 0 0 1 1-1h9l4 4v3" />
            <path d="M4 14h8" />
            <path d="M4 21h9" />
            <circle cx="18" cy="16" r="4" />
          </svg>
          <span>Objetivos</span>
        </RouterLink>

        <RouterLink
          to="/indicadores"
          class="nav-item"
          active-class="active"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
          <span>Indicadores (KPI)</span>
        </RouterLink>

        <RouterLink
          to="/mediciones"
          class="nav-item"
          active-class="active"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <rect x="4" y="3" width="16" height="18" rx="2" />
            <path d="M9 3v3h6V3" />
            <polyline points="8.5 13 11 15.5 15.5 10.5" />
          </svg>
          <span>Registro de Mediciones</span>
        </RouterLink>

        <RouterLink
          to="/dashboard"
          class="nav-item"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
            <path d="M9 3v15M15 6v15" />
          </svg>
          <span>Mapa Estratégico</span>
        </RouterLink>

        <div class="nav-label top-space">Sistema</div>

        <RouterLink
          to="/dashboard"
          class="nav-item"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span>Configuración</span>
        </RouterLink>
      </nav>

      <div class="sidebar-user">
        <div class="avatar-sm">{{ inicialesUsuario }}</div>
        <div>
          <div class="name">{{ usuario?.username || 'Usuario' }}</div>
          <div class="role">{{ usuario?.rol_nombre || 'Sin rol' }}</div>
        </div>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="breadcrumb">
          <span>Sniff</span>

          <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
            <polyline points="9 18 15 12 9 6" />
          </svg>

          <span class="current">{{ breadcrumbActual }}</span>
        </div>

        <div class="topbar-search">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>

          <input type="text" placeholder="Buscar objetivos, indicadores..." />
        </div>

        <div class="topbar-actions">
          <div class="icon-btn">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
              <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>

            <span class="dot"></span>
          </div>

          <button
            class="topbar-profile"
            type="button"
            title="Cerrar sesión"
            @click="cerrarSesion"
          >
            <div class="avatar-sm">{{ inicialesUsuario }}</div>

            <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
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

.sidebar {
  width: var(--sidebar-w);
  min-height: 100vh;
  background: var(--white);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
}

.sidebar-brand {
  height: 72px;
  padding: 18px 22px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border);
}

.sidebar-brand img {
  width: 34px;
  height: 34px;
  border-radius: 9px;
}

.wordmark {
  font-size: 21px;
  font-weight: 800;
  color: var(--navy);
  letter-spacing: -0.4px;
}

.wordmark span {
  color: var(--steel);
}

.nav-section {
  padding: 18px 14px;
  flex: 1;
}

.nav-label {
  font-size: 11px;
  font-weight: 800;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  padding: 0 10px;
  margin-bottom: 8px;
}

.top-space {
  margin-top: 14px;
}

.nav-item {
  height: 40px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 12px;
  border-radius: 9px;
  color: var(--navy);
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 6px;
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-item svg {
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}

.nav-item:hover {
  background: var(--aqua-soft);
  color: var(--steel);
}

.nav-item.active {
  background: var(--navy);
  color: var(--white);
}

.sidebar-user {
  border-top: 1px solid var(--border);
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-sm {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--aqua-soft);
  color: var(--steel);
  font-size: 12px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sidebar-user .name {
  font-size: 13px;
  font-weight: 800;
  color: var(--navy);
}

.sidebar-user .role {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
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

.icon-btn .dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--orange);
  border: 1.5px solid var(--white);
}

.topbar-profile {
  border: none;
  background: transparent;
  font-family: inherit;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 6px 5px 5px;
  border-radius: 10px;
  cursor: pointer;
}

.topbar-profile:hover {
  background: var(--bg);
}

.topbar-profile .chev {
  color: var(--text-muted);
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
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

  .sidebar-brand .wordmark,
  .nav-label,
  .nav-item span,
  .sidebar-user .name,
  .sidebar-user .role {
    display: none;
  }

  .sidebar-brand {
    justify-content: center;
    padding: 20px 0;
  }

  .nav-item {
    justify-content: center;
  }

  .sidebar-user {
    justify-content: center;
  }

  .content {
    padding: 20px 16px 32px;
  }
}
</style>