<script setup>
import { computed } from 'vue'
import sniffLogo from '../../assets/images/sniff-logo.png'
import {
  puedeGestionarUsuarios,
  puedeVerBitacora,
} from '../../utils/permisos'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
  contraido: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['alternar'])

const inicialesUsuario = computed(() => {
  const nombre = props.usuario?.username || 'Usuario'
  return nombre.slice(0, 2).toUpperCase()
})

const mostrarUsuarios = computed(() => puedeGestionarUsuarios(props.usuario))
const mostrarBitacora = computed(() => puedeVerBitacora(props.usuario))
</script>

<template>
  <aside class="sidebar-menu" :class="{ collapsed: contraido }">
    <button
      class="sidebar-brand brand-button"
      type="button"
      title="Contraer o expandir menú"
      @click="emit('alternar')"
    >
      <img :src="sniffLogo" alt="Sniff" />
      <div class="wordmark">Sniff<span>.</span></div>
    </button>

    <nav class="nav-section">
      <div class="nav-label">General</div>

      <RouterLink to="/dashboard" class="nav-item" active-class="active">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="3" width="7" height="9" rx="1.5" />
          <rect x="14" y="3" width="7" height="5" rx="1.5" />
          <rect x="14" y="12" width="7" height="9" rx="1.5" />
          <rect x="3" y="16" width="7" height="5" rx="1.5" />
        </svg>
        <span>Dashboard</span>
      </RouterLink>

      <div class="nav-label top-space">Planeación</div>

      <RouterLink to="/estrategias" class="nav-item" active-class="active">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="5" />
          <circle cx="12" cy="12" r="1" />
        </svg>
        <span>Estrategias</span>
      </RouterLink>

      <RouterLink to="/objetivos" class="nav-item" active-class="active">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M4 21V4a1 1 0 0 1 1-1h9l4 4v3" />
          <path d="M4 14h8" />
          <path d="M4 21h9" />
          <circle cx="18" cy="16" r="4" />
        </svg>
        <span>Objetivos</span>
      </RouterLink>

      <RouterLink to="/indicadores" class="nav-item" active-class="active">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
        <span>Indicadores (KPI)</span>
      </RouterLink>

      <RouterLink to="/mediciones" class="nav-item" active-class="active">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect x="4" y="3" width="16" height="18" rx="2" />
          <path d="M9 3v3h6V3" />
          <polyline points="8.5 13 11 15.5 15.5 10.5" />
        </svg>
        <span>Registro de Mediciones</span>
      </RouterLink>

      <RouterLink to="/dashboard" class="nav-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
          <path d="M9 3v15M15 6v15" />
        </svg>
        <span>Mapa Estratégico</span>
      </RouterLink>

      <div class="nav-label top-space">Sistema</div>

      <RouterLink to="/configuracion" class="nav-item" active-class="active">
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
</template>

<style scoped>
.sidebar-menu {
  width: var(--sidebar-w);
  min-width: var(--sidebar-w);
  height: 100vh;
  background: var(--white);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  left: 0;
  overflow-y: auto;
  transition: width 0.2s ease, min-width 0.2s ease;
}

.sidebar-menu.collapsed {
  width: 78px;
  min-width: 78px;
}

.sidebar-brand {
  height: 72px;
  padding: 18px 22px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border);
}

.sidebar-menu.collapsed .sidebar-brand {
  justify-content: center;
  padding: 18px 0;
}

.brand-button {
  width: 100%;
  border: none;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}

.brand-button:hover img {
  transform: scale(1.04);
}

.sidebar-brand img {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  transition: transform 0.15s ease;
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

.sidebar-menu.collapsed .wordmark,
.sidebar-menu.collapsed .nav-label,
.sidebar-menu.collapsed .nav-item span,
.sidebar-menu.collapsed .sidebar-user .name,
.sidebar-menu.collapsed .sidebar-user .role {
  display: none;
}

.sidebar-menu.collapsed .nav-item {
  justify-content: center;
}

.sidebar-menu.collapsed .sidebar-user {
  justify-content: center;
}

@media (max-width: 760px) {
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
}
</style>
