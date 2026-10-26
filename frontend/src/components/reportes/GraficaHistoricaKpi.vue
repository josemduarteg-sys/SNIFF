<script setup>
import { computed } from 'vue'
import { formatearNumero } from '../../utils/formato'
import { escalaVertical, serieHistorica, tramosConResultado } from '../../utils/reportes'

// D5: evolución de UN KPI (una sola unidad por gráfica). Línea del resultado
// real, meta como referencia punteada y periodos "Sin registro" marcados
// aparte: cortan la línea y nunca se dibujan como cero.
const props = defineProps({
  mediciones: {
    type: Array,
    default: () => [],
  },
  unidad: {
    type: String,
    default: '',
  },
})

const ALTO = 300
const MARGEN = { izquierda: 72, derecha: 20, arriba: 18, abajo: 58 }
const ANCHO_MINIMO_PERIODO = 64

const serie = computed(() => serieHistorica(props.mediciones))
const escala = computed(() => escalaVertical(serie.value, props.unidad))
const ancho = computed(() => Math.max(640, serie.value.length * ANCHO_MINIMO_PERIODO + MARGEN.izquierda + MARGEN.derecha))
const anchoUtil = computed(() => ancho.value - MARGEN.izquierda - MARGEN.derecha)
const altoUtil = ALTO - MARGEN.arriba - MARGEN.abajo
const base = MARGEN.arriba + altoUtil

function x(indice) {
  return MARGEN.izquierda + ((indice + 0.5) * anchoUtil.value) / Math.max(serie.value.length, 1)
}

function y(valor) {
  const { minimo, maximo } = escala.value
  return MARGEN.arriba + altoUtil - ((valor - minimo) / (maximo - minimo)) * altoUtil
}

const tramos = computed(() => tramosConResultado(serie.value).map((tramo) => (
  tramo.map((punto) => `${x(punto.indice)},${y(punto.valor)}`).join(' ')
)))

const tieneMeta = computed(() => serie.value.some((punto) => punto.meta !== null))

const lineaMeta = computed(() => serie.value
  .map((punto, indice) => (punto.meta === null ? null : `${x(indice)},${y(punto.meta)}`))
  .filter(Boolean)
  .join(' '))

const haySinRegistro = computed(() => serie.value.some((punto) => punto.sinRegistro))

const estadosPresentes = computed(() => {
  const vistos = new Map()
  serie.value.forEach((punto) => {
    if (!punto.sinRegistro && punto.estado && !vistos.has(punto.estado)) vistos.set(punto.estado, punto.clase)
  })
  return [...vistos.entries()].map(([nombre, clase]) => ({ nombre, clase }))
})

function texto(valor) {
  return formatearNumero(valor, { unidad: props.unidad })
}

function textoMarca(valor) {
  return formatearNumero(valor, { decimales: Number.isInteger(valor) ? 0 : 2 })
}

function descripcion(punto) {
  const meta = punto.meta === null ? '' : ` · Meta ${texto(punto.meta)}`

  if (punto.sinRegistro) return `${punto.etiqueta}: Sin registro (periodo vencido sin resultado)${meta}`

  return `${punto.etiqueta}: ${texto(punto.valor)} · ${punto.estado || 'Sin estado'}${meta}`
}

// "Enero 2027" -> ["Enero", "2027"]; el año va en la segunda línea.
function lineasEtiqueta(etiqueta) {
  const partes = String(etiqueta).split(' ')
  if (partes.length < 2) return [etiqueta]
  return [partes.slice(0, -1).join(' '), partes[partes.length - 1]]
}

const textoUnidad = computed(() => props.unidad || 'Valor')
</script>

