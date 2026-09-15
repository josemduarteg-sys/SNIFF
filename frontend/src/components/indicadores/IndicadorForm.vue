<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  indicador: {
    type: Object,
    default: null,
  },
  objetivos: {
    type: Array,
    default: () => [],
  },
  frecuencias: {
    type: Array,
    default: () => [],
  },
  tiposCalculo: {
    type: Array,
    default: () => [],
  },
  fuentesDato: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['guardar', 'cancelar'])

const UNIDADES_MEDIDA = [
  { valor: '%', etiqueta: '%' },
  { valor: 'Q', etiqueta: 'Q' },
  { valor: 'unidades', etiqueta: 'Unidades' },
  { valor: 'días', etiqueta: 'Días' },
  { valor: 'horas', etiqueta: 'Horas' },
  { valor: 'cantidad', etiqueta: 'Cantidad' },
  { valor: 'índice', etiqueta: 'Índice' },
  { valor: 'otro', etiqueta: 'Otro' },
]

const estado = reactive({
  objetivo: '',
  frecuencia: '',
  tipo_calculo: '',
  fuente_dato: '',
  nombre: '',
  descripcion: '',
  unidad_medida: '',
  unidad_personalizada: '',
  valor_meta: '',
  fecha_inicio: '',
  fecha_fin: '',
  error: '',
})

const esEdicion = computed(() => Boolean(props.indicador?.id))

const esPorcentaje = computed(() => estado.unidad_medida === '%')

const notaFuente = computed(() => {
  const fuente = props.fuentesDato.find(
    (item) => Number(item.id) === Number(estado.fuente_dato)
  )

  if (!fuente) {
    return 'Selecciona la fuente de datos que respaldará el seguimiento del KPI.'
  }

  const nombre = (fuente.nombre || '').toLowerCase()

  if (nombre.includes('manual')) {
    return 'Las mediciones de este KPI serán registradas manualmente desde el módulo de mediciones.'
  }

  if (nombre.includes('csv')) {
    return 'Esta fuente deja el KPI preparado para carga por archivo CSV. La importación se configurará en una etapa posterior; por ahora el seguimiento puede registrarse manualmente.'
  }

  if (nombre.includes('warehouse') || nombre.includes('data')) {
    return 'Esta fuente identifica un origen de datos institucional. La conexión automática con Data Warehouse se configurará en una etapa posterior.'
  }

  return 'Selecciona la fuente de datos que respaldará el seguimiento del KPI.'
})

const puedeEditar = computed(() => {
  if (!props.indicador) {
    return true
  }

  return props.indicador.puede_modificarse === true || props.indicador.estado === 'borrador'
})

const tituloBoton = computed(() => {
  return esEdicion.value ? 'Actualizar KPI' : 'Crear KPI'
})

watch(
  () => props.indicador,
  () => {
    cargarFormulario()
  },
  { immediate: true }
)

function cargarFormulario() {
  estado.objetivo = props.indicador?.objetivo || ''
  estado.frecuencia = props.indicador?.frecuencia || ''
  estado.tipo_calculo = props.indicador?.tipo_calculo || ''
  estado.fuente_dato = props.indicador?.fuente_dato || ''
  estado.nombre = props.indicador?.nombre || ''
  estado.descripcion = props.indicador?.descripcion || ''
  estado.valor_meta = props.indicador?.valor_meta || ''
  estado.fecha_inicio = props.indicador?.fecha_inicio || ''
  estado.fecha_fin = props.indicador?.fecha_fin || ''
  estado.error = ''

  const unidadExistente = props.indicador?.unidad_medida || ''
  const esOpcionConocida = UNIDADES_MEDIDA.some((unidad) => unidad.valor === unidadExistente)

  if (unidadExistente && !esOpcionConocida) {
    estado.unidad_medida = 'otro'
    estado.unidad_personalizada = unidadExistente
  } else {
    estado.unidad_medida = unidadExistente
    estado.unidad_personalizada = ''
  }
}

