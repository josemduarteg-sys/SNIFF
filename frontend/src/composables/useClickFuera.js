import { onBeforeUnmount, onMounted } from 'vue'

/**
 * Mismo patrón ya usado en SelectorBuscable.vue (click en `document` +
 * `contenedor.contains(evento.target)`), extraído acá para reutilizarlo
 * en el Centro de notificaciones (Bloque 7) sin duplicar el listener a
 * mano ni instalar una librería. No modifica SelectorBuscable.vue.
 */
export function useClickFuera(contenedorRef, callback) {
  function manejarClick(evento) {
    if (contenedorRef.value && !contenedorRef.value.contains(evento.target)) {
      callback(evento)
    }
  }

  onMounted(() => {
    document.addEventListener('click', manejarClick)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', manejarClick)
  })
}
