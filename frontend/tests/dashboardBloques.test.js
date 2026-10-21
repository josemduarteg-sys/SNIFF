// Dashboard de la entrega (referencia visual aprobada): tarjetas, filtros por
// año, gráficos y paginación (src/utils/dashboardBloques.js,
// src/utils/dashboardFiltros.js y DashboardView.vue). Se ejecuta con `npm test`.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import {
  alturaConteo,
  codigoKpi,
  ejeConteo,
  ejeEscala,
  etiquetasDona,
  evidenciasPorKpi,
  gruposCumplimiento,
  nombreCorto,
  paginar,
  porcentajeDe,
  resumenEvidencias,
  resumenOportunidad,
  resumenTarjetas,
} from '../src/utils/dashboardBloques.js'
import { aniosDisponibles, filtrarContexto, normalizarSeleccion, planesAnualesDe } from '../src/utils/dashboardFiltros.js'

const SIN_REGISTRO = 'Sin registro'
const vista = readFileSync(new URL('../src/views/DashboardView.vue', import.meta.url), 'utf8')

function kpis(cantidad) {
  return Array.from({ length: cantidad }, (_, i) => ({ id: i + 1 }))
}

// ---------- Tarjetas ----------

test('tarjetas: conteos reales sin doble conteo ni KPI sin mediciones', () => {
  const planes = [{ estado: 'en_uso' }, { estado: 'en_uso' }, { estado: 'cerrado' }, { estado: 'borrador' }]
  const anuales = [{ estado: 'en_uso' }, { estado: 'cerrado' }]
  const autorizados = [
    { cantidad_mediciones: 3, estado_acumulado_nombre: 'Favorable' },
    { cantidad_mediciones: 2, estado_acumulado_nombre: 'En riesgo' },
    { cantidad_mediciones: 1, estado_acumulado_nombre: 'Incumplido' },
    { cantidad_mediciones: 0, estado_acumulado_nombre: null },
    { cantidad_mediciones: 2, estado_acumulado_nombre: 'Pendiente de actualización' },
  ]

  assert.deepEqual(resumenTarjetas(planes, anuales, autorizados), {
    planesEnUso: 2, planesRegistrados: 4, anualesEnUso: 1, anualesRegistrados: 2,
    kpiAutorizados: 5, kpiFavorables: 1, kpiAtencion: 2,
  })
  assert.deepEqual(resumenTarjetas([], [], []), {
    planesEnUso: 0, planesRegistrados: 0, anualesEnUso: 0, anualesRegistrados: 0,
    kpiAutorizados: 0, kpiFavorables: 0, kpiAtencion: 0,
  })
})