function validarFormulario() {
  estado.error = ''

  if (!puedeEditar.value) {
    estado.error = 'Este KPI ya está activo y no permite modificar sus datos principales.'
    return false
  }

  if (!estado.objetivo) {
    estado.error = 'Seleccioná el objetivo asociado al KPI.'
    return false
  }

  if (!estado.nombre.trim()) {
    estado.error = 'Ingresá el nombre del KPI.'
    return false
  }

  if (!estado.unidad_medida) {
    estado.error = 'Seleccioná la unidad de medida del KPI.'
    return false
  }

  if (estado.unidad_medida === 'otro' && !estado.unidad_personalizada.trim()) {
    estado.error = 'Ingresá la unidad de medida personalizada.'
    return false
  }

  if (!estado.valor_meta || Number(estado.valor_meta) <= 0) {
    estado.error = 'Ingresá una meta mayor a cero.'
    return false
  }

  if (esPorcentaje.value && (Number(estado.valor_meta) < 0 || Number(estado.valor_meta) > 100)) {
    estado.error = 'Cuando la unidad de medida es porcentaje, la meta debe estar entre 0 y 100.'
    return false
  }

  if (!estado.fecha_inicio) {
    estado.error = 'Seleccioná la fecha de inicio de vigencia.'
    return false
  }

  if (!estado.fecha_fin) {
    estado.error = 'Seleccioná la fecha de fin de vigencia.'
    return false
  }

  if (estado.fecha_fin < estado.fecha_inicio) {
    estado.error = 'La fecha fin no puede ser menor que la fecha inicio.'
    return false
  }

  if (!estado.frecuencia) {
    estado.error = 'Seleccioná la frecuencia o seguimiento del KPI.'
    return false
  }

  if (!estado.tipo_calculo) {
    estado.error = 'Seleccioná el tipo de cálculo.'
    return false
  }

  if (!estado.fuente_dato) {
    estado.error = 'Seleccioná la fuente de dato.'
    return false
  }

  return true
}

function guardar() {
  if (!validarFormulario()) {
    return
  }

  const unidadFinal =
    estado.unidad_medida === 'otro'
      ? estado.unidad_personalizada.trim()
      : estado.unidad_medida

  emit('guardar', {
    objetivo: estado.objetivo,
    frecuencia: estado.frecuencia,
    tipo_calculo: estado.tipo_calculo,
    fuente_dato: estado.fuente_dato,
    nombre: estado.nombre.trim(),
    descripcion: estado.descripcion.trim(),
    unidad_medida: unidadFinal,
    valor_meta: estado.valor_meta,
    fecha_inicio: estado.fecha_inicio,
    fecha_fin: estado.fecha_fin,
  })
}

function cancelar() {
  emit('cancelar')
}
</script>