<template>
  <div class="grafica-historica">
    <p v-if="!serie.length" class="grafica-vacia">
      Este KPI todavía no tiene mediciones. La gráfica se mostrará cuando se registre el primer periodo.
    </p>

    <template v-else>
      <div class="grafica-scroll">
        <svg
          :viewBox="`0 0 ${ancho} ${ALTO}`"
          :style="{ minWidth: `${Math.min(ancho, serie.length * ANCHO_MINIMO_PERIODO + 92)}px` }"
          role="img"
          :aria-label="`Evolución del KPI en ${textoUnidad}`"
          preserveAspectRatio="xMinYMid meet"
        >
          <!-- Eje vertical en la unidad del KPI -->
          <g class="eje">
            <g v-for="marca in escala.marcas" :key="marca">
              <line :x1="MARGEN.izquierda" :x2="ancho - MARGEN.derecha" :y1="y(marca)" :y2="y(marca)" class="guia" />
              <text :x="MARGEN.izquierda - 8" :y="y(marca) + 4" text-anchor="end">{{ textoMarca(marca) }}</text>
            </g>
            <text
              :x="14"
              :y="MARGEN.arriba + altoUtil / 2"
              text-anchor="middle"
              class="titulo-eje"
              :transform="`rotate(-90 14 ${MARGEN.arriba + altoUtil / 2})`"
            >
              {{ textoUnidad }}
            </text>
          </g>

          <!-- Periodos sin registro: franja y marca propia sobre el eje -->
          <g v-for="(punto, indice) in serie" :key="`sr-${punto.id}`">
            <template v-if="punto.sinRegistro">
              <rect
                :x="x(indice) - anchoUtil / serie.length / 2"
                :y="MARGEN.arriba"
                :width="anchoUtil / serie.length"
                :height="altoUtil"
                class="franja-sin-registro"
              />
              <g class="marca-sin-registro">
                <title>{{ descripcion(punto) }}</title>
                <line :x1="x(indice) - 5" :y1="base - 11" :x2="x(indice) + 5" :y2="base - 1" />
                <line :x1="x(indice) + 5" :y1="base - 11" :x2="x(indice) - 5" :y2="base - 1" />
              </g>
            </template>
          </g>

          <polyline v-if="tieneMeta" :points="lineaMeta" class="linea-meta" />

          <polyline v-for="(puntos, indice) in tramos" :key="`t-${indice}`" :points="puntos" class="linea-resultado" />

          <g v-for="(punto, indice) in serie" :key="`p-${punto.id}`">
            <circle
              v-if="!punto.sinRegistro && punto.valor !== null"
              :cx="x(indice)"
              :cy="y(punto.valor)"
              r="5.5"
              class="punto"
              :class="punto.clase"
            >
              <title>{{ descripcion(punto) }}</title>
            </circle>
          </g>

          <!-- Eje horizontal: periodos reales del KPI -->
          <line :x1="MARGEN.izquierda" :x2="ancho - MARGEN.derecha" :y1="base" :y2="base" class="eje-base" />
          <text
            v-for="(punto, indice) in serie"
            :key="`e-${punto.id}`"
            :x="x(indice)"
            :y="base + 18"
            text-anchor="middle"
            class="etiqueta-periodo"
            :class="{ 'es-sin-registro': punto.sinRegistro }"
          >
            <tspan v-for="(linea, n) in lineasEtiqueta(punto.etiqueta)" :key="n" :x="x(indice)" :dy="n ? 13 : 0">
              {{ linea }}
            </tspan>
          </text>
        </svg>
      </div>

      <ul class="leyenda">
        <li><span class="muestra muestra-resultado"></span>Resultado real ({{ textoUnidad }})</li>
        <li v-if="tieneMeta"><span class="muestra muestra-meta"></span>Meta</li>
        <li v-if="haySinRegistro"><span class="muestra-sin-registro">×</span>Sin registro (no es cero)</li>
        <li v-for="estado in estadosPresentes" :key="estado.nombre">
          <span class="muestra-punto" :class="estado.clase"></span>{{ estado.nombre }}
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.grafica-historica {
  width: 100%;
}

.grafica-scroll {
  width: 100%;
  overflow-x: auto;
}

.grafica-scroll svg {
  display: block;
  width: 100%;
  height: auto;
}

.grafica-vacia {
  margin: 0;
  padding: 36px 16px;
  text-align: center;
  color: #5e6e82;
  font-size: 13.5px;
  font-weight: 600;
}

.eje text,
.etiqueta-periodo {
  font-size: 11px;
  fill: #5e6e82;
  font-weight: 600;
}

.titulo-eje {
  font-weight: 800;
  fill: #1d3557;
}

.guia {
  stroke: #edf1f4;
  stroke-width: 1;
}

.eje-base {
  stroke: #c9d3dc;
  stroke-width: 1.2;
}

.linea-resultado {
  fill: none;
  stroke: #457b9d;
  stroke-width: 2.5;
  stroke-linejoin: round;
}

.linea-meta {
  fill: none;
  stroke: #1d3557;
  stroke-width: 1.5;
  stroke-dasharray: 6 5;
  opacity: 0.7;
}

.punto {
  stroke: #ffffff;
  stroke-width: 2;
}

.punto.ok, .muestra-punto.ok { fill: #2a9d8f; background: #2a9d8f; }
.punto.warning, .muestra-punto.warning { fill: #e9c46a; background: #e9c46a; }
.punto.danger, .muestra-punto.danger { fill: #e76f51; background: #e76f51; }
.punto.neutral, .muestra-punto.neutral { fill: #8d99ae; background: #8d99ae; }

.franja-sin-registro {
  fill: #8d99ae;
  opacity: 0.08;
}

.marca-sin-registro line {
  stroke: #8d99ae;
  stroke-width: 2.2;
  stroke-linecap: round;
}

.etiqueta-periodo.es-sin-registro {
  fill: #8d99ae;
  font-style: italic;
}

.leyenda {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  font-size: 12px;
  font-weight: 600;
  color: #5e6e82;
}

.leyenda li {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.muestra {
  display: inline-block;
  width: 22px;
  height: 0;
  border-top: 2.5px solid #457b9d;
}

.muestra-meta {
  border-top: 2px dashed #1d3557;
}

.muestra-punto {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.muestra-sin-registro {
  color: #8d99ae;
  font-weight: 800;
  font-size: 15px;
  line-height: 1;
}
</style>
