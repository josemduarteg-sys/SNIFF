<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import api from '../services/api'

defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const estrategias = ref([])
const cargando = ref(false)
const error = ref('')

const estrategiasActivas = computed(() => {
  return estrategias.value.filter((item) => item.estado === 'activa' || item.estado === true).length
})

function normalizarRespuesta(response) {
  if (Array.isArray(response.data)) {
    return response.data
  }

  if (Array.isArray(response.data.results)) {
    return response.data.results
  }

  return []
}

async function cargarEstrategias() {
  cargando.value = true
  error.value = ''

  try {
    const response = await api.get('estrategias/')
    estrategias.value = normalizarRespuesta(response)
  } catch (e) {
    error.value = 'No se pudieron cargar las estrategias.'
  } finally {
    cargando.value = false
  }
}

function estadoClase(estado) {
  if (estado === 'activa' || estado === true) return 'active'
  if (estado === 'finalizada') return 'finished'
  if (estado === 'en_revision') return 'warning'
  return 'inactive'
}

function textoEstado(estado) {
  if (estado === true) return 'Activa'
  if (estado === false) return 'Inactiva'

  const estados = {
    activa: 'Activa',
    en_revision: 'En revisión',
    finalizada: 'Finalizada',
    inactiva: 'Inactiva',
  }

  return estados[estado] || estado || 'Sin estado'
}

function cerrarSesion() {
  emit('logout')
}

onMounted(() => {
  cargarEstrategias()
})
</script>

<template>
  <AppLayout
    :usuario="usuario"
    titulo="Gestión de Estrategias"
    subtitulo="Administra las estrategias empresariales vinculadas al seguimiento de indicadores KPI."
    breadcrumb-actual="Estrategias"
    @logout="cerrarSesion"
  >
    <template #actions>
      <button class="btn-primary">
        + Nueva estrategia
      </button>
    </template>

    <section class="summary-grid">
      <article class="summary-card">
        <span>Total registradas</span>
        <strong>{{ estrategias.length }}</strong>
        <p>Estrategias creadas en el sistema</p>
      </article>

      <article class="summary-card">
        <span>Activas</span>
        <strong>{{ estrategiasActivas }}</strong>
        <p>Estrategias actualmente en seguimiento</p>
      </article>
    </section>

    <section class="card-panel">
      <div class="panel-head">
        <div>
          <h2>Listado de estrategias</h2>
          <p>Consulta general de estrategias registradas.</p>
        </div>
      </div>

      <div v-if="cargando" class="message">
        Cargando estrategias...
      </div>

      <div v-else-if="error" class="message error">
        {{ error }}
      </div>

      <div v-else-if="!estrategias.length" class="empty-state">
        No hay estrategias registradas todavía.
      </div>

      <table v-else>
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Área</th>
            <th>Fecha inicio</th>
            <th>Fecha fin</th>
            <th>Estado</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="estrategia in estrategias"
            :key="estrategia.id"
          >
            <td>
              <div class="cell-main">{{ estrategia.nombre }}</div>
              <div class="cell-sub">{{ estrategia.descripcion || 'Sin descripción' }}</div>
            </td>

            <td>{{ estrategia.area_nombre || 'Sin área' }}</td>
            <td>{{ estrategia.fecha_inicio || 'No definida' }}</td>
            <td>{{ estrategia.fecha_fin || 'No definida' }}</td>

            <td>
              <span class="badge" :class="estadoClase(estrategia.estado)">
                {{ textoEstado(estrategia.estado) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </AppLayout>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card,
.card-panel {
  background: #ffffff;
  border: 1px solid #e4eaef;
  border-radius: 14px;
  box-shadow: 0 8px 22px rgba(29, 53, 87, 0.07);
}

.summary-card {
  padding: 20px;
}

.summary-card span {
  color: #457b9d;
  font-size: 13px;
  font-weight: 800;
}

.summary-card strong {
  display: block;
  color: #1d3557;
  font-size: 34px;
  margin-top: 10px;
}

.summary-card p {
  margin: 6px 0 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 600;
}

.card-panel {
  padding: 22px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.panel-head h2 {
  margin: 0;
  color: #1d3557;
  font-size: 17px;
  font-weight: 800;
}

.panel-head p {
  margin: 4px 0 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 500;
}

.btn-primary {
  height: 40px;
  padding: 0 16px;
  border: none;
  border-radius: 10px;
  background: #1d3557;
  color: #ffffff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.btn-primary:hover {
  background: #152840;
}

.message,
.empty-state {
  padding: 16px;
  border-radius: 12px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 13px;
  font-weight: 700;
}

.message.error {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  text-align: left;
  color: #9aa8b8;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 12px 10px;
  border-bottom: 1px solid #e4eaef;
}

td {
  padding: 13px 10px;
  border-bottom: 1px solid #eef2f5;
  color: #1d3557;
  font-size: 13px;
  font-weight: 600;
  vertical-align: top;
}

.cell-main {
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
}

.cell-sub {
  color: #9aa8b8;
  font-size: 12px;
  font-weight: 500;
  margin-top: 2px;
  max-width: 520px;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.badge.active {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.badge.warning {
  background: rgba(244, 162, 97, 0.16);
  color: #b86520;
}

.badge.finished {
  background: rgba(69, 123, 157, 0.12);
  color: #457b9d;
}

.badge.inactive {
  background: rgba(154, 168, 184, 0.16);
  color: #5e6e82;
}

@media (max-width: 800px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  table {
    display: block;
    overflow-x: auto;
  }
}
</style>