test('la vista renderiza las cinco tarjetas pedidas', () => {
  for (const titulo of ['Planes estratégicos en uso', 'Planes anuales en ejecución', 'KPI autorizados', 'KPI favorables', 'Requieren atención']) {
    assert.match(vista, new RegExp(`titulo: '${titulo}'`), titulo)
  }
  assert.equal(vista.match(/clave: '/g).length, 5)
  assert.doesNotMatch(vista, /Periodos sin registro'|usuarios'|Cierres automáticos/)
})

// ---------- Filtros por año y plan ----------

const planesEstrategicos = [{ id: 1, titulo: 'A', estado: 'en_uso' }, { id: 2, titulo: 'B', estado: 'en_uso' }]
const planesAnuales = [
  { id: 10, plan_estrategico: 1, anio: 2026, estado: 'cerrado' },
  { id: 11, plan_estrategico: 1, anio: 2027, estado: 'en_uso' },
  { id: 20, plan_estrategico: 2, anio: 2027, estado: 'en_uso' },
]
const datos = {
  planesEstrategicos,
  planesAnuales,
  indicadores: [
    { id: 100, plan_estrategico: 1, plan_anual: 10 },
    { id: 101, plan_estrategico: 1, plan_anual: 11 },
    { id: 200, plan_estrategico: 2, plan_anual: 20 },
  ],
  mediciones: [{ indicador: 100 }, { indicador: 101 }, { indicador: 200 }],
  alertas: [],
}

test('años: solo los de planes anuales reales, del más reciente al más antiguo', () => {
  assert.deepEqual(aniosDisponibles(planesAnuales), [2027, 2026])
  assert.deepEqual(aniosDisponibles([]), [])
})

test('un año con varios planes anuales incluye a todos, sin contradicciones', () => {
  const contexto = filtrarContexto(datos, normalizarSeleccion({ anio: '2027' }, planesEstrategicos, planesAnuales))

  assert.deepEqual(contexto.planesAnuales.map((p) => p.id), [11, 20])
  assert.deepEqual(contexto.planesEstrategicos.map((p) => p.id), [1, 2])
  assert.deepEqual(contexto.indicadores.map((k) => k.id), [101, 200])
  assert.equal(contexto.mediciones.length, 2)
})

test('año combinado con plan estratégico y con plan anual', () => {
  const conPlan = filtrarContexto(datos, normalizarSeleccion({ anio: '2027', planEstrategico: '1' }, planesEstrategicos, planesAnuales))
  assert.deepEqual(conPlan.indicadores.map((k) => k.id), [101])

  // Año 2026: solo el plan estratégico con un plan anual de ese año.
  const anio2026 = filtrarContexto(datos, normalizarSeleccion({ anio: '2026' }, planesEstrategicos, planesAnuales))
  assert.deepEqual(anio2026.planesEstrategicos.map((p) => p.id), [1])
  assert.deepEqual(anio2026.indicadores.map((k) => k.id), [100])

  // El plan anual define su año y su plan estratégico.
  assert.deepEqual(normalizarSeleccion({ planAnual: '20' }, planesEstrategicos, planesAnuales), { planEstrategico: 2, planAnual: 20, anio: 2027 })
  assert.deepEqual(normalizarSeleccion({ anio: '2026', planAnual: '20' }, planesEstrategicos, planesAnuales), { planEstrategico: 2, planAnual: 20, anio: 2027 })
  // Año inexistente o inválido: se ignora.
  assert.deepEqual(normalizarSeleccion({ anio: '1999' }, planesEstrategicos, planesAnuales), { planEstrategico: null, planAnual: null, anio: null })
  assert.deepEqual(normalizarSeleccion({ anio: 'abc' }, planesEstrategicos, planesAnuales).anio, null)
  assert.deepEqual(planesAnualesDe(planesAnuales, 1, 2027).map((p) => p.id), [11])
})

// ---------- Cumplimiento ----------

test('cumplimiento: un grupo por unidad, sin mezclar escalas', () => {
  const grupos = gruposCumplimiento([
    { id: 3, unidad_medida: '%', promedio_acumulado: '80.00', valor_meta: '85.0000' },
    { id: 1, unidad_medida: '%', promedio_acumulado: '40.00', valor_meta: '85.0000' },
    { id: 7, unidad_medida: 'días', promedio_acumulado: '4.00', valor_meta: '3.0000' },
  ])

  assert.deepEqual(grupos.map((g) => g.unidad), ['%', 'días'])
  assert.equal(grupos[0].escala, 100)
  assert.deepEqual(grupos[0].barras.map((b) => [b.codigo, b.alturaPorcentaje, b.metaPorcentaje]), [['KPI-01', 40, 85], ['KPI-03', 80, 85]])
  assert.equal(grupos[1].escala, 4)
  assert.equal(grupos[1].barras[0].alturaPorcentaje, 100)
  assert.equal(grupos[1].barras[0].metaPorcentaje, 75)
  assert.deepEqual(ejeEscala(100), [0, 25, 50, 75, 100])
})

test('cumplimiento: KPI sin mediciones no inventa una altura', () => {
  const [grupo] = gruposCumplimiento([
    { id: 5, unidad_medida: '%', promedio_acumulado: null, valor_meta: '85' },
    { id: 6, unidad_medida: '%', promedio_acumulado: '120', valor_meta: '85' },
  ])

  assert.equal(grupo.barras[0].valor, null)
  assert.equal(grupo.barras[0].alturaPorcentaje, 0)
  assert.equal(grupo.escala, 120)
  assert.equal(grupo.barras[1].alturaPorcentaje, 100)
})

test('cumplimiento: vista limitada a 6 KPI con selector de unidad', () => {
  assert.match(vista, /const KPI_POR_VISTA = 6/)
  assert.match(vista, /paginar\(grupo\.barras, paginaCumplimiento\.value, KPI_POR_VISTA\)/)
  assert.match(vista, /aria-label="Unidad de medida"/)
  assert.equal(codigoKpi({ id: 12 }), 'KPI-12')
  assert.equal(codigoKpi({ id: 3 }), 'KPI-03')
  assert.equal(nombreCorto('Porcentaje de recuperación de cartera vencida'), 'Porcentaje de recuper…')
  assert.equal(nombreCorto('Corto'), 'Corto')
})

// ---------- Estado, evidencias y oportunidad ----------

test('dona: etiquetas en el punto medio de cada segmento, sin las muy chicas', () => {
  const etiquetas = etiquetasDona([
    { nombre: 'Favorable', porcentaje: 50 },
    { nombre: 'En riesgo', porcentaje: 45 },
    { nombre: 'Sin mediciones', porcentaje: 5 },
  ])

  assert.deepEqual(etiquetas.map((e) => e.texto), ['50%', '45%'])
  assert.ok(Math.abs(etiquetas[0].x - 90) < 0.001 && Math.abs(etiquetas[0].y - 50) < 0.001)
})

test('evidencias: cuenta KPI (no archivos) y excluye las omisiones', () => {
  const mediciones = [
    { indicador: 1, tiene_evidencia: true, cierre_automatico: false },
    { indicador: 1, tiene_evidencia: true, cierre_automatico: false },
    { indicador: 2, tiene_evidencia: false, cierre_automatico: false },
    { indicador: 3, tiene_evidencia: true, cierre_automatico: true },
  ]

  assert.deepEqual(resumenEvidencias(kpis(3), mediciones), { con: 1, sin: 2, total: 3 })
  assert.equal(evidenciasPorKpi(mediciones).get(1), 2)
  assert.equal(porcentajeDe(1, 3), 33)
  assert.equal(porcentajeDe(0, 0), 0)
})

test('oportunidad: las omisiones se cuentan aparte de las mediciones registradas', () => {
  const mediciones = [
    { oportunidad_registro: 'A tiempo' },
    { oportunidad_registro: 'Con retraso' },
    { oportunidad_registro: 'Con retraso' },
    { oportunidad_registro: 'Con ampliación' },
    { oportunidad_registro: SIN_REGISTRO, cierre_automatico: true },
  ]

  assert.deepEqual(resumenOportunidad(mediciones, SIN_REGISTRO), {
    aTiempo: 1, conRetraso: 2, conAmpliacion: 1, sinRegistro: 1, registradas: 4, total: 5,
  })
  assert.deepEqual(ejeConteo(22), { tope: 24, marcas: [0, 6, 12, 18, 24] })
  assert.deepEqual(ejeConteo(0), { tope: 4, marcas: [0, 1, 2, 3, 4] })
  assert.equal(alturaConteo(2, 4), 50)
})

// ---------- Paginación de la tabla ----------

test('paginación con 0, 1, 8, 9 y muchos KPI', () => {
  const cero = paginar([], 1, 8)
  assert.deepEqual([cero.total, cero.pagina, cero.totalPaginas, cero.elementos.length, cero.hayAnterior, cero.haySiguiente], [0, 1, 1, 0, false, false])

  const uno = paginar(kpis(1), 1, 8)
  assert.deepEqual([uno.totalPaginas, uno.desde, uno.hasta, uno.haySiguiente], [1, 1, 1, false])

  const ocho = paginar(kpis(8), 1, 8)
  assert.deepEqual([ocho.totalPaginas, ocho.elementos.length, ocho.haySiguiente], [1, 8, false])

  const nueve = paginar(kpis(9), 2, 8)
  assert.deepEqual([nueve.totalPaginas, nueve.pagina, nueve.elementos.map((k) => k.id), nueve.hayAnterior, nueve.haySiguiente], [2, 2, [9], true, false])

  const muchos = paginar(kpis(45), 3, 8)
  assert.deepEqual([muchos.totalPaginas, muchos.desde, muchos.hasta, muchos.elementos[0].id], [6, 17, 24, 17])
})

test('si los resultados disminuyen, la página se ajusta y nunca queda vacía', () => {
  // Estaba en la página 5 de 45 KPI; un filtro deja 9.
  const ajustada = paginar(kpis(9), 5, 8)
  assert.deepEqual([ajustada.pagina, ajustada.elementos.length], [2, 1])

  assert.equal(paginar(kpis(9), 0, 8).pagina, 1)
  assert.equal(paginar(kpis(9), 'x', 8).pagina, 1)
})

test('cambiar año, plan estratégico o plan anual vuelve a la página 1', () => {
  assert.match(vista, /watch\(\s*\(\) => \[seleccion\.value\.anio, seleccion\.value\.planEstrategico, seleccion\.value\.planAnual\],\s*\(\) => \{\s*paginaTabla\.value = 1/)
  assert.match(vista, /const KPI_POR_PAGINA = 8/)
  assert.match(vista, /Página \{\{ tablaPaginada\.pagina \}\} de \{\{ tablaPaginada\.totalPaginas \}\}/)
  assert.match(vista, /:disabled="!tablaPaginada\.hayAnterior"/)
  assert.match(vista, /:disabled="!tablaPaginada\.haySiguiente"/)
  assert.match(vista, /KPI encontrados/)
})

// ---------- Estructura y navegación ----------

test('el Dashboard conserva los cinco bloques y la tabla de seis columnas', () => {
  for (const titulo of ['Cumplimiento de KPI', 'Estado actual de KPI', 'KPI con evidencias', 'Oportunidad de registro', 'Detalle de indicadores KPI']) {
    assert.match(vista, new RegExp(`\\s${titulo}\\s*</h2>`), titulo)
  }
  assert.equal(vista.match(/<h2>/g).length, 5)

  for (const retirado of ['Estado de KPI por plan estratégico', 'Evolución mensual', 'Alertas pendientes', 'Últimas mediciones']) {
    assert.doesNotMatch(vista, new RegExp(retirado), retirado)
  }

  const encabezados = [...vista.matchAll(/<th[^>]*>([^<]+)<\/th>/g)].map((m) => m[1].trim())
  assert.deepEqual(encabezados, ['Código', 'Nombre del indicador', 'Objetivo', 'Cumplimiento', 'Estado', 'Evidencias'])
})

test('KPI con evidencias: dos barras horizontales con la cantidad al extremo', () => {
  assert.match(vista, /class="barras-horizontales"/)
  assert.match(vista, /:style="\{ width: `\$\{barra\.ancho\}%` \}"/)
  assert.match(vista, /<span class="horizontal-valor">\{\{ barra\.cantidad \}\}<\/span>/)
  assert.match(vista, /nombre: 'Con evidencia'/)
  assert.match(vista, /nombre: 'Sin evidencia'/)
  // Ya no usa el eje vertical de conteos.
  assert.doesNotMatch(vista, /graficoEvidencias\.eje/)
  // El largo es la proporción de KPI: 2 de 8 => 25 %.
  assert.equal(alturaConteo(2, 8), 25)
  assert.equal(alturaConteo(0, 0), 0)
})

test('Oportunidad de registro conserva sus barras verticales', () => {
  assert.match(vista, /v-for="barra in graficoOportunidad\.barras"/)
  assert.match(vista, /const eje = ejeConteo\(Math\.max\(aTiempo, conRetraso, sinRegistro\)\)/)
})

test('Objetivo: texto resumido en una línea y completo en el title', () => {
  assert.match(vista, /<td class="celda-texto" :title="fila\.objetivo">\{\{ fila\.objetivo \}\}<\/td>/)
  assert.match(vista, /\.celda-texto\{[^}]*white-space:nowrap;[^}]*overflow:hidden;[^}]*text-overflow:ellipsis;/)
  assert.match(vista, /table\{[^}]*table-layout:fixed;/)
})

test('la fila y el nombre del KPI abren su detalle', () => {
  assert.match(vista, /class="fila-navegable"\s*@click="irAIndicador\(fila\.kpi\.id\)"/)
  assert.match(vista, /class="nombre-kpi"[^>]*@click\.stop="irAIndicador\(fila\.kpi\.id\)"/)
  assert.match(vista, /router\.push\(\{ path: '\/indicadores', query: \{ resaltar: id \} \}\)/)
  assert.match(vista, /aria-label="Año del plan anual"/)
})
