<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const router = useRouter()
const abierto = ref(false)
const dropdownRef = ref(null)

const inicialesUsuario = computed(() => {
  const nombre = props.usuario?.username || 'Usuario'
  return nombre.slice(0, 2).toUpperCase()
})

const nombreUsuario = computed(() => {
  return props.usuario?.username || 'Usuario'
})

const rolUsuario = computed(() => {
  return props.usuario?.rol_nombre || 'Sin rol'
})

function alternarDropdown() {
  abierto.value = !abierto.value
}

function cerrarDropdown() {
  abierto.value = false
}

function irConfiguracion() {
  cerrarDropdown()
  router.push('/configuracion')
}

function cerrarSesion() {
  cerrarDropdown()
  emit('logout')
}

function manejarClickFuera(event) {
  if (!dropdownRef.value) return

  if (!dropdownRef.value.contains(event.target)) {
    cerrarDropdown()
  }
}

onMounted(() => {
  document.addEventListener('click', manejarClickFuera)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', manejarClickFuera)
})
</script>

<template>
  <div ref="dropdownRef" class="profile-dropdown">
    <button
      class="profile-trigger"
      type="button"
      @click="alternarDropdown"
    >
      <div class="avatar-sm">
        {{ inicialesUsuario }}
      </div>

      <svg
        class="chev"
        :class="{ open: abierto }"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>

    <transition name="dropdown">
      <div v-if="abierto" class="dropdown-menu">
        <div class="dropdown-header">
          <div class="avatar-lg">
            {{ inicialesUsuario }}
          </div>

          <div>
            <div class="user-name">
              {{ nombreUsuario }}
            </div>

            <div class="user-role">
              {{ rolUsuario }}
            </div>
          </div>
        </div>

        <div class="dropdown-divider"></div>

        <button
          class="dropdown-item"
          type="button"
          @click="irConfiguracion"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" />
          </svg>

          <span>Mi perfil</span>
        </button>

        <button
          class="dropdown-item"
          type="button"
          @click="irConfiguracion"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>

          <span>Configuración</span>
        </button>

        <div class="dropdown-divider"></div>

        <button
          class="dropdown-item danger"
          type="button"
          @click="cerrarSesion"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>

          <span>Cerrar sesión</span>
        </button>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.profile-dropdown {
  position: relative;
}

.profile-trigger {
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

.profile-trigger:hover {
  background: #f6f9fa;
}

.avatar-sm,
.avatar-lg {
  border-radius: 10px;
  background: #eaf5f5;
  color: #457b9d;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-sm {
  width: 34px;
  height: 34px;
  font-size: 12px;
}

.avatar-lg {
  width: 42px;
  height: 42px;
  font-size: 13px;
}

.chev {
  color: #9aa8b8;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.15s ease;
}

.chev.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 235px;
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 14px;
  box-shadow: 0 14px 34px rgba(29, 53, 87, 0.14);
  padding: 10px;
  z-index: 50;
}

.dropdown-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
}

.user-name {
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
}

.user-role {
  color: #9aa8b8;
  font-size: 11.5px;
  font-weight: 600;
  margin-top: 2px;
}

.dropdown-divider {
  height: 1px;
  background: #eef2f5;
  margin: 8px 0;
}

.dropdown-item {
  width: 100%;
  min-height: 36px;
  border: none;
  background: transparent;
  border-radius: 9px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 10px;
  color: #1d3557;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 750;
  cursor: pointer;
  text-align: left;
}

.dropdown-item svg {
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}

.dropdown-item:hover {
  background: #eaf5f5;
  color: #457b9d;
}

.dropdown-item.danger {
  color: #e76f51;
}

.dropdown-item.danger:hover {
  background: rgba(231, 111, 81, 0.1);
  color: #e76f51;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.14s ease, transform 0.14s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}
</style>