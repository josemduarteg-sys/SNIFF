import { computed, ref, watch } from 'vue'

/**
 * Paginación frontend uniforme (Bloque 7): recibe la lista YA filtrada
 * (búsqueda + filtros aplicados por la vista) y corta ese resultado con
 * slice(). Nunca pagina antes de filtrar — la vista arma su propio
 * `computed` de filtrado y se lo pasa acá.
 *
 * Al cambiar la lista filtrada (nueva búsqueda, nuevo filtro, nuevos datos
 * cargados) o la cantidad por página, vuelve automáticamente a la página 1.
 */
export function usePaginacion(listaFiltrada, opciones = {}) {
  const porPaginaInicial = opciones.porPaginaInicial || 10

  const paginaActual = ref(1)
  const porPagina = ref(porPaginaInicial)

  const totalResultados = computed(() => listaFiltrada.value.length)

  // Nunca "Página 1 de 0": con 0 resultados se mantiene en 1 igual, la
  // vista es la que decide si oculta la navegación (ver Paginacion.vue).
  const totalPaginas = computed(() => {
    return Math.max(1, Math.ceil(totalResultados.value / porPagina.value))
  })

  const elementosVisibles = computed(() => {
    const inicio = (paginaActual.value - 1) * porPagina.value
    return listaFiltrada.value.slice(inicio, inicio + porPagina.value)
  })

  const rangoInicio = computed(() => {
    if (!totalResultados.value) return 0
    return (paginaActual.value - 1) * porPagina.value + 1
  })

  const rangoFin = computed(() => {
    return Math.min(paginaActual.value * porPagina.value, totalResultados.value)
  })

  watch(listaFiltrada, () => {
    paginaActual.value = 1
  })

  watch(porPagina, () => {
    paginaActual.value = 1
  })

  function irAPagina(pagina) {
    if (pagina < 1 || pagina > totalPaginas.value) return
    paginaActual.value = pagina
  }

  return {
    paginaActual,
    porPagina,
    totalResultados,
    totalPaginas,
    elementosVisibles,
    rangoInicio,
    rangoFin,
    irAPagina,
  }
}
