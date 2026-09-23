<script setup>
defineProps({
  estrategia: {
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
</script>

<template>
  <section class="detail-wrapper">
    <div class="detail-summary">
      <div>
        <span class="eyebrow">Estrategia</span>
        <h3>{{ estrategia.nombre }}</h3>
        <p>{{ estrategia.descripcion || 'Sin descripción registrada.' }}</p>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-item">
        <span>Área</span>
        <strong>{{ estrategia.area_nombre || 'Sin área' }}</strong>
      </div>

      <div class="detail-item">
        <span>Estado</span>
        <strong>{{ textoEstado(estrategia.estado) }}</strong>
      </div>

      <div class="detail-item">
        <span>Fecha de inicio</span>
        <strong>{{ formatearFecha(estrategia.fecha_inicio) }}</strong>
      </div>

      <div class="detail-item">
        <span>Fecha de finalización</span>
        <strong>{{ formatearFecha(estrategia.fecha_fin) }}</strong>
      </div>

      <div class="detail-item">
        <span>Creado por</span>
        <strong>{{ estrategia.creado_por_username || 'Sistema' }}</strong>
      </div>

      <div class="detail-item">
        <span>Fecha de creación</span>
        <strong>{{ formatearFecha(estrategia.fecha_creacion) }}</strong>
      </div>
    </div>

    <div class="observation-box">
      <span>Descripción</span>
      <p>{{ estrategia.descripcion || 'Sin descripción registrada.' }}</p>
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

@media (max-width: 640px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
