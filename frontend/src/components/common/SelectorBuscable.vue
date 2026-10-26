<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { filtrarOpciones } from '../../utils/busqueda'

/**
 * Selector con filtro de texto, reutilizable para relaciones con listas
 * potencialmente largas (Plan estratégico, Plan anual, Objetivo general...).
 * Reemplaza un <select> nativo sin cambiar el contrato: v-model recibe/emite
 * el id de la opción seleccionada.
 *
 * Teclado: Enter/Espacio/flecha abajo abre; flechas recorren las opciones;
 * Enter elige; Escape cierra. La búsqueda ignora mayúsculas y acentos, y se
 * limpia con el botón ×. `variante="toolbar"` lo adapta a las barras de
 * filtros (sin borde propio, como el <select> que reemplaza).
 */
const props = defineProps({
  modelValue: {
    type: [Number, String],
    default: '',
  },
  opciones: {
    type: Array,
    default: () => [],
  },
  placeholder: {
    type: String,
    default: 'Seleccionar...',
  },
  placeholderBusqueda: {
    type: String,
    default: 'Escribí para filtrar...',
  },
  mensajeVacio: {
    type: String,
    default: 'Sin resultados',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  variante: {
    type: String,
    default: 'campo',
  },
  etiqueta: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue'])

const contenedor = ref(null)
const campoBusqueda = ref(null)
const disparador = ref(null)
const lista = ref(null)
const abierto = ref(false)
const busqueda = ref('')
const indiceActivo = ref(-1)
const idLista = `selector-lista-${Math.random().toString(36).slice(2, 9)}`

const opcionSeleccionada = computed(() => {
  return (
    props.opciones.find((opcion) => String(opcion.id) === String(props.modelValue)) || null
  )
})

const opcionesFiltradas = computed(() => filtrarOpciones(props.opciones, busqueda.value))

watch(
  () => props.disabled,
  (esDisabled) => {
    if (esDisabled) {
      abierto.value = false
    }
  }
)

watch(busqueda, () => {
  indiceActivo.value = opcionesFiltradas.value.length ? 0 : -1
})

function alternar() {
  if (props.disabled) {
    return
  }

  if (abierto.value) {
    cerrar()
  } else {
    abrir()
  }
}

function abrir() {
  abierto.value = true
  busqueda.value = ''
  indiceActivo.value = Math.max(
    opcionesFiltradas.value.findIndex((opcion) => String(opcion.id) === String(props.modelValue)),
    0,
  )

  nextTick(() => {
    campoBusqueda.value?.focus()
    asegurarVisible()
  })
}

function cerrar({ devolverFoco = false } = {}) {
  abierto.value = false
  busqueda.value = ''
  indiceActivo.value = -1

  if (devolverFoco) {
    nextTick(() => disparador.value?.focus())
  }
}

function seleccionar(opcion) {
  emit('update:modelValue', opcion.id)
  cerrar({ devolverFoco: true })
}

function limpiarBusqueda() {
  busqueda.value = ''
  campoBusqueda.value?.focus()
}

function mover(paso) {
  const total = opcionesFiltradas.value.length

  if (!total) return

  indiceActivo.value = (indiceActivo.value + paso + total) % total
  nextTick(asegurarVisible)
}

function asegurarVisible() {
  lista.value?.querySelector('.selector-opcion.resaltada')?.scrollIntoView({ block: 'nearest' })
}

function elegirActiva() {
  const opcion = opcionesFiltradas.value[indiceActivo.value]

  if (opcion) seleccionar(opcion)
}

function teclaEnDisparador(evento) {
  if (['ArrowDown', 'ArrowUp'].includes(evento.key)) {
    evento.preventDefault()
    abrir()
  }
}

function manejarClickFuera(evento) {
  if (contenedor.value && !contenedor.value.contains(evento.target)) {
    cerrar()
  }
}

onMounted(() => {
  document.addEventListener('click', manejarClickFuera)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', manejarClickFuera)
})
</script>

<template>
  <div ref="contenedor" class="selector-buscable" :class="`variante-${variante}`">
    <button
      ref="disparador"
      type="button"
      class="selector-trigger"
      :class="{ abierto: abierto }"
      :disabled="disabled"
      :aria-label="etiqueta || undefined"
      aria-haspopup="listbox"
      :aria-expanded="abierto"
      @click="alternar"
      @keydown="teclaEnDisparador"
    >
      <span :class="{ placeholder: !opcionSeleccionada }">
        {{ opcionSeleccionada ? opcionSeleccionada.texto : placeholder }}
      </span>

      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>

    <div v-if="abierto" class="selector-panel">
      <div class="selector-busqueda-fila">
        <input
          ref="campoBusqueda"
          v-model="busqueda"
          type="text"
          class="selector-busqueda"
          role="combobox"
          aria-autocomplete="list"
          :aria-controls="idLista"
          :aria-activedescendant="indiceActivo >= 0 ? `${idLista}-${indiceActivo}` : undefined"
          :placeholder="placeholderBusqueda"
          @keydown.esc.prevent="cerrar({ devolverFoco: true })"
          @keydown.down.prevent="mover(1)"
          @keydown.up.prevent="mover(-1)"
          @keydown.enter.prevent="elegirActiva"
          @keydown.tab="cerrar()"
        />
        <button
          v-if="busqueda"
          type="button"
          class="selector-limpiar"
          aria-label="Limpiar búsqueda"
          title="Limpiar búsqueda"
          @click.stop="limpiarBusqueda"
        >
          ×
        </button>
      </div>

      <ul :id="idLista" ref="lista" class="selector-lista" role="listbox">
        <li v-if="!opcionesFiltradas.length" class="selector-vacio">
          {{ mensajeVacio }}
        </li>

        <li
          v-for="(opcion, indice) in opcionesFiltradas"
          :id="`${idLista}-${indice}`"
          :key="opcion.id"
          class="selector-opcion"
          role="option"
          :aria-selected="String(opcion.id) === String(modelValue)"
          :class="{ activa: String(opcion.id) === String(modelValue), resaltada: indice === indiceActivo }"
          @mouseenter="indiceActivo = indice"
          @click.stop.prevent="seleccionar(opcion)"
        >
          {{ opcion.texto }}
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.selector-buscable {
  position: relative;
  width: 100%;
}

.selector-trigger {
  width: 100%;
  min-width: 0;
  border: 1.5px solid #e4eaef;
  border-radius: 11px;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 13px;
  font-weight: 650;
  padding: 11px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.selector-trigger span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.selector-trigger span.placeholder {
  color: #9aa8b8;
  font-weight: 600;
}

.selector-trigger svg {
  flex-shrink: 0;
  color: #9aa8b8;
  transition: transform 0.15s ease;
}

.selector-trigger.abierto svg {
  transform: rotate(180deg);
}

.selector-trigger:focus-visible,
.selector-trigger.abierto {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
  outline: none;
}

.selector-trigger:disabled {
  background: #f4f7f9;
  color: #9aa8b8;
  cursor: not-allowed;
}

/* Barras de filtros: el contenedor .toolbar-filter ya dibuja el borde. */
.variante-toolbar {
  width: auto;
  min-width: 0;
  max-width: 260px;
}

.variante-toolbar .selector-trigger {
  border: none;
  background: transparent;
  padding: 0;
  font-weight: 700;
  box-shadow: none;
}

.variante-toolbar .selector-trigger:focus-visible {
  outline: 2px solid #a8dadc;
  outline-offset: 3px;
  border-radius: 4px;
}

.variante-toolbar .selector-panel {
  min-width: 260px;
  top: calc(100% + 14px);
  left: -12px;
  right: auto;
}

.selector-panel {
  position: absolute;
  z-index: 40;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: #ffffff;
  border: 1.5px solid #e4eaef;
  border-radius: 12px;
  box-shadow: 0 16px 34px rgba(29, 53, 87, 0.16);
  overflow: hidden;
}

.selector-busqueda-fila {
  display: flex;
  align-items: center;
  border-bottom: 1px solid #eef2f5;
}

.selector-busqueda {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  padding: 11px 12px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  color: #1d3557;
  box-sizing: border-box;
}

.selector-busqueda::placeholder {
  color: #9aa8b8;
}

.selector-limpiar {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  margin-right: 6px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #9aa8b8;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.selector-limpiar:hover {
  background: #eaf5f5;
  color: #457b9d;
}

.selector-lista {
  list-style: none;
  margin: 0;
  padding: 6px;
  max-height: 220px;
  overflow-y: auto;
}

.selector-opcion {
  padding: 9px 10px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 650;
  color: #1d3557;
  cursor: pointer;
}

.selector-opcion.resaltada {
  background: #eaf5f5;
}

.selector-opcion.activa {
  background: #1d3557;
  color: #ffffff;
}

.selector-vacio {
  padding: 12px 10px;
  font-size: 12.5px;
  font-weight: 650;
  color: #9aa8b8;
  text-align: center;
}

@media (max-width: 640px) {
  .variante-toolbar {
    flex: 1;
    max-width: 100%;
  }

  .variante-toolbar .selector-panel {
    min-width: 0;
    left: -12px;
    right: -12px;
  }
}
</style>
