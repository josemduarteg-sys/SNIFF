<script setup>
import { computed } from 'vue'
import { formatearNumero, formatearDiferencia } from '../../utils/formato'
import { claseColorCumplimiento, textoEstadoCumplimiento } from '../../utils/cumplimiento'

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

const claseCumplimiento = computed(() => claseColorCumplimiento(props.medicion.estado_cumplimiento_color))

const diferencia = computed(() => {
  return formatearDiferencia(props.medicion.valor_resultado, props.medicion.valor_meta, {
    unidad: props.medicion.unidad_medida,
  })
})

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
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

      <span class="badge" :class="claseCumplimiento">
        <span class="badge-dot"></span>
        {{ textoEstadoCumplimiento(medicion.estado_cumplimiento_nombre) }}
      </span>
    </div>

    <div class="progress-block">
      <div class="progress-head">
        <span title="Se calcula comparando el resultado obtenido con la meta establecida.">
          Cumplimiento de la meta
        </span>
        <strong :class="claseCumplimiento">
          {{ formatearNumero(porcentaje, { unidad: '%' }) }}
        </strong>
      </div>

      <div class="progress-track">
        <div
          class="progress-fill"
          :class="claseCumplimiento"
          :style="{ width: `${Math.min(porcentaje, 100)}%` }"
        ></div>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-item">
        <span>KPI</span>
        <strong>{{ medicion.indicador_nombre || 'Sin KPI' }}</strong>
      </div>

      <div class="detail-item">
        <span>Periodo evaluado</span>
        <strong>{{ medicion.periodo_nombre || medicion.mes_medicion || 'No definido' }}</strong>
      </div>

      <div class="detail-item">
        <span>Meta del KPI</span>
        <strong>{{ formatearNumero(medicion.valor_meta, { unidad: medicion.unidad_medida }) }}</strong>
      </div>

      <div class="detail-item">
        <span>Resultado</span>
        <strong>{{ formatearNumero(medicion.valor_resultado, { unidad: medicion.unidad_medida }) }}</strong>
      </div>

      <div class="detail-item">
        <span>Diferencia respecto a la meta</span>
        <strong>{{ diferencia }}</strong>
      </div>

      <div class="detail-item">
        <span title="Se calcula comparando el resultado obtenido con la meta establecida.">Cumplimiento de la meta</span>
        <strong>{{ formatearNumero(medicion.porcentaje_cumplimiento, { unidad: '%' }) }}</strong>
      </div>

      <div class="detail-item">
        <span>Estado</span>
        <strong>{{ textoEstadoCumplimiento(medicion.estado_cumplimiento_nombre) }}</strong>
      </div>

      <div class="detail-item">
        <span>Registrado por</span>
        <strong>{{ medicion.registrado_por_username || 'Sistema' }}</strong>
      </div>

      <div class="detail-item">
        <span>Fecha de registro</span>
        <strong>{{ formatearFecha(medicion.fecha_registro) }}</strong>
      </div>
    </div>

    <div class="observation-box">
      <span>Observaciones / razones</span>
      <p>{{ medicion.observacion || medicion.observaciones || 'Sin observaciones registradas.' }}</p>
    </div>

    <div class="observation-box">
      <span>Evidencias / respaldo de lo realizado</span>
      <p>{{ medicion.evidencia || 'Sin evidencias registradas.' }}</p>
    </div>

    <div class="note-box">
      <strong>Nota:</strong>
      El porcentaje y el estado de cumplimiento son calculados por el backend según la meta y vigencia configuradas en el KPI autorizado.
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

.detail-item {
  border: 1px solid #e4eaef;
  border-radius: 12px;
  padding: 14px;
  background: #ffffff;
}

.detail-item span {
  display: block;
  color: #9aa8b8;
  font-size: 11.5px;
  font-weight: 800;
  margin-bottom: 6px;
}

.detail-item strong {
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

.observation-box {
  border-radius: 12px;
  border: 1px solid #e4eaef;
  background: #ffffff;
  padding: 14px;
}

.observation-box span {
  display: block;
  color: #9aa8b8;
  font-size: 11.5px;
  font-weight: 800;
  margin-bottom: 6px;
}

.observation-box p {
  margin: 0;
  color: #1d3557;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
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
