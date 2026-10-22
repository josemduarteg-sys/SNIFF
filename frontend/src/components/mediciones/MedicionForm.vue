<script setup>
import { computed, reactive, ref, watch } from 'vue'
import SelectorBuscable from '../common/SelectorBuscable.vue'
import { actualizarMedicion, crearMedicion, obtenerSiguientePeriodo } from '../../services/medicionService'
import { formatearNumero } from '../../utils/formato'
import { formatearFechaIso } from '../../utils/ampliaciones'
import { textoObjetivoKpi } from '../../utils/objetivos'
import { MENSAJE_SIN_KPI_DISPONIBLES, kpisDisponiblesParaRegistro } from '../../utils/registroMediciones'
import { formatearTamano, validarArchivosEvidencia } from '../../utils/evidencias'

const props = defineProps({
  indicadores: {
    type: Array,
    required: true,
  },
  medicionEditar: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['guardado', 'cancelar'])

const form = reactive({
  indicador: '',
  valor_resultado: '',
  observacion: '',
  archivos: [],
})

const estado = reactive({
  guardando: false,
  error: '',
  cargandoPeriodo: false,
  periodo: null,
})

const esEdicion = computed(() => !!props.medicionEditar?.id)

// El botón debe reflejar explícitamente cuándo no se puede guardar (no
// alcanza con ocultar los campos): en creación, exige un KPI elegido, el
// periodo ya calculado (no cargando) y disponible=true.
const puedeGuardar = computed(() => {
  if (estado.guardando) return false
  if (esEdicion.value) return true
  if (!form.indicador) return false
  if (estado.cargandoPeriodo) return false
  return estado.periodo?.disponible === true
})

const tituloBoton = computed(() => {
  if (estado.guardando) return esEdicion.value ? 'Actualizando...' : 'Guardando...'
  return esEdicion.value ? 'Actualizar medición' : 'Guardar medición'
})

// Solo los KPI que hoy tienen un periodo disponible para registrar (pedido
// de Hernán: "que le aparezcan solo los que tocan"). Antes se listaban todos
// los autorizados, marcados "(Disponible)" / "(No disponible)". El backend
// vuelve a validar el periodo al guardar.
const opcionesKpi = computed(() => {
  return kpisDisponiblesParaRegistro(props.indicadores).map((indicador) => ({
    id: indicador.id,
    texto: `${indicador.nombre} — ${indicador.plan_anual_nombre || 'Sin plan anual'} — ${textoObjetivoKpi(indicador)}`,
  }))
})

const sinKpiDisponibles = computed(() => !esEdicion.value && !opcionesKpi.value.length)

const indicadorSeleccionado = computed(() => {
  if (!form.indicador) return null

  return props.indicadores.find((indicador) => {
    return Number(indicador.id) === Number(form.indicador)
  }) || null
})

// Contexto de solo lectura a mostrar: en creación viene del KPI elegido, en
// edición viene directamente de la medición (que ya trae los datos de su
// KPI expandidos, sin necesidad de que ese KPI siga en la lista de
// "autorizados" seleccionables).
const contexto = computed(() => {
  if (esEdicion.value) {
    const medicion = props.medicionEditar
    return {
      planEstrategico: medicion.indicador_plan_estrategico_titulo,
      planAnual: medicion.indicador_plan_anual_nombre,
      objetivoEspecifico: medicion.indicador_objetivo_especifico_texto,
      nombreKpi: medicion.indicador_nombre,
      formula: medicion.formula_medicion,
      unidad: medicion.unidad_medida,
      meta: medicion.valor_meta,
      frecuencia: medicion.indicador_frecuencia_nombre,
      periodoNombre: medicion.periodo_nombre,
    }
  }

  const indicador = indicadorSeleccionado.value

  if (!indicador) return null

  return {
    planEstrategico: indicador.plan_estrategico_titulo,
    planAnual: indicador.plan_anual_nombre,
    objetivoEspecifico: textoObjetivoKpi(indicador),
    nombreKpi: indicador.nombre,
    formula: indicador.formula_medicion,
    unidad: indicador.unidad_medida,
    meta: indicador.valor_meta,
    frecuencia: indicador.frecuencia_nombre,
    periodoNombre: estado.periodo?.periodo_nombre,
  }
})

const unidadMedida = computed(() => contexto.value?.unidad || 'unidad')

// D2: los archivos elegidos se SUMAN a las evidencias que la medición ya
// tenga (nunca las reemplazan). En edición solo si la medición admite
// cambios (backend: MedicionSerializer.validate es quien decide).
const puedeEditarEvidencia = computed(() => {
  if (!esEdicion.value) return true
  return props.medicionEditar?.puede_modificarse !== false
})

const ayudaResultado = computed(() => {
  const unidad = unidadMedida.value

  if (unidad === '%') {
    return 'Ingresá el porcentaje real obtenido en el periodo. Ejemplo: 85 para representar 85%.'
  }

  return `Ingresá el valor real obtenido en el periodo usando la unidad configurada: ${unidad}.`
})

watch(
  () => props.medicionEditar,
  (medicion) => {
    estado.error = ''
    form.archivos = []

    if (medicion?.id) {
      form.indicador = medicion.indicador || ''
      form.valor_resultado = medicion.valor_resultado || ''
      form.observacion = medicion.observacion || medicion.observaciones || ''
      estado.periodo = null
      return
    }

    limpiarFormulario()
  },
  { immediate: true }
)

watch(
  () => form.indicador,
  (nuevoIndicador) => {
    estado.error = ''

    if (esEdicion.value) return

    cargarSiguientePeriodo(nuevoIndicador)
  }
)

function limpiarFormulario() {
  form.indicador = ''
  form.valor_resultado = ''
  form.observacion = ''
  form.archivos = []
  estado.periodo = null
}

async function cargarSiguientePeriodo(indicadorId) {
  if (!indicadorId) {
    estado.periodo = null
    return
  }

  estado.cargandoPeriodo = true
  estado.periodo = null

  try {
    estado.periodo = await obtenerSiguientePeriodo(indicadorId)
  } catch (error) {
    estado.periodo = {
      disponible: false,
      motivo:
        error.response?.data?.detail ||
        'No se pudo calcular el siguiente periodo de medición.',
    }
  } finally {
    estado.cargandoPeriodo = false
  }
}

function manejarSeleccionArchivo(evento) {
  const archivos = Array.from(evento.target.files || [])
  const error = validarArchivosEvidencia(archivos)

  if (error) {
    estado.error = error
    evento.target.value = ''
    form.archivos = []
    return
  }

  estado.error = ''
  form.archivos = archivos
}

const inputArchivoRef = ref(null)

function quitarArchivos() {
  form.archivos = []

  if (inputArchivoRef.value) {
    inputArchivoRef.value.value = ''
  }
}

function validarFormulario() {
  if (!esEdicion.value) {
    if (!form.indicador) return 'Seleccioná el KPI.'

    if (estado.cargandoPeriodo) return 'Esperá a que se calcule el periodo a registrar.'

    if (!estado.periodo?.disponible) {
      return estado.periodo?.motivo || 'Este KPI no tiene un periodo disponible para registrar.'
    }
  }

  if (form.valor_resultado === '' || form.valor_resultado === null) {
    return 'Ingresá el valor obtenido en el periodo.'
  }

  const resultado = Number(form.valor_resultado)

  if (Number.isNaN(resultado)) return 'El valor obtenido debe ser un número válido.'
  if (resultado < 0) return 'El valor obtenido no puede ser negativo.'

  if (unidadMedida.value === '%' && resultado > 100) {
    return 'Cuando la unidad de medida es porcentaje, el resultado no puede ser mayor a 100.'
  }

  return ''
}

async function guardar() {
  estado.error = ''

  const errorValidacion = validarFormulario()

  if (errorValidacion) {
    estado.error = errorValidacion
    return
  }

  estado.guardando = true

  const payload = {
    indicador: Number(form.indicador),
    valor_resultado: form.valor_resultado,
    observacion: form.observacion,
    archivos_evidencia: form.archivos,
  }

  try {
    if (esEdicion.value) {
      await actualizarMedicion(props.medicionEditar.id, payload)
    } else {
      await crearMedicion(payload)
    }

    emit('guardado')
    limpiarFormulario()
  } catch (error) {
    const data = error.response?.data

    if (data?.non_field_errors) {
      estado.error = data.non_field_errors.join(' ')
    } else if (data?.detail) {
      estado.error = data.detail
    } else if (typeof data === 'object' && data !== null) {
      const primerCampo = Object.keys(data)[0]
      const mensaje = data[primerCampo]
      estado.error = Array.isArray(mensaje) ? mensaje.join(' ') : String(mensaje)
    } else {
      estado.error = esEdicion.value
        ? 'No se pudo actualizar la medición.'
        : 'No se pudo guardar la medición.'
    }
  } finally {
    estado.guardando = false
  }
}
</script>

<template>
  <form class="medicion-form" @submit.prevent="guardar">
    <div v-if="sinKpiDisponibles" class="form-group full">
      <p class="field-hint error sin-kpi">{{ MENSAJE_SIN_KPI_DISPONIBLES }}</p>
    </div>

    <div v-else-if="!esEdicion" class="form-group full">
      <label>KPI</label>
      <SelectorBuscable
        v-model="form.indicador"
        :opciones="opcionesKpi"
        placeholder="Seleccionar KPI"
        placeholder-busqueda="Escribí el nombre del KPI..."
        mensaje-vacio="Ningún KPI disponible coincide con ese texto."
      />
    </div>

    <section v-if="contexto" class="kpi-context full">
      <div class="context-item">
        <span>Plan estratégico</span>
        <strong>{{ contexto.planEstrategico || 'No definido' }}</strong>
      </div>

      <div class="context-item">
        <span>Plan anual</span>
        <strong>{{ contexto.planAnual || 'No definido' }}</strong>
      </div>

      <div class="context-item">
        <span>Objetivo</span>
        <strong>{{ contexto.objetivoEspecifico || 'No definido' }}</strong>
      </div>

      <div class="context-item">
        <span>Frecuencia</span>
        <strong>{{ contexto.frecuencia || 'No definida' }}</strong>
      </div>

      <div class="context-item full">
        <span>Fórmula de medición</span>
        <strong>{{ contexto.formula || 'No definida' }}</strong>
      </div>

      <div class="context-item">
        <span>Meta configurada</span>
        <strong>{{ formatearNumero(contexto.meta, { unidad: contexto.unidad }) }}</strong>
      </div>

      <div class="context-item">
        <span>Periodo a registrar</span>
        <strong>{{ contexto.periodoNombre || 'No definido' }}</strong>
      </div>
    </section>

    <div v-if="!esEdicion && form.indicador" class="form-group full">
      <p v-if="estado.cargandoPeriodo" class="field-hint">
        Calculando el periodo que corresponde registrar...
      </p>

      <p
        v-else-if="estado.periodo"
        class="field-hint"
        :class="{ error: !estado.periodo.disponible, ok: estado.periodo.disponible }"
      >
        <template v-if="estado.periodo.disponible">
          Podés registrar la medición de <strong>{{ estado.periodo.periodo_nombre }}</strong><template v-if="estado.periodo.periodo_parcial">
            (primer periodo, medido desde el inicio del seguimiento del KPI, el
            {{ formatearFechaIso(estado.periodo.inicio_seguimiento) }})</template>.
          Fecha de cierre: {{ formatearFechaIso(estado.periodo.fecha_cierre) }}.
          <template v-if="estado.periodo.fecha_limite_extraordinaria">
            <strong>Plazo ampliado hasta el {{ formatearFechaIso(estado.periodo.fecha_limite_extraordinaria) }}</strong>
            (días adicionales autorizados; el plazo ordinario terminó el
            {{ formatearFechaIso(estado.periodo.fecha_limite_ordinaria) }}).
          </template>
          <template v-else>
            Fecha límite de registro: {{ formatearFechaIso(estado.periodo.fecha_limite_registro) }}.
          </template>
        </template>
        <template v-else>
          {{ estado.periodo.motivo }}
        </template>
      </p>
    </div>

    <template v-if="esEdicion || estado.periodo?.disponible">
      <div class="form-group">
        <label>Valor obtenido en el periodo</label>
        <div class="input-with-unit">
          <input
            v-model="form.valor_resultado"
            type="number"
            min="0"
            :max="unidadMedida === '%' ? 100 : undefined"
            step="0.01"
            placeholder="Ejemplo: 85"
          />
          <span>{{ unidadMedida }}</span>
        </div>
        <small>{{ ayudaResultado }}</small>
      </div>

      <div class="form-group full">
        <label>Observación</label>
        <textarea
          v-model="form.observacion"
          rows="3"
          placeholder="Explicá brevemente el resultado obtenido, causas o contexto del periodo evaluado."
        ></textarea>
      </div>

      <div class="form-group full">
        <label>Evidencia / respaldo (opcional)</label>

        <p v-if="esEdicion && medicionEditar?.cantidad_evidencias" class="field-hint">
          Esta medición ya tiene {{ medicionEditar.cantidad_evidencias }}
          {{ medicionEditar.cantidad_evidencias === 1 ? 'evidencia adjunta' : 'evidencias adjuntas' }}.
          Se conservan todas: los archivos que elijas se suman a las anteriores.
        </p>

        <template v-if="puedeEditarEvidencia">
          <input
            ref="inputArchivoRef"
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,application/pdf,image/jpeg"
            @change="manejarSeleccionArchivo"
          />

          <div v-if="form.archivos.length" class="archivo-seleccionado">
            <ul class="field-hint ok lista-archivos">
              <li v-for="archivo in form.archivos" :key="archivo.name + archivo.size">
                {{ archivo.name }} ({{ formatearTamano(archivo.size) }})
              </li>
            </ul>
            <button type="button" class="btn-quitar-archivo" @click="quitarArchivos">
              Quitar
            </button>
          </div>

          <small>Solo PDF, JPG o JPEG. Hasta 10 archivos por vez, 10 MB cada uno.</small>
        </template>
      </div>
    </template>

    <div v-if="estado.error" class="form-error full">
      {{ estado.error }}
    </div>

    <div class="form-actions full">
      <button
        class="btn-secondary"
        type="button"
        :disabled="estado.guardando"
        @click="emit('cancelar')"
      >
        Cancelar
      </button>

      <button
        class="btn-primary"
        type="submit"
        :disabled="!puedeGuardar"
      >
        {{ tituloBoton }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.medicion-form,
.medicion-form * {
  box-sizing: border-box;
}

.medicion-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.form-group.full,
.full {
  grid-column: 1 / -1;
}

label {
  color: #1d3557;
  font-size: 12px;
  font-weight: 800;
}

input,
select,
textarea {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  padding: 0 12px;
  font-family: inherit;
  color: #1d3557;
  outline: none;
  background: #ffffff;
}

input[type='file'] {
  padding: 9px 12px;
  font-size: 12.5px;
  font-weight: 650;
  height: auto;
}

input,
select {
  height: 40px;
}

textarea {
  min-height: 96px;
  padding-top: 11px;
  resize: vertical;
}

input:focus,
select:focus,
textarea:focus {
  border-color: #a8dadc;
}

input:disabled,
select:disabled,
textarea:disabled {
  background: #f4f7f9;
  color: #9aa8b8;
  cursor: not-allowed;
}

small {
  color: #9aa8b8;
  font-size: 11.5px;
  font-weight: 600;
}

.field-hint {
  margin: 4px 0 0;
  color: #7f8fa3;
  font-size: 11.5px;
  font-weight: 650;
  line-height: 1.35;
}

.field-hint.error {
  color: #e76f51;
}

.field-hint.ok {
  color: #2a9d8f;
}

.archivo-seleccionado {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.archivo-seleccionado .field-hint {
  margin: 0;
}

.lista-archivos {
  padding-left: 18px;
}

.btn-quitar-archivo {
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #e76f51;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 800;
  border-radius: 8px;
  padding: 4px 10px;
  cursor: pointer;
}

.btn-quitar-archivo:hover {
  background: rgba(231, 111, 81, 0.1);
  border-color: #e76f51;
}

.kpi-context {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  background: #f6f9fa;
  border: 1px solid #e4eaef;
}

.context-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.context-item span {
  color: #9aa8b8;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-item strong {
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
}

.input-with-unit {
  display: flex;
  align-items: center;
  border: 1.5px solid #e4eaef;
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
}

.input-with-unit:focus-within {
  border-color: #a8dadc;
}

.input-with-unit input {
  border: none;
  border-radius: 0;
}

.input-with-unit span {
  height: 40px;
  min-width: 48px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 12px;
  font-weight: 800;
}

.form-error {
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
  font-size: 13px;
  font-weight: 700;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
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
}

.btn-secondary {
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #5e6e82;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

@media (max-width: 700px) {
  .medicion-form,
  .kpi-context {
    grid-template-columns: 1fr;
  }
}
</style>
