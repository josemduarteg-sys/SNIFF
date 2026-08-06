<script setup>
import { computed } from 'vue'

const props = defineProps({
  medicion: {
    type: Object,
    required: true,
  },
})

const porcentaje = computed(() => {
  const valor = Number(props.medicion.porcentaje_cumplimiento)
  return Number.isNaN(valor) ? 0 : valor
})

function estadoClase(nombreEstado) {
  const estado = nombreEstado?.toLowerCase() || ''

  if (estado.includes('favorable')) return 'ok'
  if (estado.includes('riesgo')) return 'warning'
  if (estado.includes('incumplido')) return 'danger'
  if (estado.includes('pendiente')) return 'neutral'

  return 'neutral'
}

function porcentajeClase(valor) {
  const numero = Number(valor)

  if (numero >= 90) return 'ok'
  if (numero >= 70) return 'warning'
  return 'danger'
}

function formatearNumero(valor) {
  if (valor === null || valor === undefined || valor === '') return '-'

  const numero = Number(valor)
  if (Number.isNaN(numero)) return valor

  return numero.toLocaleString('es-GT', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })
}

function formatearPorcentaje(valor) {
  const numero = Number(valor)

  if (Number.isNaN(numero)) return '0.00%'

  return `${numero.toFixed(2)}%`
}

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

function obtenerFuente(medicion) {
  if (medicion.archivo_importado) return 'CSV'
  if (medicion.consulta_dw) return 'Data Warehouse'
  return 'Manual'
}

function fuenteClase(medicion) {
  const fuente = obtenerFuente(medicion).toLowerCase()

  if (fuente.includes('csv')) return 'csv'
  if (fuente.includes('warehouse')) return 'dw'

  return 'manual'
}
</script>

<template>
  <section class="detail-wrapper">
    <div class="detail-summary">
      <div>
        <span class="eyebrow">Indicador KPI</span>
        <h3>{{ medicion.indicador_nombre || 'Sin KPI' }}</h3>
        <p>{{ medicion.observacion || medicion.observaciones || 'Sin observaciones registradas.' }}</p>
      </div>

      <span class="badge" :class="estadoClase(medicion.estado_cumplimiento_nombre)">
        <span class="badge-dot"></span>
        {{ medicion.estado_cumplimiento_nombre || 'Sin estado' }}
      </span>
    </div>

    <div class="progress-block">
      <div class="progress-head">
        <span>Cumplimiento calculado</span>
        <strong :class="porcentajeClase(porcentaje)">
          {{ formatearPorcentaje(porcentaje) }}
        </strong>
      </div>

      <div class="progress-track">
        <div
          class="progress-fill"
          :class="porcentajeClase(porcentaje)"
          :style="{ width: `${Math.min(porcentaje, 100)}%` }"
        ></div>
      </div>
    </div>

    <div class="detail-grid">
      <article class="detail-card">
        <span>Periodo</span>
        <strong>{{ medicion.periodo_nombre || 'Sin periodo' }}</strong>
      </article>

      <article class="detail-card">
        <span>Meta definida</span>
        <strong>{{ formatearNumero(medicion.valor_meta) }}</strong>
      </article>

      <article class="detail-card">
        <span>Resultado medido</span>
        <strong>{{ formatearNumero(medicion.valor_resultado) }}</strong>
      </article>

      <article class="detail-card">
        <span>Fuente de dato</span>
        <strong>
          <span class="source-chip" :class="fuenteClase(medicion)">
            {{ obtenerFuente(medicion) }}
          </span>
        </strong>
      </article>

      <article class="detail-card">
        <span>Fecha de registro</span>
        <strong>{{ formatearFecha(medicion.fecha_registro || medicion.created_at) }}</strong>
      </article>

      <article class="detail-card">
        <span>ID de medición</span>
        <strong>#{{ medicion.id }}</strong>
      </article>
    </div>

    <div class="note-box">
      <strong>Nota:</strong>
      El porcentaje y el estado de cumplimiento son calculados por el backend según la meta asociada y los rangos configurados para el KPI.
    </div>
  </section>
</template>

<style scoped>
.detail-wrapper {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-summary {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  padding-bottom: 18px;
  border-bottom: 1px solid #eef2f5;
}

.eyebrow {
  display: block;
  color: #457b9d;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: 6px;
}

h3 {
  margin: 0;
  color: #1d3557;
  font-size: 18px;
  font-weight: 800;
}

p {
  margin: 6px 0 0;
  color: #9aa8b8;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.45;
}

.progress-block {
  background: #f6f9fa;
  border: 1px solid #eef2f5;
  border-radius: 14px;
  padding: 16px;
}

.progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #5e6e82;
  font-size: 13px;
  font-weight: 800;
}

.progress-head strong {
  font-size: 20px;
}

.progress-head strong.ok { color: #2a9d8f; }
.progress-head strong.warning { color: #b9701e; }
.progress-head strong.danger { color: #e76f51; }

.progress-track {
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: #e4eaef;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
}

.progress-fill.ok { background: #2a9d8f; }
.progress-fill.warning { background: #f4a261; }
.progress-fill.danger { background: #e76f51; }

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 12px;
}

.detail-card {
  border: 1px solid #e4eaef;
  border-radius: 12px;
  padding: 14px;
  background: #ffffff;
}

.detail-card span {
  display: block;
  color: #9aa8b8;
  font-size: 11.5px;
  font-weight: 800;
  margin-bottom: 6px;
}

.detail-card strong {
  color: #1d3557;
  font-size: 14px;
  font-weight: 800;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 800;
  padding: 5px 10px;
  border-radius: 20px;
  white-space: nowrap;
}

.badge.ok {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.badge.warning {
  background: rgba(244, 162, 97, 0.16);
  color: #b9701e;
}

.badge.danger {
  background: rgba(231, 111, 81, 0.12);
  color: #e76f51;
}

.badge.neutral {
  background: rgba(154, 168, 184, 0.16);
  color: #5e6e82;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.source-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 9px;
  font-size: 11.5px;
  font-weight: 800;
}

.source-chip.manual {
  background: rgba(69, 123, 157, 0.12);
  color: #457b9d;
}

.source-chip.csv {
  background: rgba(244, 162, 97, 0.16);
  color: #b9701e;
}

.source-chip.dw {
  background: rgba(42, 157, 143, 0.12);
  color: #2a9d8f;
}

.note-box {
  border-radius: 12px;
  background: #eaf5f5;
  color: #457b9d;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.5;
  padding: 13px 14px;
}

.note-box strong {
  font-weight: 800;
}

@media (max-width: 640px) {
  .detail-summary {
    flex-direction: column;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
