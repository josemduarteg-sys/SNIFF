<script setup>
defineProps({
  abierto: {
    type: Boolean,
    required: true,
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
  ancho: {
    type: String,
    required: false,
    default: '680px',
  },
})

const emit = defineEmits(['cerrar'])

function cerrar() {
  emit('cerrar')
}
</script>

<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="abierto" class="modal-backdrop" @click.self="cerrar">
        <section class="modal-card" :style="{ maxWidth: ancho }">
          <header class="modal-header">
            <div>
              <h2>{{ titulo }}</h2>
              <p v-if="subtitulo">{{ subtitulo }}</p>
            </div>

            <button class="close-btn" type="button" title="Cerrar" @click="cerrar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </header>

          <div class="modal-body">
            <slot></slot>
          </div>
        </section>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(21, 40, 64, 0.42);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 22px;
}

.modal-card {
  width: 100%;
  max-height: calc(100vh - 44px);
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 18px;
  box-shadow: 0 24px 70px rgba(29, 53, 87, 0.22);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 20px 22px;
  border-bottom: 1px solid #eef2f5;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.modal-header h2 {
  margin: 0;
  color: #1d3557;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.2px;
}

.modal-header p {
  margin: 5px 0 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 500;
}

.close-btn {
  width: 34px;
  height: 34px;
  border: 1px solid #e4eaef;
  border-radius: 10px;
  background: #ffffff;
  color: #5e6e82;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.close-btn:hover {
  background: rgba(231, 111, 81, 0.10);
  color: #e76f51;
  border-color: rgba(231, 111, 81, 0.25);
}

.close-btn svg {
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
}

.modal-body {
  padding: 22px;
  overflow-y: auto;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.16s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-card,
.modal-fade-leave-active .modal-card {
  transition: transform 0.16s ease;
}

.modal-fade-enter-from .modal-card,
.modal-fade-leave-to .modal-card {
  transform: translateY(8px) scale(0.98);
}
</style>
