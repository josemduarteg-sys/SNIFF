<script setup>
import AppLayout from '../components/layout/AppLayout.vue'

// Pantalla temporal "Próximamente" (ver también el enlace del menú lateral
// en SidebarMenu.vue, que ahora apunta a /mapa-estrategico). No existe
// todavía ninguna implementación previa del Mapa Estratégico que
// conservar: el enlace del menú apuntaba directamente a /dashboard como
// placeholder provisional antes de este cambio.
//
// Para retomar la implementación definitiva: reemplazar el contenido de
// <template> de este archivo (dejando el mismo AppLayout/título/
// breadcrumb) por la pantalla real, sin necesidad de tocar el router ni
// el menú lateral.

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

function cerrarSesion() {
  emit('logout')
}
</script>

<template>
  <AppLayout
    :usuario="props.usuario"
    titulo="Mapa estratégico"
    subtitulo="Visualización jerárquica de planes estratégicos, planes anuales y objetivos"
    breadcrumb-actual="Mapa Estratégico"
    @logout="cerrarSesion"
  >
    <div class="proximamente-wrapper">
      <div class="proximamente-card">
        <div class="proximamente-icono">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
            <path d="M9 3v15M15 6v15" />
          </svg>
        </div>

        <span class="proximamente-eyebrow">Próximamente</span>

        <p class="proximamente-texto">
          Esta funcionalidad se encuentra pendiente de implementación y estará disponible en una
          próxima actualización del sistema.
        </p>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.proximamente-wrapper {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
}

.proximamente-card {
  width: 100%;
  max-width: 460px;
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 20px;
  box-shadow: 0 2px 10px rgba(29, 53, 87, 0.05), 0 1px 2px rgba(29, 53, 87, 0.04);
  padding: 44px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.proximamente-icono {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: rgba(69, 123, 157, 0.1);
  color: #457b9d;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.proximamente-eyebrow {
  font-size: 18px;
  font-weight: 800;
  color: #1d3557;
  margin-bottom: 12px;
}

.proximamente-texto {
  margin: 0;
  font-size: 13.5px;
  font-weight: 500;
  line-height: 1.6;
  color: #5e6e82;
  max-width: 360px;
}

@media (max-width: 640px) {
  .proximamente-wrapper {
    min-height: 320px;
    padding: 16px 8px;
  }

  .proximamente-card {
    padding: 32px 22px;
  }
}
</style>
