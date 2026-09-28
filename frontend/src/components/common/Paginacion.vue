<script setup>
const props = defineProps({
  paginaActual: {
    type: Number,
    required: true,
  },
  totalPaginas: {
    type: Number,
    required: true,
  },
  porPagina: {
    type: Number,
    required: true,
  },
  rangoInicio: {
    type: Number,
    required: true,
  },
  rangoFin: {
    type: Number,
    required: true,
  },
  totalResultados: {
    type: Number,
    required: true,
  },
  opcionesPorPagina: {
    type: Array,
    default: () => [10, 20, 50],
  },
  etiqueta: {
    type: String,
    default: 'resultados',
  },
})

const emit = defineEmits(['cambiar-pagina', 'cambiar-por-pagina'])

function manejarCambioPorPagina(evento) {
  emit('cambiar-por-pagina', Number(evento.target.value))
}
</script>

<template>
  <div v-if="totalResultados > 0" class="paginacion">
    <div class="paginacion-info">
      Mostrando {{ rangoInicio }}–{{ rangoFin }} de {{ totalResultados }} {{ etiqueta }}
    </div>

    <div class="paginacion-controles">
      <label class="paginacion-por-pagina">
        Mostrar
        <select :value="porPagina" @change="manejarCambioPorPagina">
          <option v-for="opcion in opcionesPorPagina" :key="opcion" :value="opcion">{{ opcion }}</option>
        </select>
      </label>

      <div v-if="totalPaginas > 1" class="paginacion-nav">
        <button
          type="button"
          class="paginacion-btn"
          :disabled="paginaActual === 1"
          @click="emit('cambiar-pagina', paginaActual - 1)"
        >
          ‹ Anterior
        </button>

        <span class="paginacion-actual">Página {{ paginaActual }} de {{ totalPaginas }}</span>

        <button
          type="button"
          class="paginacion-btn"
          :disabled="paginaActual === totalPaginas"
          @click="emit('cambiar-pagina', paginaActual + 1)"
        >
          Siguiente ›
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.paginacion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 14px;
  margin-top: 4px;
  border-top: 1px solid #f1f4f7;
}

.paginacion-info {
  font-size: 12px;
  color: #9aa8b8;
  font-weight: 600;
}

.paginacion-controles {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.paginacion-por-pagina {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 700;
  color: #5e6e82;
}

.paginacion-por-pagina select {
  height: 30px;
  border-radius: 8px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  padding: 0 6px;
}

.paginacion-nav {
  display: flex;
  align-items: center;
  gap: 10px;
}

.paginacion-actual {
  font-size: 12px;
  font-weight: 800;
  color: #1d3557;
  white-space: nowrap;
}

.paginacion-btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  color: #457b9d;
  font-family: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.paginacion-btn:hover:not(:disabled) {
  background: #eaf5f5;
  border-color: #a8dadc;
}

.paginacion-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .paginacion {
    flex-direction: column;
    align-items: stretch;
  }

  .paginacion-controles {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .paginacion-nav {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  .paginacion-btn {
    padding: 0 10px;
  }
}
</style>
