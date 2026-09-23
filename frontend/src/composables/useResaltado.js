import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

/**
 * Resaltado temporal por query param (?resaltar=ID): hace scroll hasta
 * la fila `#{prefijoFila}-{id}` y le aplica la clase `.highlight-row`
 * por unos segundos. Mismo patrón ya usado en Estrategias/Objetivos/
 * Indicadores, extraído acá para no seguir copiándolo.
 */
export function useResaltado(route, paramNombre = 'resaltar', prefijoFila = 'fila') {
  const idResaltado = ref(null)
  let timeoutResaltado = null

  async function aplicarResaltadoDesdeRuta() {
    const idQuery = Number(route.query[paramNombre])

    if (!idQuery) {
      return
    }

    idResaltado.value = idQuery

    await nextTick()

    const fila = document.getElementById(`${prefijoFila}-${idQuery}`)

    if (fila) {
      fila.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }

    if (timeoutResaltado) {
      window.clearTimeout(timeoutResaltado)
    }

    timeoutResaltado = window.setTimeout(() => {
      if (idResaltado.value === idQuery) {
        idResaltado.value = null
      }
    }, 3500)
  }

  watch(
    () => route.query[paramNombre],
    () => {
      aplicarResaltadoDesdeRuta()
    }
  )

  onBeforeUnmount(() => {
    if (timeoutResaltado) {
      window.clearTimeout(timeoutResaltado)
    }
  })

  return { idResaltado, aplicarResaltadoDesdeRuta }
}
