<script setup>
import ModalBase from '../ui/ModalBase.vue'

defineProps({
  abierto: {
    type: Boolean,
    required: true,
  },
  titulo: {
    type: String,
    default: 'Confirmar acción',
  },
  mensaje: {
    type: String,
    default: '',
  },
  textoSecundario: {
    type: String,
    default: '',
  },
  textoConfirmar: {
    type: String,
    default: 'Confirmar',
  },
  textoCancelar: {
    type: String,
    default: 'Cancelar',
  },
  // normal | advertencia | peligrosa
  variante: {
    type: String,
    default: 'normal',
  },
})

const emit = defineEmits(['confirmar', 'cancelar'])
</script>

<template>
  <ModalBase
    :abierto="abierto"
    :titulo="titulo"
    ancho="420px"
    @cerrar="emit('cancelar')"
  >
    <div class="confirmacion-body">
      <p class="confirmacion-mensaje">{{ mensaje }}</p>
      <p v-if="textoSecundario" class="confirmacion-secundario">{{ textoSecundario }}</p>
    </div>

    <div class="confirmacion-acciones">
      <button class="btn-cancelar" type="button" @click="emit('cancelar')">
        {{ textoCancelar }}
      </button>

      <button
        class="btn-confirmar"
        :class="variante"
        type="button"
        @click="emit('confirmar')"
      >
        {{ textoConfirmar }}
      </button>
    </div>
  </ModalBase>
</template>

<style scoped>
.confirmacion-body {
  margin-bottom: 22px;
}

.confirmacion-mensaje {
  margin: 0;
  color: #1d3557;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
}

.confirmacion-secundario {
  margin: 10px 0 0;
  color: #9aa8b8;
  font-size: 12.5px;
  font-weight: 500;
  line-height: 1.5;
}

.confirmacion-acciones {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-cancelar {
  height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-cancelar:hover {
  background: #f6f9fa;
}

.btn-confirmar {
  height: 40px;
  padding: 0 18px;
  border-radius: 10px;
  border: none;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  color: #ffffff;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-confirmar.normal {
  background: #1d3557;
}

.btn-confirmar.normal:hover {
  background: #152840;
}

.btn-confirmar.advertencia {
  background: #f4a261;
  color: #1d3557;
}

.btn-confirmar.advertencia:hover {
  background: #e99248;
}

.btn-confirmar.peligrosa {
  background: #e76f51;
}

.btn-confirmar.peligrosa:hover {
  background: #d65f40;
}
</style>
