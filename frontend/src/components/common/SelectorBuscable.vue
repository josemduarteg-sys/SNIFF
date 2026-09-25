<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

/**
 * Selector con filtro de texto, reutilizable para relaciones con listas
 * potencialmente largas (Plan estratégico, Plan anual, Objetivo general...).
 * Reemplaza un <select> nativo sin cambiar el contrato: v-model recibe/emite
 * el id de la opción seleccionada.
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
})

const emit = defineEmits(['update:modelValue'])

const contenedor = ref(null)
const campoBusqueda = ref(null)
const abierto = ref(false)
const busqueda = ref('')

const opcionSeleccionada = computed(() => {
  return (
    props.opciones.find((opcion) => String(opcion.id) === String(props.modelValue)) || null
  )
})

const opcionesFiltradas = computed(() => {
  const texto = busqueda.value.trim().toLowerCase()

  if (!texto) {
    return props.opciones
  }

  return props.opciones.filter((opcion) => opcion.texto.toLowerCase().includes(texto))
})

watch(
  () => props.disabled,
  (esDisabled) => {
    if (esDisabled) {
      abierto.value = false
    }
  }
)

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

  nextTick(() => {
    campoBusqueda.value?.focus()
  })
}

function cerrar() {
  abierto.value = false
  busqueda.value = ''
}

function seleccionar(opcion) {
  emit('update:modelValue', opcion.id)
  cerrar()
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
  <div ref="contenedor" class="selector-buscable">
    <button
      type="button"
      class="selector-trigger"
      :class="{ abierto: abierto }"
      :disabled="disabled"
      @click="alternar"
    >
      <span :class="{ placeholder: !opcionSeleccionada }">
        {{ opcionSeleccionada ? opcionSeleccionada.texto : placeholder }}
      </span>

      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>

    <div v-if="abierto" class="selector-panel">
      <input
        ref="campoBusqueda"
        v-model="busqueda"
        type="text"
        class="selector-busqueda"
        :placeholder="placeholderBusqueda"
        @keydown.esc="cerrar"
      />

      <ul class="selector-lista">
        <li v-if="!opcionesFiltradas.length" class="selector-vacio">
          {{ mensajeVacio }}
        </li>

        <li
          v-for="opcion in opcionesFiltradas"
          :key="opcion.id"
          class="selector-opcion"
          :class="{ activa: String(opcion.id) === String(modelValue) }"
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

.selector-busqueda {
  width: 100%;
  border: none;
  border-bottom: 1px solid #eef2f5;
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

.selector-opcion:hover {
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
</style>
