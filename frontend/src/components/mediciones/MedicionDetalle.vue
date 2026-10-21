<script setup>
import { computed, ref } from 'vue'
import { formatearNumero, formatearDiferencia } from '../../utils/formato'
import {
  SIN_REGISTRO,
  claseColorCumplimiento,
  esMedicionSinRegistro,
  textoEstadoCumplimiento,
} from '../../utils/cumplimiento'
import { descargarEvidencia, descargarArchivoEvidencia } from '../../services/medicionService'

const props = defineProps({
  medicion: {
    type: Object,
    required: true,
  },
})

const claseCumplimiento = computed(() => claseColorCumplimiento(props.medicion.estado_cumplimiento_color))

const tienePromedioAcumulado = computed(() => {
  return props.medicion.promedio_acumulado_hasta_medicion !== null
    && props.medicion.promedio_acumulado_hasta_medicion !== undefined
})

const textoPromedioAcumulado = computed(() => {
  if (!tienePromedioAcumulado.value) {
    return 'Sin mediciones'
  }

  return formatearNumero(props.medicion.promedio_acumulado_hasta_medicion, { unidad: props.medicion.unidad_medida })
})

const claseEstadoAcumulado = computed(() => claseColorCumplimiento(props.medicion.estado_acumulado_hasta_medicion_color))

// Etapa 3 (C3): una omisión no tiene resultado ni diferencia con la meta.
const sinRegistro = computed(() => esMedicionSinRegistro(props.medicion))

const textoResultado = computed(() => {
  if (sinRegistro.value) return SIN_REGISTRO

  return formatearNumero(props.medicion.valor_resultado, { unidad: props.medicion.unidad_medida })
})

const diferencia = computed(() => {
  if (sinRegistro.value) return '-'

  return formatearDiferencia(props.medicion.valor_resultado, props.medicion.valor_meta, {
    unidad: props.medicion.unidad_medida,
  })
})

// Bloque 4: una medición de cierre automático no tiene un usuario humano
// real detrás (registrado_por queda NULL a propósito). Se muestra "Sistema"
// únicamente en pantalla, sin inventar un usuario falso en la base.
const registradoPorTexto = computed(() => {
  if (props.medicion.cierre_automatico && !props.medicion.registrado_por_username) {
    return 'Sistema'
  }

  return props.medicion.registrado_por_username || 'Sistema'
})

const tipoRegistroTexto = computed(() => {
  return props.medicion.cierre_automatico ? 'Cierre automático' : 'Manual'
})

const descargando = ref(false)
const abriendo = ref(false)

const extensionEvidencia = computed(() => {
  const nombre = props.medicion.evidencia_nombre || ''
  const partes = nombre.split('.')
  return partes.length > 1 ? partes.pop().toUpperCase() : ''
})

async function verEvidencia() {
  abriendo.value = true

  try {
    const blob = await descargarEvidencia(props.medicion.id)
    const url = window.URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener')
    window.setTimeout(() => window.URL.revokeObjectURL(url), 60000)
  } catch {
    // Silencioso: la descarga es una acción secundaria del detalle: si
    // falla (por ejemplo, el archivo ya no existe), no rompe la vista.
  } finally {
    abriendo.value = false
  }
}

