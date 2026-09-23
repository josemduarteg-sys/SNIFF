import { ref } from 'vue'

/**
 * Reemplazo reutilizable de window.confirm(): en vez de bloquear con un
 * cuadro nativo del navegador, guarda la acción pendiente y la ejecuta solo
 * si el usuario confirma desde ConfirmacionModal.vue. No cambia qué hace
 * cada operación, solo cómo se solicita la confirmación.
 */
export function useConfirmacion() {
  const solicitud = ref(null)

  function solicitar({
    titulo = 'Confirmar acción',
    mensaje = '',
    textoSecundario = '',
    textoConfirmar = 'Confirmar',
    textoCancelar = 'Cancelar',
    variante = 'normal',
    accion,
  }) {
    solicitud.value = {
      titulo,
      mensaje,
      textoSecundario,
      textoConfirmar,
      textoCancelar,
      variante,
      accion,
    }
  }

  function cancelar() {
    solicitud.value = null
  }

  async function confirmar() {
    const pendiente = solicitud.value
    solicitud.value = null

    if (pendiente?.accion) {
      await pendiente.accion()
    }
  }

  return { solicitud, solicitar, cancelar, confirmar }
}
