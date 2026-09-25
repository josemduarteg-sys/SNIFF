<script setup>
import { formatearNumero } from '../../utils/formato'

defineProps({
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
}
</style>