<template>
  <form class="indicador-form" @submit.prevent="guardar">
    <div v-if="!puedeEditar" class="alert warning">
      Este KPI ya está activo. Sus datos principales no pueden modificarse.
    </div>

    <div v-if="estado.error" class="alert error">
      {{ estado.error }}
    </div>

    <div class="form-grid">
      <label class="field field-full">
        <span>Objetivo asociado</span>

        <select v-model="estado.objetivo" :disabled="!puedeEditar">
          <option value="">Seleccionar objetivo</option>

          <option
            v-for="objetivo in objetivos"
            :key="objetivo.id"
            :value="objetivo.id"
          >
            {{ objetivo.nombre }}
          </option>
        </select>
      </label>

      <label class="field field-full">
        <span>Nombre del KPI</span>

        <input
          v-model="estado.nombre"
          type="text"
          placeholder="Ejemplo: Porcentaje de recuperación de cartera"
          :disabled="!puedeEditar"
        />
      </label>

      <label class="field field-full">
        <span>Descripción</span>

        <textarea
          v-model="estado.descripcion"
          rows="3"
          placeholder="Describe qué mide este indicador y para qué se utilizará."
          :disabled="!puedeEditar"
        ></textarea>
      </label>

      <label class="field">
        <span>Unidad de medida</span>

        <select v-model="estado.unidad_medida" :disabled="!puedeEditar">
          <option value="">Seleccionar unidad</option>

          <option
            v-for="unidad in UNIDADES_MEDIDA"
            :key="unidad.valor"
            :value="unidad.valor"
          >
            {{ unidad.etiqueta }}
          </option>
        </select>
      </label>

      <label v-if="estado.unidad_medida === 'otro'" class="field">
        <span>Unidad personalizada</span>

        <input
          v-model="estado.unidad_personalizada"
          type="text"
          placeholder="Ejemplo: casos, puntos, transacciones"
          :disabled="!puedeEditar"
        />
      </label>

      <label class="field">
        <span>Meta del KPI</span>

        <input
          v-model="estado.valor_meta"
          type="number"
          min="0"
          :max="esPorcentaje ? 100 : undefined"
          step="0.01"
          placeholder="Ejemplo: 85.00"
          :disabled="!puedeEditar"
        />
      </label>

      <label class="field">
        <span>Fecha inicio</span>

        <input
          v-model="estado.fecha_inicio"
          type="date"
          :disabled="!puedeEditar"
        />
      </label>

      <label class="field">
        <span>Fecha fin</span>

        <input
          v-model="estado.fecha_fin"
          type="date"
          :disabled="!puedeEditar"
        />
      </label>

      <label class="field">
        <span>Frecuencia / seguimiento</span>

        <select v-model="estado.frecuencia" :disabled="!puedeEditar">
          <option value="">Seleccionar frecuencia</option>

          <option
            v-for="frecuencia in frecuencias"
            :key="frecuencia.id"
            :value="frecuencia.id"
          >
            {{ frecuencia.nombre }}
          </option>
        </select>
      </label>

      <label class="field">
        <span>Tipo de cálculo</span>

        <select v-model="estado.tipo_calculo" :disabled="!puedeEditar">
          <option value="">Seleccionar tipo</option>

          <option
            v-for="tipo in tiposCalculo"
            :key="tipo.id"
            :value="tipo.id"
          >
            {{ tipo.nombre }}
          </option>
        </select>
      </label>

      <label class="field field-full">
        <span>Fuente de dato</span>

        <select v-model="estado.fuente_dato" :disabled="!puedeEditar">
          <option value="">Seleccionar fuente</option>

          <option
            v-for="fuente in fuentesDato"
            :key="fuente.id"
            :value="fuente.id"
          >
            {{ fuente.nombre }}
          </option>
        </select>

        <p class="field-note">{{ notaFuente }}</p>
      </label>
    </div>

    <div class="help-box">
      El KPI se guardará como borrador y quedará pendiente de autorización antes de
      iniciar su seguimiento.
    </div>

    <div class="form-actions">
      <button class="btn-secondary" type="button" @click="cancelar">
        Cancelar
      </button>

      <button
        class="btn-primary"
        type="submit"
        :disabled="!puedeEditar"
      >
        {{ tituloBoton }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.indicador-form,
.indicador-form * {
  box-sizing: border-box;
}

.indicador-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.alert {
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 750;
}

.alert.error {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

.alert.warning {
  background: rgba(244, 162, 97, 0.16);
  color: #b9701e;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.field-full {
  grid-column: 1 / -1;
}

.field span {
  font-size: 12px;
  font-weight: 800;
  color: #1d3557;
}

.field-note {
  margin: 2px 2px 0;
  font-size: 11.5px;
  font-weight: 650;
  color: #457b9d;
  line-height: 1.4;
}

.field input,
.field select,
.field textarea {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  border: 1.5px solid #e4eaef;
  border-radius: 11px;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 13px;
  font-weight: 650;
  outline: none;
  padding: 11px 12px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.field textarea {
  resize: vertical;
  min-height: 86px;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  border-color: #a8dadc;
  box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.25);
}

.field input:disabled,
.field select:disabled,
.field textarea:disabled {
  background: #f4f7f9;
  color: #9aa8b8;
  cursor: not-allowed;
}

.help-box {
  border-radius: 12px;
  background: #eaf5f5;
  color: #457b9d;
  padding: 13px 14px;
  font-size: 12.5px;
  line-height: 1.45;
  font-weight: 650;
}

.help-box strong {
  color: #1d3557;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 4px;
}

.btn-primary,
.btn-secondary {
  height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.btn-primary {
  border: none;
  background: #1d3557;
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(29, 53, 87, 0.14);
}

.btn-primary:hover:not(:disabled) {
  background: #152840;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
}

.btn-secondary:hover {
  background: #f4f7f9;
}

@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
