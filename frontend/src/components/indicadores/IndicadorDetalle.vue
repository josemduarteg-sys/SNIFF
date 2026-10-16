<script setup>
import { computed } from 'vue'
import { formatearNumero } from '../../utils/formato'
import { claseColorCumplimiento, textoEstadoCumplimiento } from '../../utils/cumplimiento'

const props = defineProps({
  indicador: {
    type: Object,
    required: true,
  },
  rangos: {
    type: Array,
    required: false,
    default: () => [],
  },
})

const tieneMediciones = computed(() => {
  return props.indicador.promedio_acumulado !== null && props.indicador.promedio_acumulado !== undefined
})

const textoPromedioAcumulado = computed(() => {
  if (!tieneMediciones.value) {
    return 'Sin mediciones'
  }

  return formatearNumero(props.indicador.promedio_acumulado, { unidad: props.indicador.unidad_medida })
})

const claseEstadoAcumulado = computed(() => claseColorCumplimiento(props.indicador.estado_acumulado_color))

function textoEstado(estado) {
  const estados = {
    borrador: 'Borrador',
    autorizado: 'Activo',
    anulado: 'Anulado',
  }

  return estados[estado] || estado || 'Sin estado'
}

function formatearCriterio(rango) {
  // valor_minimo es inclusivo y valor_maximo es exclusivo (NULL = sin límite
  // superior). Se describe en palabras, con dos decimales, para no mostrar
  // nunca la precisión interna del límite (ej. 69.9999).
  const minimo = formatearNumero(rango.valor_minimo, { unidad: '%' })

  if (rango.valor_maximo === null || rango.valor_maximo === undefined) {
    return `Desde ${minimo} · sin límite superior`
  }

  const maximo = formatearNumero(rango.valor_maximo, { unidad: '%' })

  if (Number(rango.valor_minimo) === 0) {
    return `Menor que ${maximo}`
  }

  return `Desde ${minimo} hasta menos de ${maximo}`
}
</script>

<template>
  <section class="detail-wrapper">
    <div class="detail-summary">
      <div>
        <span class="eyebrow">Indicador KPI</span>
        <h3>{{ indicador.nombre }}</h3>
        <p>{{ indicador.descripcion || 'Sin descripción registrada.' }}</p>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-item">
        <span>Plan estratégico</span>
        <strong>{{ indicador.plan_estrategico_titulo || 'Sin plan estratégico' }}</strong>
      </div>

      <div class="detail-item">
        <span>Plan anual</span>
        <strong>{{ indicador.plan_anual_nombre || 'Sin plan anual' }}</strong>
      </div>

      <div class="detail-item detail-full">
        <span>Objetivo general</span>
        <strong>{{ indicador.objetivo_general_texto || 'Sin objetivo general' }}</strong>
      </div>

      <div class="detail-item detail-full">
        <span>Objetivo específico</span>
        <strong>{{ indicador.objetivo_especifico_texto || 'Sin objetivo específico' }}</strong>
      </div>

      <div class="detail-item">
        <span>Meta</span>
        <strong>{{ formatearNumero(indicador.valor_meta, { unidad: indicador.unidad_medida }) }}</strong>
      </div>

      <div class="detail-item">
        <span>Unidad de medida</span>
        <strong>{{ indicador.unidad_medida || 'Sin unidad' }}</strong>
      </div>

      <div class="detail-item">
        <span>Frecuencia</span>
        <strong>{{ indicador.frecuencia_nombre || 'Sin frecuencia' }}</strong>
      </div>

      <div class="detail-item">
        <span>Ponderación</span>
        <strong>{{ indicador.ponderacion != null ? `${indicador.ponderacion}%` : 'Sin ponderar' }}</strong>
      </div>

      <div class="detail-item">
        <span>Distribuido / pendiente en el ámbito</span>
        <strong>{{ indicador.ponderacion_total_ambito }}% / {{ indicador.ponderacion_pendiente_ambito }}%</strong>
      </div>

      <div class="detail-item">
        <span>Estado</span>
        <strong>{{ textoEstado(indicador.estado) }}</strong>
      </div>

      <div class="detail-item">
        <span>Creado por</span>
        <strong>{{ indicador.creado_por_username || 'Sistema' }}</strong>
      </div>

      <div class="detail-item">
        <span>Autorizado por</span>
        <strong>{{ indicador.autorizado_por_username || 'Aún no autorizado' }}</strong>
      </div>

      <div class="detail-item detail-full">
        <span>Fórmula de medición</span>
        <strong>{{ indicador.formula_medicion || 'Sin fórmula registrada' }}</strong>
      </div>
    </div>

    <div class="criterios-block">
      <div class="criterios-head">
        <span>Seguimiento acumulado</span>
        <p>Promedio directo de los resultados registrados de este KPI y su estado según sus propios rangos de cumplimiento.</p>
      </div>

      <div class="seguimiento-grid">
        <div class="detail-item">
          <span>Promedio acumulado</span>
          <strong>{{ textoPromedioAcumulado }}</strong>
        </div>

        <div class="detail-item">
          <span>Cantidad de mediciones</span>
          <strong>{{ indicador.cantidad_mediciones ?? 0 }}</strong>
        </div>

        <div class="detail-item">
          <span>Estado actual acumulado</span>
          <strong v-if="tieneMediciones">
            <span class="badge" :class="claseEstadoAcumulado">
              <span class="badge-dot"></span>
              {{ textoEstadoCumplimiento(indicador.estado_acumulado_nombre) }}
            </span>
          </strong>
          <strong v-else>Sin mediciones</strong>
        </div>
      </div>
    </div>

    <div class="criterios-block">
      <div class="criterios-head">
        <span>Criterios de cumplimiento</span>
        <p>Rangos configurados para clasificar el porcentaje de cumplimiento de este KPI.</p>
      </div>

      <div v-if="!rangos.length" class="sin-criterio">
        Sin criterio de cumplimiento configurado
      </div>

      <ul v-else class="criterios-lista">
        <li v-for="rango in rangos" :key="rango.id">
          <span class="criterio-nombre">{{ rango.estado_cumplimiento_nombre || 'Sin estado' }}</span>
          <span class="criterio-rango">{{ formatearCriterio(rango) }}</span>
        </li>
      </ul>
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

.detail-full {
  grid-column: 1 / -1;
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
  line-height: 1.45;
}

.criterios-block {
  border-radius: 12px;
  border: 1px solid #e4eaef;
  background: #f6f9fa;
  padding: 14px;
}

.seguimiento-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(140px, 1fr));
  gap: 12px;
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

.criterios-head span {
  display: block;
  color: #1d3557;
  font-size: 13px;
  font-weight: 800;
}

.criterios-head p {
  margin: 4px 0 12px;
  color: #9aa8b8;
  font-size: 12px;
  font-weight: 500;
}

.sin-criterio {
  border-radius: 10px;
  background: rgba(154, 168, 184, 0.16);
  color: #5e6e82;
  font-size: 12.5px;
  font-weight: 700;
  padding: 10px 12px;
}

.criterios-lista {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.criterios-lista li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #e4eaef;
}

.criterio-nombre {
  color: #1d3557;
  font-size: 12.5px;
  font-weight: 800;
}

.criterio-rango {
  color: #5e6e82;
  font-size: 12.5px;
  font-weight: 700;
}

@media (max-width: 640px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .seguimiento-grid {
    grid-template-columns: 1fr;
  }
}
</style>
