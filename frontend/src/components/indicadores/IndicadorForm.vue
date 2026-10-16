<script setup>
import { computed, reactive, watch } from 'vue'
import SelectorBuscable from '../common/SelectorBuscable.vue'

const props = defineProps({
  indicador: {
    type: Object,
    default: null,
  },
  planesAnuales: {
    type: Array,
    default: () => [],
  },
  objetivosGenerales: {
    type: Array,
    default: () => [],
  },
  objetivosEspecificos: {
    type: Array,
    default: () => [],
  },
  frecuencias: {
    type: Array,
    default: () => [],
  },
  // Bloque 3, segunda parte (ponderaciones): listado completo de KPI ya
  // cargado por la vista — se usa solo para mostrar en vivo, a título
  // informativo, cuánto ya está asignado en el mismo ámbito (plan_anual,
  // objetivo_general). El backend sigue siendo la única fuente de verdad
  // que valida de verdad el límite de 100% (ver IndicadorKPISerializer.validate).
  indicadores: {
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
  plan_anual: '',
  objetivo_general: '',
  objetivo_especifico: '',
  frecuencia: '',
  nombre: '',
  descripcion: '',
  formula_medicion: '',
  unidad_medida: '',
  unidad_personalizada: '',
  valor_meta: '',
  ponderacion: '',
  error: '',
})

const esEdicion = computed(() => Boolean(props.indicador?.id))

const esPorcentaje = computed(() => estado.unidad_medida === '%')

// Mientras el KPI ya esté autorizado, sus datos principales quedan
// bloqueados (ver IndicadorKPISerializer.validate). El listado ya oculta
// la acción Editar en ese caso; este disabled es un resguardo defensivo.
const puedeEditar = computed(() => {
  if (!props.indicador) {
    return true
  }

  return props.indicador.puede_modificarse === true || props.indicador.estado === 'borrador'
})

const tituloBoton = computed(() => {
  return esEdicion.value ? 'Actualizar KPI' : 'Crear KPI'
})

const opcionesPlanesAnuales = computed(() => {
  return props.planesAnuales.map((plan) => ({
    id: plan.id,
    texto: `${plan.nombre || `Plan ${plan.anio}`} — ${plan.plan_estrategico_titulo || 'Sin plan estratégico'}`,
  }))
})

const planAnualSeleccionado = computed(() => {
  return (
    props.planesAnuales.find((plan) => Number(plan.id) === Number(estado.plan_anual)) || null
  )
})

// Solo objetivos generales del mismo Plan estratégico que el Plan anual
// elegido (ver validación equivalente, y autoritativa, en backend).
const opcionesObjetivosGenerales = computed(() => {
  if (!planAnualSeleccionado.value) {
    return []
  }

  return props.objetivosGenerales
    .filter(
      (objetivo) =>
        Number(objetivo.plan_estrategico) === Number(planAnualSeleccionado.value.plan_estrategico)
    )
    .map((objetivo) => ({ id: objetivo.id, texto: objetivo.texto_objetivo }))
})

// Bloque 3, segunda parte (ponderaciones): suma informativa de lo ya
// asignado en el mismo ámbito (plan_anual, objetivo_general), EXCLUYENDO
// este mismo KPI en edición. Solo a título de vista previa en vivo — el
// backend vuelve a validar el límite de 100% de forma autoritativa.
const ponderacionAsignadaAmbito = computed(() => {
  if (!estado.plan_anual || !estado.objetivo_general) {
    return 0
  }

  return props.indicadores
    .filter(
      (kpi) =>
        Number(kpi.plan_anual) === Number(estado.plan_anual)
        && Number(kpi.objetivo_general) === Number(estado.objetivo_general)
        && !(esEdicion.value && Number(kpi.id) === Number(props.indicador.id))
    )
    .reduce((total, kpi) => total + (Number(kpi.ponderacion) || 0), 0)
})

const ponderacionPendienteAmbito = computed(() => {
  return Math.max(0, 100 - ponderacionAsignadaAmbito.value)
})

// Objetivos específicos reales (el backend ya excluye los "KPI directo"
// generados internamente) que pertenecen a la combinación elegida de
// Plan anual + Objetivo general, más una opción explícita para no elegir
// ninguno. Es opcional: si se deja en "Sin objetivo específico", el
// backend crea/reutiliza el objetivo específico implícito de esa misma
// combinación (Bloque 3) — esta opción también permite volver a un KPI
// directo después de haber elegido uno real.
const OPCION_SIN_OBJETIVO_ESPECIFICO = {
  id: '',
  texto: 'Sin objetivo específico (KPI directo del objetivo general)',
}

const opcionesObjetivosEspecificos = computed(() => {
  if (!estado.plan_anual || !estado.objetivo_general) {
    return []
  }

  const reales = props.objetivosEspecificos
    .filter(
      (objetivo) =>
        Number(objetivo.plan_anual) === Number(estado.plan_anual)
        && Number(objetivo.objetivo_general) === Number(estado.objetivo_general)
    )
    .map((objetivo) => ({ id: objetivo.id, texto: objetivo.texto_objetivo }))

  return [OPCION_SIN_OBJETIVO_ESPECIFICO, ...reales]
})

watch(
  () => props.indicador,
  () => {
    cargarFormulario()
  },
  { immediate: true }
)

watch(
  () => estado.plan_anual,
  () => {
    const siguePerteneciendo = opcionesObjetivosGenerales.value.some(
      (opcion) => Number(opcion.id) === Number(estado.objetivo_general)
    )

    if (!siguePerteneciendo) {
      estado.objetivo_general = ''
    }
  }
)

watch(
  () => estado.objetivo_general,
  () => {
    const siguePerteneciendo = opcionesObjetivosEspecificos.value.some(
      (opcion) => Number(opcion.id) === Number(estado.objetivo_especifico)
    )

    if (!siguePerteneciendo) {
      estado.objetivo_especifico = ''
    }
  }
)

function cargarFormulario() {
  // Bloque 3 (KPI directo): plan_anual/objetivo_general ya llegan
  // resueltos directamente desde el indicador (derivados en backend de su
  // objetivo_especifico, real o implícito) — no hace falta buscarlos en
  // objetivosEspecificos, que ya ni siquiera incluye los implícitos.
  estado.plan_anual = props.indicador?.plan_anual || ''
  estado.objetivo_general = props.indicador?.objetivo_general || ''
  // Un KPI directo (es_directo) no tiene un objetivo específico real que
  // mostrar seleccionado: el campo queda vacío (opcional) en el formulario.
  estado.objetivo_especifico =
    props.indicador && !props.indicador.es_directo ? props.indicador.objetivo_especifico || '' : ''
  estado.frecuencia = props.indicador?.frecuencia || ''
  estado.nombre = props.indicador?.nombre || ''
  estado.descripcion = props.indicador?.descripcion || ''
  estado.formula_medicion = props.indicador?.formula_medicion || ''
  estado.valor_meta = props.indicador?.valor_meta || ''
  estado.ponderacion = props.indicador?.ponderacion ?? ''
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

function ponderacionValida() {
  if (estado.ponderacion === '' || estado.ponderacion === null) {
    return true
  }

  return Number(estado.ponderacion) >= 0 && Number(estado.ponderacion) <= 100
}

function validarFormulario() {
  estado.error = ''

  // Bloque 3, segunda parte: un KPI ya autorizado sigue bloqueado para
  // sus campos principales, pero la ponderación es la única excepción
  // (regla 7: es independiente de meta/resultado/promedio acumulado) —
  // ver guardar(), que para este caso reenvía solo ese campo.
  if (!puedeEditar.value) {
    if (!ponderacionValida()) {
      estado.error = 'La ponderación debe estar entre 0 y 100.'
      return false
    }

    return true
  }

  if (!estado.plan_anual) {
    estado.error = 'Seleccioná un plan anual.'
    return false
  }

  if (!estado.objetivo_general) {
    estado.error = 'Seleccioná un objetivo general.'
    return false
  }

  // El objetivo específico es opcional (Bloque 3): sin él, el KPI queda
  // como "directo" del objetivo general elegido.

  if (!estado.nombre.trim()) {
    estado.error = 'Ingresá el nombre del KPI.'
    return false
  }

  if (!estado.formula_medicion.trim()) {
    estado.error = 'Ingresá la fórmula de medición.'
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

  if (estado.valor_meta === '' || estado.valor_meta === null || Number(estado.valor_meta) < 0) {
    estado.error = 'Ingresá la meta del KPI.'
    return false
  }

  if (esPorcentaje.value && (Number(estado.valor_meta) < 0 || Number(estado.valor_meta) > 100)) {
    estado.error = 'Cuando la unidad de medida es porcentaje, la meta debe estar entre 0 y 100.'
    return false
  }

  if (!estado.frecuencia) {
    estado.error = 'Seleccioná la frecuencia del KPI.'
    return false
  }

  if (!ponderacionValida()) {
    estado.error = 'La ponderación debe estar entre 0 y 100.'
    return false
  }

  return true
}

function guardar() {
  if (!validarFormulario()) {
    return
  }

  if (!puedeEditar.value) {
    // KPI ya autorizado: solo se reenvía la ponderación (ver
    // actualizarPonderacionIndicador en indicadorService.js — reenviar el
    // resto de campos activaría el bloqueo de "KPI ya autorizado" aunque
    // su valor no haya cambiado).
    emit('guardar', { soloPonderacion: true, ponderacion: estado.ponderacion })
    return
  }

  const unidadFinal =
    estado.unidad_medida === 'otro'
      ? estado.unidad_personalizada.trim()
      : estado.unidad_medida

  emit('guardar', {
    plan_anual: estado.plan_anual,
    objetivo_general: estado.objetivo_general,
    objetivo_especifico: estado.objetivo_especifico || null,
    frecuencia: estado.frecuencia,
    nombre: estado.nombre.trim(),
    descripcion: estado.descripcion.trim(),
    formula_medicion: estado.formula_medicion.trim(),
    unidad_medida: unidadFinal,
    valor_meta: estado.valor_meta,
    ponderacion: estado.ponderacion,
  })
}

function cancelar() {
  emit('cancelar')
}
</script>

<template>
  <form class="indicador-form" @submit.prevent="guardar">
    <div v-if="!puedeEditar" class="alert warning">
      Este KPI ya está autorizado. Sus datos principales no pueden modificarse.
    </div>

    <div v-if="estado.error" class="alert error">
      {{ estado.error }}
    </div>

    <div class="form-grid">
      <label class="field field-full">
        <span>Plan anual</span>

        <SelectorBuscable
          v-model="estado.plan_anual"
          :opciones="opcionesPlanesAnuales"
          placeholder="Seleccionar plan anual"
          placeholder-busqueda="Escribí el plan o el año..."
          mensaje-vacio="No hay planes anuales En uso disponibles."
          :disabled="!puedeEditar"
        />
      </label>

      <label class="field field-full">
        <span>Objetivo general</span>

        <SelectorBuscable
          v-model="estado.objetivo_general"
          :opciones="opcionesObjetivosGenerales"
          placeholder="Seleccionar objetivo general"
          placeholder-busqueda="Escribí el texto del objetivo..."
          mensaje-vacio="Seleccioná primero un plan anual."
          :disabled="!puedeEditar || !estado.plan_anual"
        />
      </label>

      <label class="field field-full">
        <span>Objetivo específico (opcional)</span>

        <SelectorBuscable
          v-model="estado.objetivo_especifico"
          :opciones="opcionesObjetivosEspecificos"
          placeholder="Sin objetivo específico (KPI directo del objetivo general)"
          placeholder-busqueda="Escribí el texto del objetivo..."
          mensaje-vacio="No se encontraron objetivos específicos con ese texto."
          :disabled="!puedeEditar || !estado.objetivo_general"
        />
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

      <label class="field field-full">
        <span>Fórmula de medición</span>

        <textarea
          v-model="estado.formula_medicion"
          rows="3"
          placeholder="Ejemplo: (Ventas actuales / Meta de ventas) × 100"
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
        <span>Frecuencia</span>

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
        <span>Ponderación (opcional)</span>

        <input
          v-model="estado.ponderacion"
          type="number"
          min="0"
          max="100"
          step="0.01"
          placeholder="Ejemplo: 30.00"
        />
      </label>
    </div>

    <!-- La ponderación es la única excepción al bloqueo de "KPI ya
         autorizado": por eso su input, arriba, nunca queda :disabled. -->
    <div v-if="estado.plan_anual && estado.objetivo_general" class="help-box ponderacion-box">
      Peso del KPI dentro del 100% de su año y objetivo general (independiente
      de la meta, el resultado y el promedio acumulado).
      Ya asignado en este ámbito: <strong>{{ ponderacionAsignadaAmbito.toFixed(2) }}%</strong> ·
      Pendiente: <strong>{{ ponderacionPendienteAmbito.toFixed(2) }}%</strong>
    </div>

    <div class="help-box">
      El KPI se crea como borrador y no inicia su seguimiento hasta ser autorizado.
      Su vigencia es la del año del plan anual elegido.
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
  min-height: 78px;
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
