<script setup>
import SidebarMenu from './SidebarMenu.vue'
import ProfileDropdown from './ProfileDropdown.vue'

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

function cerrarSesion() {
  emit('logout')
}
</script>

<template>
  <div class="app-layout">
    <SidebarMenu :usuario="props.usuario" />

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