async function descargarEvidenciaArchivo() {
  descargando.value = true

  try {
    const blob = await descargarArchivoEvidencia(props.medicion.id)
    const url = window.URL.createObjectURL(blob)
    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = props.medicion.evidencia_nombre || 'evidencia'
    document.body.appendChild(enlace)
    enlace.click()
    enlace.remove()
    window.setTimeout(() => window.URL.revokeObjectURL(url), 60000)
  } catch {
    // Silencioso: mismo criterio que verEvidencia().
  } finally {
    descargando.value = false
  }
}

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
        <p v-if="sinRegistro">
          Este periodo venció sin que se registrara un resultado y el sistema lo cerró automáticamente.
          No es un resultado del KPI: no forma parte del promedio acumulado.
        </p>
        <p v-else>{{ medicion.observacion || medicion.observaciones || 'Sin observaciones registradas.' }}</p>
      </div>

      <div class="estado-periodo-resumen">
        <span class="mini-label">Estado del periodo</span>
        <span class="badge" :class="claseCumplimiento">
          <span class="badge-dot"></span>
          {{ textoEstadoCumplimiento(medicion.estado_cumplimiento_nombre) }}
        </span>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-item">
        <span>KPI</span>
        <strong>{{ medicion.indicador_nombre || 'Sin KPI' }}</strong>
      </div>

      <div class="detail-item">
        <span>Plan estratégico</span>
        <strong>{{ medicion.indicador_plan_estrategico_titulo || 'No definido' }}</strong>
      </div>

      <div class="detail-item">
        <span>Plan anual</span>
        <strong>{{ medicion.indicador_plan_anual_nombre || 'No definido' }}</strong>
      </div>

      <div class="detail-item">
        <span>Objetivo</span>
        <strong>{{ medicion.indicador_objetivo_especifico_texto || 'No definido' }}</strong>
      </div>

      <div class="detail-item">
        <span>Periodo evaluado</span>
        <strong>{{ medicion.periodo_nombre || 'No definido' }}</strong>
      </div>

      <div class="detail-item">
        <span>Frecuencia</span>
        <strong>{{ medicion.indicador_frecuencia_nombre || 'No definida' }}</strong>
      </div>

      <div class="detail-item">
        <span>Meta del KPI</span>
        <strong>{{ formatearNumero(medicion.valor_meta, { unidad: medicion.unidad_medida }) }}</strong>
      </div>

      <div class="detail-item">
        <span>Resultado</span>
        <strong>{{ textoResultado }}</strong>
      </div>

      <div class="detail-item">
        <span>Diferencia respecto a la meta</span>
        <strong>{{ diferencia }}</strong>
      </div>

      <div class="detail-item">
        <span title="Estado individual de esta medición, clasificado directamente contra los rangos configurados para este KPI.">Estado del periodo</span>
        <strong>{{ textoEstadoCumplimiento(medicion.estado_cumplimiento_nombre) }}</strong>
      </div>

      <div class="detail-item">
        <span>Tipo de registro</span>
        <strong>{{ tipoRegistroTexto }}</strong>
      </div>

      <div class="detail-item">
        <span>Registrado por</span>
        <strong>{{ registradoPorTexto }}</strong>
      </div>

      <div class="detail-item">
        <span>Fecha de medición</span>
        <strong>{{ formatearFecha(medicion.fecha_medicion) }}</strong>
      </div>

      <div class="detail-item">
        <span>Fecha de registro</span>
        <strong>{{ formatearFecha(medicion.fecha_registro) }}</strong>
      </div>
    </div>

    <div class="observation-box">
      <span>Seguimiento acumulado del KPI hasta este periodo</span>

      <div class="acumulado-grid">
        <div class="detail-item">
          <span>Promedio acumulado hasta este periodo</span>
          <strong>{{ textoPromedioAcumulado }}</strong>
        </div>

        <div class="detail-item">
          <span>Estado acumulado hasta este periodo</span>
          <strong v-if="tienePromedioAcumulado">
            <span class="badge" :class="claseEstadoAcumulado">
              <span class="badge-dot"></span>
              {{ textoEstadoCumplimiento(medicion.estado_acumulado_hasta_medicion_nombre) }}
            </span>
          </strong>
          <strong v-else>Sin mediciones</strong>
        </div>
      </div>

      <p class="acumulado-nota">
        Es el promedio directo de todos los resultados de este KPI hasta este periodo — no es el
        resultado de este periodo en particular (ver "Resultado" arriba) ni el "Estado del periodo".
      </p>
    </div>

    <div class="observation-box">
      <span>Observaciones / razones</span>
      <p>{{ medicion.observacion || medicion.observaciones || 'Sin observaciones registradas.' }}</p>
    </div>

    <div class="observation-box">
      <span>Evidencia / respaldo de lo realizado</span>

      <template v-if="medicion.tiene_evidencia">
        <p class="evidencia-nombre">
          {{ medicion.evidencia_nombre }}
          <span v-if="extensionEvidencia" class="evidencia-tipo">{{ extensionEvidencia }}</span>
        </p>

        <div class="evidencia-acciones">
          <button
            class="btn-evidencia"
            type="button"
            :disabled="abriendo"
            @click="verEvidencia"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            {{ abriendo ? 'Abriendo...' : 'Ver evidencia' }}
          </button>

          <button
            class="btn-evidencia"
            type="button"
            :disabled="descargando"
            @click="descargarEvidenciaArchivo"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            {{ descargando ? 'Descargando...' : 'Descargar' }}
          </button>
        </div>
      </template>
      <p v-else>Sin evidencia adjunta.</p>
    </div>

    <div class="note-box">
      <strong>Nota:</strong>
      El estado de cumplimiento se calcula automáticamente comparando el resultado directamente contra los rangos configurados para este KPI.
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

.estado-periodo-resumen {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.mini-label {
  color: #9aa8b8;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.4px;
  text-transform: uppercase;
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

.acumulado-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 10px;
}

.acumulado-grid strong {
  font-size: 16px;
}

.acumulado-nota {
  margin-top: 8px !important;
  color: #9aa8b8 !important;
  font-size: 11.5px !important;
  font-weight: 500 !important;
}

.evidencia-nombre {
  margin: 0 0 10px !important;
  color: #1d3557 !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  display: flex;
  align-items: center;
  gap: 8px;
}

.evidencia-tipo {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(69, 123, 157, 0.12);
  color: #457b9d;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.4px;
}

.evidencia-acciones {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-evidencia {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 36px;
  padding: 0 14px;
  border-radius: 9px;
  border: 1.5px solid #e4eaef;
  background: #ffffff;
  color: #1d3557;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.btn-evidencia:hover:not(:disabled) {
  background: #eaf5f5;
  border-color: #a8dadc;
}

.btn-evidencia:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-evidencia svg {
  stroke: currentColor;
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

  .estado-periodo-resumen {
    align-items: flex-start;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .acumulado-grid {
    grid-template-columns: 1fr;
  }
}
</style>
