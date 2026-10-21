<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  estaAutenticado,
  logout,
  obtenerUsuarioActual,
  registrarCierreSesion,
} from './services/authService'
import { registrarAlExpirarSesion } from './services/api'
import { esRutaRetornoSegura } from './services/sesion'

const router = useRouter()

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

    if (usuario.value?.debe_cambiar_password && router.currentRoute.value.path !== '/cambio-password-obligatorio') {
      router.replace('/cambio-password-obligatorio')
    }
  } catch (error) {
    logout()
    usuario.value = null
    router.push('/login')
  } finally {
    cargandoSesion.value = false
  }
}

function manejarLoginExitoso(usuarioAutenticado) {
  usuario.value = usuarioAutenticado

  if (usuarioAutenticado?.debe_cambiar_password) {
    router.push('/cambio-password-obligatorio')
    return
  }

  // Etapa 2 (A3): vuelve a la pantalla que estaba abierta cuando venció la
  // sesión. Los permisos de esa ruta los vuelve a revisar el guard.
  const retorno = router.currentRoute.value.query.redirect
  router.push(esRutaRetornoSegura(retorno) ? retorno : '/dashboard')
}

// Etapa 2 (A3): la sesión venció y no pudo renovarse (ver services/sesion.js).
registrarAlExpirarSesion(() => {
  usuario.value = null

  const rutaActual = router.currentRoute.value

  if (rutaActual.meta?.public) {
    return
  }

  const query = { sesion: 'expirada' }

  if (esRutaRetornoSegura(rutaActual.fullPath)) {
    query.redirect = rutaActual.fullPath
  }

  router.replace({ path: '/login', query })
})

async function manejarLogout() {
  await registrarCierreSesion()
  logout()
  usuario.value = null
  router.push('/login')
}

function manejarUsuarioActualizado(usuarioActualizado) {
  usuario.value = usuarioActualizado
}

onMounted(() => {
  cargarSesion()
})
</script>

<template>
  <div v-if="cargandoSesion" class="loading">
    Cargando...
  </div>

  <router-view v-else v-slot="{ Component }">
    <component
      :is="Component"
      :usuario="usuario"
      @login-success="manejarLoginExitoso"
      @logout="manejarLogout"
      @usuario-actualizado="manejarUsuarioActualizado"
    />
  </router-view>
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

