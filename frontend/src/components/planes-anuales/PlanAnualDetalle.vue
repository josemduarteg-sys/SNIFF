<script setup>
defineProps({
  planAnual: {
    type: Object,
    required: true,
  },
})

function formatearFecha(fecha) {
  if (!fecha) return 'No definida'

  const soloFecha = fecha.split('T')[0]
  const [anio, mes, dia] = soloFecha.split('-')

  if (!anio || !mes || !dia) return fecha

  return `${dia}/${mes}/${anio}`
}

function textoEstado(estado) {
  const estados = {
    borrador: 'Borrador',
    en_uso: 'En uso',
    cerrado: 'Cerrado',
  }

  return estados[estado] || estado || 'Sin estado'
}
</script>

<template>
  <section class="detail-wrapper">
    <div class="detail-summary">
      <div>
        <span class="eyebrow">Plan anual</span>
        <h3>{{ planAnual.nombre || `Plan ${planAnual.anio}` }}</h3>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-item">
        <span>Plan estratégico</span>
        <strong>{{ planAnual.plan_estrategico_titulo || 'Sin especificar' }}</strong>
      </div>

      <div class="detail-item">
        <span>Estado</span>
        <strong>{{ textoEstado(planAnual.estado) }}</strong>
      </div>

      <div class="detail-item">
        <span>Creado por</span>
        <strong>{{ planAnual.creado_por_username || 'Sistema' }}</strong>
      </div>

      <div class="detail-item">
        <span>Fecha de creación</span>
        <strong>{{ formatearFecha(planAnual.fecha_creacion) }}</strong>
      </div>
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

@media (max-width: 640px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
