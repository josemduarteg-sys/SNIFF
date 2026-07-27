<script setup>
import { onMounted, ref } from 'vue'
import LoginView from './views/LoginView.vue'
import DashboardView from './views/DashboardView.vue'
import { estaAutenticado, logout, obtenerUsuarioActual } from './services/authService'

const usuario = ref(null)
const cargandoSesion = ref(true)

async function cargarSesion() {
  if (!estaAutenticado()) {
    usuario.value = null
    cargandoSesion.value = false
    return
  }

  try {
    usuario.value = await obtenerUsuarioActual()
  } catch (error) {
    logout()
    usuario.value = null
  } finally {
    cargandoSesion.value = false
  }
}

function manejarLoginExitoso(usuarioAutenticado) {
  usuario.value = usuarioAutenticado
}

function manejarLogout() {
  logout()
  usuario.value = null
}

onMounted(() => {
  cargarSesion()
})
</script>

<template>
  <div v-if="cargandoSesion" class="loading">
    Cargando...
  </div>

  <LoginView
    v-else-if="!usuario"
    @login-success="manejarLoginExitoso"
  />

  <DashboardView
    v-else
    :usuario="usuario"
    @logout="manejarLogout"
  />
</template>

<style scoped>
.loading {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f6f9fa;
  color: #1d3557;
  font-family: Arial, sans-serif;
  font-weight: 700;
}
</style>
