<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import SelectorBuscable from '../common/SelectorBuscable.vue'
import {
  asignarResponsableKpi,
  desactivarResponsableKpi,
  obtenerCandidatosResponsable,
  obtenerResponsablesKpi,
} from '../../services/responsableKpiService'

// Etapa 4 (auditoría M6): responsables (Ejecutores operativos) del KPI. Solo
// el Administrador de planificación asigna o desactiva; el resto consulta.
// Los responsables reciben los avisos individuales de periodos pendientes y
// sin registro. No cambia quién puede registrar mediciones.

const props = defineProps({
  indicador: {
    type: Object,
    required: true,
  },
  puedeGestionar: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['actualizados'])

const responsables = ref([])
const candidatos = ref([])
const usuarioSeleccionado = ref('')
const cargando = ref(false)
const guardando = ref(false)
const error = ref('')

const activos = computed(() => responsables.value.filter((r) => r.estado))

// Un KPI anulado o de un plan Cerrado no admite asignaciones nuevas (el
// backend también lo rechaza); sí se puede desactivar una existente.
const admiteAsignaciones = computed(() => {
  return (
    props.indicador.estado !== 'anulado' &&
    props.indicador.plan_anual_estado !== 'cerrado' &&
    props.indicador.plan_estrategico_estado !== 'cerrado'
  )
})

const opcionesCandidatos = computed(() => {
  const asignados = new Set(activos.value.map((r) => Number(r.usuario)))

  return candidatos.value
    .filter((candidato) => !asignados.has(Number(candidato.id)))
    .map((candidato) => ({ id: candidato.id, texto: `${candidato.nombre} (${candidato.username})` }))
})

function mensajeError(e, porDefecto) {
  const data = e.response?.data

  if (data?.detail) return data.detail

  if (data && typeof data === 'object') {
    const primero = Object.values(data)[0]
    return Array.isArray(primero) ? primero.join(' ') : String(primero)
  }

  return porDefecto
}

async function cargar() {
  cargando.value = true
  error.value = ''

  try {
    const [lista, opciones] = await Promise.all([
      obtenerResponsablesKpi(props.indicador.id),
      props.puedeGestionar ? obtenerCandidatosResponsable() : Promise.resolve([]),
    ])

    responsables.value = lista
    candidatos.value = opciones
  } catch (e) {
    error.value = mensajeError(e, 'No se pudieron cargar los responsables.')
  } finally {
    cargando.value = false
  }
}

async function asignar() {
  if (!usuarioSeleccionado.value) return

  guardando.value = true
  error.value = ''

  try {
    await asignarResponsableKpi(props.indicador.id, usuarioSeleccionado.value)
    usuarioSeleccionado.value = ''
    await cargar()
    emit('actualizados', activos.value.length)
  } catch (e) {
    error.value = mensajeError(e, 'No se pudo asignar el responsable.')
  } finally {
    guardando.value = false
  }
}

async function desactivar(responsable) {
  guardando.value = true
  error.value = ''

  try {
    await desactivarResponsableKpi(responsable.id)
    await cargar()
    emit('actualizados', activos.value.length)
  } catch (e) {
    error.value = mensajeError(e, 'No se pudo desactivar el responsable.')
  } finally {
    guardando.value = false
  }
}

watch(() => props.indicador.id, cargar)
onMounted(cargar)
</script>

<template>
  <div class="responsables-block">
    <div class="responsables-head">
      <span>Responsables</span>
      <p>Ejecutores operativos que reciben los avisos de periodos pendientes y sin registro de este KPI.</p>
    </div>

    <div v-if="error" class="responsables-error">{{ error }}</div>

    <div v-if="cargando" class="sin-responsable">Cargando responsables...</div>

    <div v-else-if="!activos.length" class="sin-responsable">
      Sin responsable
    </div>

    <ul v-else class="responsables-lista">
      <li v-for="responsable in activos" :key="responsable.id">
        <div>
          <span class="responsable-nombre">{{ responsable.usuario_nombre }}</span>
          <span class="responsable-usuario">{{ responsable.usuario_username }}</span>
        </div>

        <button
          v-if="puedeGestionar"
          class="btn-quitar"
          type="button"
          :disabled="guardando"
          @click="desactivar(responsable)"
        >
          Desactivar
        </button>
      </li>
    </ul>

    <div v-if="puedeGestionar && admiteAsignaciones" class="responsables-asignar">
      <SelectorBuscable
        v-model="usuarioSeleccionado"
        :opciones="opcionesCandidatos"
        placeholder="Seleccionar Ejecutor operativo"
        placeholder-busqueda="Escribí el nombre o usuario..."
        mensaje-vacio="No hay Ejecutores operativos activos disponibles."
        :disabled="guardando"
      />

      <button
        class="btn-asignar"
        type="button"
        :disabled="!usuarioSeleccionado || guardando"
        @click="asignar"
      >
        Asignar
      </button>
    </div>

    <p v-else-if="puedeGestionar" class="responsables-nota">
      Este KPI está anulado o su plan está Cerrado: no admite asignaciones nuevas.
    </p>
  </div>
</template>

<style scoped>
.responsables-block {
  border-radius: 12px;
  border: 1px solid #e4eaef;
  background: #f6f9fa;
  padding: 14px;
}

.responsables-head span {
  display: block;
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
}

.responsables-head p,
.responsables-nota {
  margin: 4px 0 12px;
  color: #9aa8b8;
  font-size: 12px;
  font-weight: 500;
}

.responsables-nota {
  margin: 12px 0 0;
}

.sin-responsable {
  border-radius: 10px;
  background: rgba(154, 168, 184, 0.16);
  color: #5e6e82;
  font-size: 12.5px;
  font-weight: 700;
  padding: 10px 12px;
}

.responsables-error {
  border-radius: 10px;
  background: rgba(231, 111, 81, 0.12);
  color: #c4502f;
  font-size: 12.5px;
  font-weight: 700;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.responsables-lista {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.responsables-lista li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #e4eaef;
}

.responsable-nombre {
  display: block;
  color: #1d3557;
  font-size: 12.5px;
  font-weight: 800;
}

.responsable-usuario {
  color: #9aa8b8;
  font-size: 11.5px;
  font-weight: 600;
}

.responsables-asignar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 12px;
}

.responsables-asignar > :first-child {
  flex: 1;
}

.btn-asignar,
.btn-quitar {
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  font-size: 12.5px;
  font-weight: 800;
  cursor: pointer;
}

.btn-asignar {
  background: #1d3557;
  color: #ffffff;
}

.btn-quitar {
  background: rgba(231, 111, 81, 0.12);
  color: #c4502f;
}

.btn-asignar:disabled,
.btn-quitar:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .responsables-asignar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
