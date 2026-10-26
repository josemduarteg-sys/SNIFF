// Búsqueda de texto en selectores (SelectorBuscable): sin distinguir
// mayúsculas ni acentos, por cualquier parte del texto.

export function normalizarTexto(texto) {
  return String(texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

export function filtrarOpciones(opciones, busqueda) {
  const texto = normalizarTexto(busqueda)

  if (!texto) return opciones || []

  return (opciones || []).filter((opcion) => normalizarTexto(opcion.texto).includes(texto))
}
