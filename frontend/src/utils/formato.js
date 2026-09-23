export function formatearNumero(valor, opciones = {}) {
  const { decimales = 2, unidad = '' } = opciones

  if (valor === null || valor === undefined || valor === '') {
    return '-'
  }

  const numero = Number(valor)

  if (Number.isNaN(numero)) {
    return String(valor)
  }

  const texto = numero.toLocaleString('es-GT', {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  })

  if (!unidad) {
    return texto
  }

  if (unidad === 'Q') {
    return `Q ${texto}`
  }

  return `${texto} ${unidad}`
}

/**
 * Diferencia matemática y neutral entre resultado y meta, SOLO para
 * presentación (no altera el cálculo de cumplimiento del backend). No
 * clasifica si la diferencia es favorable o desfavorable.
 */
export function formatearDiferencia(valorResultado, valorMeta, opciones = {}) {
  const { decimales = 2, unidad = '' } = opciones

  const resultado = Number(valorResultado)
  const meta = Number(valorMeta)

  if (
    valorResultado === null || valorResultado === undefined || valorResultado === '' ||
    valorMeta === null || valorMeta === undefined || valorMeta === '' ||
    Number.isNaN(resultado) || Number.isNaN(meta)
  ) {
    return '-'
  }

  const diferencia = resultado - meta
  const signo = diferencia > 0 ? '+' : diferencia < 0 ? '-' : ''
  const magnitud = Math.abs(diferencia).toLocaleString('es-GT', {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  })

  if (unidad === '%') {
    return `${signo}${magnitud} puntos porcentuales`
  }

  if (unidad === 'Q') {
    return `${signo}Q ${magnitud}`
  }

  if (!unidad) {
    return `${signo}${magnitud}`
  }

  return `${signo}${magnitud} ${unidad}`
}
