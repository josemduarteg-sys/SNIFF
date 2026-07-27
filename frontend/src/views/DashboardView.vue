<script setup>
import { computed } from 'vue'
import sniffLogo from '../assets/images/sniff-logo.png'

const props = defineProps({
  usuario: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['logout'])

const inicialesUsuario = computed(() => {
  const nombre = props.usuario?.username || 'Usuario'
  return nombre.slice(0, 2).toUpperCase()
})

function cerrarSesion() {
  emit('logout')
}
</script>

<template>
  <div class="dashboard-view">

  <!-- ===================== SIDEBAR ===================== -->
  <aside class="sidebar">
    <div class="sidebar-brand">
      <img :src="sniffLogo" alt="Sniff">
      <div class="wordmark">Sniff<span>.</span></div>
    </div>

    <nav class="nav-section">
      <div class="nav-label">General</div>
      <RouterLink to="/dashboard" class="nav-item active">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>
        <span>Dashboard</span>
      </RouterLink>

      <div class="nav-label" style="margin-top:14px;">Planeación</div>
      <RouterLink to="/estrategias" class="nav-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>
        <span>Estrategias</span>
      </RouterLink>
      <RouterLink to="/objetivos" class="nav-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21V4a1 1 0 0 1 1-1h9l4 4v3"/><path d="M4 14h8"/><path d="M4 21h9"/><circle cx="18" cy="16" r="4"/></svg>
        <span>Objetivos</span>
      </RouterLink>
      <RouterLink to="/indicadores" class="nav-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
        <span>Indicadores (KPI)</span>
      </RouterLink>
      <RouterLink to="/mediciones" class="nav-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 3v3h6V3"/><polyline points="8.5 13 11 15.5 15.5 10.5"/></svg>
        <span>Registro de Mediciones</span>
      </RouterLink>
      <RouterLink to="/dashboard" class="nav-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><path d="M9 3v15M15 6v15"/></svg>
        <span>Mapa Estratégico</span>
      </RouterLink>

      <div class="nav-label" style="margin-top:14px;">Sistema</div>
      <RouterLink to="/dashboard" class="nav-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        <span>Configuración</span>
      </RouterLink>
    </nav>

    <div class="sidebar-user">
      <div class="avatar-sm">{{ inicialesUsuario }}</div>
      <div>
        <div class="name">{{ usuario?.username || 'Usuario' }}</div>
        <div class="role">{{ usuario?.rol_nombre || 'Sin rol' }}</div>
      </div>
    </div>
  </aside>

  <!-- ===================== MAIN AREA ===================== -->
  <div class="main-area">

    <header class="topbar">
      <div class="breadcrumb">
        <span>Sniff</span>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        <span class="current">Dashboard</span>
      </div>

      <div class="topbar-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" placeholder="Buscar objetivos, indicadores...">
      </div>

      <div class="topbar-actions">
        <div class="icon-btn">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          <span class="dot"></span>
        </div>
        <button class="topbar-profile" type="button" @click="cerrarSesion" title="Cerrar sesión">
          <div class="avatar-sm">{{ inicialesUsuario }}</div>
          <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
      </div>
    </header>

    <main class="content">

      <div class="page-header">
        <div>
          <h1>Dashboard Principal</h1>
          <div class="subtitle">Resumen general del cumplimiento estratégico</div>
        </div>
        <div class="period-select">
          <svg class="cal" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          Segundo Trimestre 2026
          <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
      </div>

      <!-- ================= SUMMARY CARDS ================= -->
      <section class="summary-grid">

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon navy">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            </div>
            <div class="kpi-trend up">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
              +4%
            </div>
          </div>
          <div class="kpi-value">82%</div>
          <div class="kpi-label">Cumplimiento general</div>
          <div class="progress-track"><div class="progress-fill" style="width:82%;"></div></div>
          <div class="kpi-foot">Meta del periodo: 90%</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon steel">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>
            </div>
          </div>
          <div class="kpi-value">5</div>
          <div class="kpi-label">Estrategias activas</div>
          <div class="kpi-foot" style="margin-top:22px;">De 5 estrategias registradas</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon aqua">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21V4a1 1 0 0 1 1-1h9l4 4v3"/><path d="M4 14h8"/><path d="M4 21h9"/><circle cx="18" cy="16" r="4"/></svg>
            </div>
          </div>
          <div class="kpi-value">18</div>
          <div class="kpi-label">Objetivos registrados</div>
          <div class="kpi-foot" style="margin-top:22px;">Distribuidos en 5 estrategias</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon steel">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
          </div>
          <div class="kpi-value">34</div>
          <div class="kpi-label">KPI activos</div>
          <div class="kpi-foot" style="margin-top:22px;">En seguimiento este trimestre</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon danger">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>
            <div class="kpi-trend down">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>
              +2
            </div>
          </div>
          <div class="kpi-value">6</div>
          <div class="kpi-label">Indicadores en riesgo</div>
          <div class="kpi-foot">Requieren atención inmediata</div>
        </div>

      </section>

      <!-- ================= CHARTS ================= -->
      <section class="charts-grid">

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Cumplimiento por estrategia</h2>
              <div class="desc">Porcentaje alcanzado frente a la meta del trimestre</div>
            </div>
            <div class="panel-tag">Q2 2026</div>
          </div>

          <div class="bar-chart">
            <div class="bar-col">
              <div class="bar-val">92%</div>
              <div class="bar-shape" style="height:150px; background:var(--success);"></div>
              <div class="bar-name">Crecimiento de Cartera</div>
            </div>
            <div class="bar-col">
              <div class="bar-val">85%</div>
              <div class="bar-shape" style="height:138px; background:var(--success);"></div>
              <div class="bar-name">Satisfacción del Socio</div>
            </div>
            <div class="bar-col">
              <div class="bar-val">78%</div>
              <div class="bar-shape" style="height:126px; background:var(--orange);"></div>
              <div class="bar-name">Eficiencia Operativa</div>
            </div>
            <div class="bar-col">
              <div class="bar-val">88%</div>
              <div class="bar-shape" style="height:143px; background:var(--success);"></div>
              <div class="bar-name">Solidez Financiera</div>
            </div>
            <div class="bar-col">
              <div class="bar-val">64%</div>
              <div class="bar-shape" style="height:104px; background:var(--danger);"></div>
              <div class="bar-name">Innovación Digital</div>
            </div>
          </div>

          <div class="chart-legend">
            <div class="legend-item"><span class="legend-dot" style="background:var(--success);"></span>En meta (≥85%)</div>
            <div class="legend-item"><span class="legend-dot" style="background:var(--orange);"></span>En riesgo (70–84%)</div>
            <div class="legend-item"><span class="legend-dot" style="background:var(--danger);"></span>Crítico (&lt;70%)</div>
          </div>
        </div>

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Evolución de mediciones</h2>
              <div class="desc">Cumplimiento general promedio, últimos 6 meses</div>
            </div>
          </div>

          <div class="line-chart-wrap">
            <svg viewBox="0 0 320 190" width="100%" height="190" preserveAspectRatio="none">
              <line x1="0" y1="10" x2="320" y2="10" stroke="#EEF2F5" stroke-width="1"/>
              <line x1="0" y1="55" x2="320" y2="55" stroke="#EEF2F5" stroke-width="1"/>
              <line x1="0" y1="100" x2="320" y2="100" stroke="#EEF2F5" stroke-width="1"/>
              <line x1="0" y1="145" x2="320" y2="145" stroke="#EEF2F5" stroke-width="1"/>

              <defs>
                <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#A8DADC" stop-opacity="0.55"/>
                  <stop offset="100%" stop-color="#A8DADC" stop-opacity="0"/>
                </linearGradient>
              </defs>

              <path d="M10,120 L64,109 L118,100 L172,88 L226,75 L280,55 L280,180 L10,180 Z" fill="url(#areaFill)"/>
              <polyline points="10,120 64,109 118,100 172,88 226,75 280,55" fill="none" stroke="var(--navy)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>

              <circle cx="10" cy="120" r="4" fill="var(--white)" stroke="var(--steel)" stroke-width="2.4"/>
              <circle cx="64" cy="109" r="4" fill="var(--white)" stroke="var(--steel)" stroke-width="2.4"/>
              <circle cx="118" cy="100" r="4" fill="var(--white)" stroke="var(--steel)" stroke-width="2.4"/>
              <circle cx="172" cy="88" r="4" fill="var(--white)" stroke="var(--steel)" stroke-width="2.4"/>
              <circle cx="226" cy="75" r="4" fill="var(--white)" stroke="var(--steel)" stroke-width="2.4"/>
              <circle cx="280" cy="55" r="5.5" fill="var(--navy)" stroke="var(--white)" stroke-width="2"/>
            </svg>
          </div>
          <div class="line-chart-foot">
            <span>Ene</span><span>Feb</span><span>Mar</span><span>Abr</span><span>May</span><span>Jun</span>
          </div>
        </div>

      </section>

      <!-- ================= TABLE ================= -->
      <section class="card-panel table-card">
        <div class="panel-head">
          <div>
            <h2>Indicadores con menor cumplimiento</h2>
            <div class="desc">Los 5 KPI que más se alejan de su meta este trimestre</div>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Indicador</th>
              <th>Meta</th>
              <th>Actual</th>
              <th>Cumplimiento</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <div class="cell-main">Tasa de morosidad</div>
                <div class="cell-sub">Solidez Financiera</div>
              </td>
              <td>≤ 5.0%</td>
              <td>8.4%</td>
              <td>
                <div class="mini-progress"><div class="track"><div class="fill" style="width:52%; background:var(--danger);"></div></div><span class="pct">52%</span></div>
              </td>
              <td><span class="badge critical"><span class="badge-dot"></span>Crítico</span></td>
            </tr>
            <tr>
              <td>
                <div class="cell-main">Adopción de banca digital</div>
                <div class="cell-sub">Innovación Digital</div>
              </td>
              <td>60%</td>
              <td>39%</td>
              <td>
                <div class="mini-progress"><div class="track"><div class="fill" style="width:65%; background:var(--orange);"></div></div><span class="pct">65%</span></div>
              </td>
              <td><span class="badge warning"><span class="badge-dot"></span>En riesgo</span></td>
            </tr>
            <tr>
              <td>
                <div class="cell-main">Tiempo de resolución de PQR</div>
                <div class="cell-sub">Satisfacción del Socio</div>
              </td>
              <td>24 h</td>
              <td>34 h</td>
              <td>
                <div class="mini-progress"><div class="track"><div class="fill" style="width:70%; background:var(--orange);"></div></div><span class="pct">70%</span></div>
              </td>
              <td><span class="badge warning"><span class="badge-dot"></span>En riesgo</span></td>
            </tr>
            <tr>
              <td>
                <div class="cell-main">Costo de servicio por socio</div>
                <div class="cell-sub">Eficiencia Operativa</div>
              </td>
              <td>Q 450</td>
              <td>Q 510</td>
              <td>
                <div class="mini-progress"><div class="track"><div class="fill" style="width:74%; background:var(--orange);"></div></div><span class="pct">74%</span></div>
              </td>
              <td><span class="badge warning"><span class="badge-dot"></span>En riesgo</span></td>
            </tr>
            <tr>
              <td>
                <div class="cell-main">Nuevos créditos colocados</div>
                <div class="cell-sub">Crecimiento de Cartera</div>
              </td>
              <td>1,200</td>
              <td>980</td>
              <td>
                <div class="mini-progress"><div class="track"><div class="fill" style="width:81%; background:var(--orange);"></div></div><span class="pct">81%</span></div>
              </td>
              <td><span class="badge warning"><span class="badge-dot"></span>En riesgo</span></td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ================= BOTTOM: ALERTS + MEASUREMENTS ================= -->
      <section class="bottom-grid">

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Alertas recientes</h2>
              <div class="desc">Eventos que requieren revisión</div>
            </div>
          </div>

          <div class="alert-item">
            <div class="alert-icon critical">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>
            <div>
              <div class="alert-text">"Tasa de morosidad" superó el umbral crítico definido</div>
              <div class="alert-time">Hace 2 horas</div>
            </div>
          </div>

          <div class="alert-item">
            <div class="alert-icon warning">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>
            <div>
              <div class="alert-text">"Adopción de banca digital" por debajo de la meta trimestral</div>
              <div class="alert-time">Hace 5 horas</div>
            </div>
          </div>

          <div class="alert-item">
            <div class="alert-icon warning">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            </div>
            <div>
              <div class="alert-text">3 indicadores sin medición registrada esta semana</div>
              <div class="alert-time">Hace 1 día</div>
            </div>
          </div>

          <div class="alert-item">
            <div class="alert-icon info">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            </div>
            <div>
              <div class="alert-text">Meta de "Crecimiento de Cartera" actualizada por Ana Martínez</div>
              <div class="alert-time">Hace 2 días</div>
            </div>
          </div>

          <div class="link-see-all">Ver todas las alertas</div>
        </div>

        <div class="card-panel">
          <div class="panel-head">
            <div>
              <h2>Últimas mediciones registradas</h2>
              <div class="desc">Cargas más recientes al sistema</div>
            </div>
          </div>

          <div class="meas-item">
            <div class="meas-left">
              <div class="meas-avatar">CP</div>
              <div>
                <div class="meas-name">Cumplimiento general de cartera</div>
                <div class="meas-sub">Carlos Pérez · 30 jun 2026</div>
              </div>
            </div>
            <div class="meas-value">92%</div>
          </div>

          <div class="meas-item">
            <div class="meas-left">
              <div class="meas-avatar">LR</div>
              <div>
                <div class="meas-name">Satisfacción del socio (NPS)</div>
                <div class="meas-sub">Lucía Ramírez · 29 jun 2026</div>
              </div>
            </div>
            <div class="meas-value">85%</div>
          </div>

          <div class="meas-item">
            <div class="meas-left">
              <div class="meas-avatar">CP</div>
              <div>
                <div class="meas-name">Tasa de morosidad</div>
                <div class="meas-sub">Carlos Pérez · 29 jun 2026</div>
              </div>
            </div>
            <div class="meas-value">8.4%</div>
          </div>

          <div class="meas-item">
            <div class="meas-left">
              <div class="meas-avatar">AM</div>
              <div>
                <div class="meas-name">Costo de servicio por socio</div>
                <div class="meas-sub">Ana Martínez · 28 jun 2026</div>
              </div>
            </div>
            <div class="meas-value">Q 510</div>
          </div>

          <div class="meas-item">
            <div class="meas-left">
              <div class="meas-avatar">DS</div>
              <div>
                <div class="meas-name">Adopción de banca digital</div>
                <div class="meas-sub">Diego Solís · 27 jun 2026</div>
              </div>
            </div>
            <div class="meas-value">39%</div>
          </div>

          <div class="link-see-all">Ver todas las mediciones</div>
        </div>

      </section>

    </main>
  </div>

  </div>
</template>

<style scoped>
  .dashboard-view{
    --navy:#1D3557;
    --navy-dark:#152840;
    --steel:#457B9D;
    --aqua:#A8DADC;
    --aqua-soft:#EAF5F5;
    --orange:#F4A261;
    --success:#2A9D8F;
    --danger:#E76F51;
    --bg:#F6F9FA;
    --white:#FFFFFF;
    --text-secondary:#5E6E82;
    --text-muted:#9AA8B8;
    --border:#E4EAEF;
    --radius-lg:20px;
    --radius-md:14px;
    --radius-sm:10px;
    --shadow-card: 0 2px 10px rgba(29,53,87,0.05), 0 1px 2px rgba(29,53,87,0.04);
    --shadow-hover: 0 10px 26px rgba(29,53,87,0.10);
    --sidebar-w:264px;
  }
  .dashboard-view *{ box-sizing:border-box; margin:0; padding:0; }
  .dashboard-view{
    font-family:'Montserrat', sans-serif;
    background:var(--bg);
    color:var(--navy);
    -webkit-font-smoothing:antialiased;
  }
  .dashboard-view a{ color:inherit; text-decoration:none; }
  .dashboard-view button{ font-family:inherit; }

  /* ===================== SIDEBAR ===================== */
  .sidebar{
    position:fixed;
    top:0; left:0; bottom:0;
    width:var(--sidebar-w);
    background:var(--white);
    border-right:1px solid var(--border);
    display:flex;
    flex-direction:column;
    z-index:20;
  }

  .sidebar-brand{
    display:flex;
    align-items:center;
    gap:11px;
    padding:22px 22px 20px;
    border-bottom:1px solid var(--border);
  }
  .sidebar-brand img{
    width:38px; height:38px; border-radius:10px; display:block;
  }
  .sidebar-brand .wordmark{
    font-weight:800;
    font-size:19px;
    letter-spacing:-0.4px;
    color:var(--navy);
  }
  .sidebar-brand .wordmark span{ color:var(--steel); }

  .nav-section{
    padding:18px 14px;
    flex:1;
    overflow-y:auto;
  }
  .nav-label{
    font-size:10.5px;
    font-weight:700;
    letter-spacing:1.2px;
    text-transform:uppercase;
    color:var(--text-muted);
    padding:6px 12px 10px;
  }
  .nav-item{
    display:flex;
    align-items:center;
    gap:11px;
    padding:10px 12px;
    border-radius:var(--radius-sm);
    font-size:13.5px;
    font-weight:600;
    color:var(--text-secondary);
    margin-bottom:2px;
    cursor:pointer;
    transition:background .15s ease, color .15s ease;
  }
  .nav-item svg{ flex-shrink:0; opacity:0.85; }
  .nav-item:hover{ background:#F4F8F9; color:var(--navy); }
  .nav-item.active{
    background:var(--navy);
    color:var(--white);
  }
  .nav-item.active svg{ opacity:1; }

  .sidebar-user{
    display:flex;
    align-items:center;
    gap:10px;
    padding:16px 20px;
    border-top:1px solid var(--border);
  }
  .avatar-sm{
    width:36px; height:36px; border-radius:10px;
    background:var(--aqua-soft);
    color:var(--steel);
    display:flex; align-items:center; justify-content:center;
    font-weight:700; font-size:13px;
    flex-shrink:0;
  }
  .sidebar-user .name{ font-size:13px; font-weight:700; color:var(--navy); line-height:1.3; }
  .sidebar-user .role{ font-size:11px; color:var(--text-muted); font-weight:500; }

  /* ===================== MAIN AREA ===================== */
  .main-area{
    margin-left:var(--sidebar-w);
    min-height:100vh;
    display:flex;
    flex-direction:column;
  }

  /* ---- topbar ---- */
  .topbar{
    position:sticky;
    top:0;
    z-index:10;
    height:66px;
    background:var(--white);
    border-bottom:1px solid var(--border);
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:0 28px;
    gap:20px;
  }
  .breadcrumb{
    font-size:13px;
    font-weight:600;
    color:var(--text-muted);
    display:flex;
    align-items:center;
    gap:6px;
    white-space:nowrap;
  }
  .breadcrumb .current{ color:var(--navy); }

  .topbar-search{
    flex:1;
    max-width:380px;
    position:relative;
  }
  .topbar-search svg{
    position:absolute; left:13px; top:50%; transform:translateY(-50%);
    color:var(--text-muted);
  }
  .topbar-search input{
    width:100%;
    height:38px;
    border-radius:10px;
    border:1.5px solid var(--border);
    background:var(--bg);
    padding:0 14px 0 38px;
    font-family:inherit;
    font-size:13px;
    color:var(--navy);
    outline:none;
    transition:border-color .15s ease, background .15s ease;
  }
  .topbar-search input::placeholder{ color:var(--text-muted); }
  .topbar-search input:focus{ border-color:var(--steel); background:var(--white); }

  .topbar-actions{
    display:flex;
    align-items:center;
    gap:14px;
    flex-shrink:0;
  }
  .icon-btn{
    width:38px; height:38px;
    border-radius:10px;
    border:1.5px solid var(--border);
    background:var(--white);
    display:flex; align-items:center; justify-content:center;
    color:var(--text-secondary);
    cursor:pointer;
    position:relative;
    transition:background .15s ease, border-color .15s ease;
  }
  .icon-btn:hover{ background:var(--bg); border-color:var(--steel); color:var(--steel); }
  .icon-btn .dot{
    position:absolute; top:8px; right:8px;
    width:7px; height:7px; border-radius:50%;
    background:var(--orange);
    border:1.5px solid var(--white);
  }
  .topbar-profile{
    display:flex; align-items:center; gap:9px;
    padding:5px 6px 5px 5px;
    border-radius:10px;
    cursor:pointer;
    transition:background .15s ease;
  }
  .topbar-profile:hover{ background:var(--bg); }
  .topbar-profile .chev{ color:var(--text-muted); }

  /* ---- content ---- */
  .content{
    padding:28px 32px 40px;
    max-width:1400px;
    width:100%;
  }

  .page-header{
    display:flex;
    align-items:flex-end;
    justify-content:space-between;
    flex-wrap:wrap;
    gap:16px;
    margin-bottom:24px;
  }
  .page-header h1{
    font-size:23px;
    font-weight:800;
    letter-spacing:-0.3px;
    color:var(--navy);
  }
  .page-header .subtitle{
    font-size:13px;
    color:var(--text-muted);
    font-weight:500;
    margin-top:4px;
  }

  .period-select{
    display:flex;
    align-items:center;
    gap:8px;
    height:40px;
    padding:0 14px;
    border-radius:10px;
    border:1.5px solid var(--border);
    background:var(--white);
    font-size:13px;
    font-weight:600;
    color:var(--navy);
    cursor:pointer;
    box-shadow:var(--shadow-card);
  }
  .period-select svg.cal{ color:var(--steel); }
  .period-select svg.chev{ color:var(--text-muted); }

  /* ---- summary cards ---- */
  .summary-grid{
    display:grid;
    grid-template-columns:repeat(5, 1fr);
    gap:16px;
    margin-bottom:24px;
  }
  .kpi-card{
    background:var(--white);
    border:1px solid var(--border);
    border-radius:var(--radius-md);
    padding:18px 18px 16px;
    box-shadow:var(--shadow-card);
    transition:box-shadow .15s ease, transform .15s ease;
  }
  .kpi-card:hover{ box-shadow:var(--shadow-hover); transform:translateY(-2px); }

  .kpi-top{
    display:flex;
    align-items:center;
    justify-content:space-between;
    margin-bottom:14px;
  }
  .kpi-icon{
    width:34px; height:34px;
    border-radius:9px;
    display:flex; align-items:center; justify-content:center;
  }
  .kpi-icon.navy{ background:rgba(29,53,87,0.08); color:var(--navy); }
  .kpi-icon.steel{ background:rgba(69,123,157,0.10); color:var(--steel); }
  .kpi-icon.aqua{ background:var(--aqua-soft); color:var(--steel); }
  .kpi-icon.orange{ background:rgba(244,162,97,0.14); color:var(--orange); }
  .kpi-icon.danger{ background:rgba(231,111,81,0.12); color:var(--danger); }

  .kpi-trend{
    font-size:11px;
    font-weight:700;
    display:flex;
    align-items:center;
    gap:3px;
  }
  .kpi-trend.up{ color:var(--success); }
  .kpi-trend.down{ color:var(--danger); }

  .kpi-value{
    font-size:26px;
    font-weight:800;
    color:var(--navy);
    letter-spacing:-0.4px;
    line-height:1;
    margin-bottom:6px;
  }
  .kpi-label{
    font-size:12.5px;
    font-weight:600;
    color:var(--text-secondary);
    margin-bottom:12px;
  }

  .progress-track{
    width:100%; height:6px;
    background:#EEF2F5;
    border-radius:6px;
    overflow:hidden;
  }
  .progress-fill{
    height:100%;
    border-radius:6px;
    background:linear-gradient(90deg, var(--steel), var(--navy));
  }
  .kpi-foot{
    font-size:11px;
    color:var(--text-muted);
    font-weight:500;
    margin-top:8px;
  }

  /* ---- section titles ---- */
  .card-panel{
    background:var(--white);
    border:1px solid var(--border);
    border-radius:var(--radius-md);
    box-shadow:var(--shadow-card);
    padding:20px 22px 22px;
  }
  .panel-head{
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    margin-bottom:18px;
    gap:12px;
  }
  .panel-head h2{
    font-size:14.5px;
    font-weight:700;
    color:var(--navy);
  }
  .panel-head .desc{
    font-size:11.5px;
    color:var(--text-muted);
    font-weight:500;
    margin-top:3px;
  }
  .panel-tag{
    font-size:10.5px;
    font-weight:700;
    padding:5px 10px;
    border-radius:20px;
    background:var(--aqua-soft);
    color:var(--steel);
    white-space:nowrap;
  }

  /* ---- charts row ---- */
  .charts-grid{
    display:grid;
    grid-template-columns:1.3fr 1fr;
    gap:18px;
    margin-bottom:20px;
    align-items:stretch;
  }

  .bar-chart{ display:flex; align-items:flex-end; gap:22px; height:210px; padding-top:6px; }
  .bar-col{ flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; }
  .bar-val{ font-size:12px; font-weight:700; color:var(--navy); margin-bottom:6px; }
  .bar-shape{ width:100%; max-width:38px; border-radius:8px 8px 4px 4px; }
  .bar-name{ font-size:10.5px; font-weight:600; color:var(--text-muted); margin-top:10px; text-align:center; line-height:1.3; }

  .chart-legend{ display:flex; gap:16px; margin-top:16px; flex-wrap:wrap; }
  .legend-item{ display:flex; align-items:center; gap:6px; font-size:11px; font-weight:600; color:var(--text-secondary); }
  .legend-dot{ width:8px; height:8px; border-radius:50%; }

  .line-chart-wrap{ position:relative; }
  .line-chart-foot{ display:flex; justify-content:space-between; margin-top:8px; padding:0 4px; }
  .line-chart-foot span{ font-size:10.5px; font-weight:600; color:var(--text-muted); }

  /* ---- table ---- */
  .table-card{ margin-bottom:20px; }
  table{ width:100%; border-collapse:collapse; }
  thead th{
    text-align:left;
    font-size:10.5px;
    font-weight:700;
    letter-spacing:0.5px;
    text-transform:uppercase;
    color:var(--text-muted);
    padding:0 12px 10px;
    border-bottom:1px solid var(--border);
  }
  tbody td{
    padding:13px 12px;
    font-size:13px;
    color:var(--navy);
    border-bottom:1px solid #F1F4F7;
    vertical-align:middle;
  }
  tbody tr:last-child td{ border-bottom:none; }
  tbody tr{ transition:background .12s ease; }
  tbody tr:hover{ background:#FAFCFD; }

  .cell-main{ font-weight:700; font-size:13px; color:var(--navy); }
  .cell-sub{ font-size:11.5px; color:var(--text-muted); font-weight:500; margin-top:2px; }

  .badge{
    display:inline-flex;
    align-items:center;
    gap:5px;
    font-size:11px;
    font-weight:700;
    padding:4px 10px;
    border-radius:20px;
    white-space:nowrap;
  }
  .badge.critical{ background:rgba(231,111,81,0.12); color:var(--danger); }
  .badge.warning{ background:rgba(244,162,97,0.16); color:#B9701E; }
  .badge.ok{ background:rgba(42,157,143,0.12); color:var(--success); }
  .badge-dot{ width:6px; height:6px; border-radius:50%; background:currentColor; }

  .mini-progress{ display:flex; align-items:center; gap:8px; }
  .mini-progress .track{ width:80px; height:6px; background:#EEF2F5; border-radius:6px; overflow:hidden; }
  .mini-progress .fill{ height:100%; border-radius:6px; }
  .mini-progress .pct{ font-size:12px; font-weight:700; color:var(--navy); width:34px; }

  /* ---- bottom grid ---- */
  .bottom-grid{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:18px;
  }

  .alert-item{
    display:flex;
    gap:12px;
    padding:12px 4px;
    border-bottom:1px solid #F1F4F7;
  }
  .alert-item:last-child{ border-bottom:none; padding-bottom:0; }
  .alert-icon{
    width:32px; height:32px; border-radius:9px;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0;
  }
  .alert-icon.critical{ background:rgba(231,111,81,0.12); color:var(--danger); }
  .alert-icon.warning{ background:rgba(244,162,97,0.16); color:#B9701E; }
  .alert-icon.info{ background:rgba(69,123,157,0.10); color:var(--steel); }
  .alert-text{ font-size:12.5px; font-weight:600; color:var(--navy); line-height:1.4; }
  .alert-time{ font-size:11px; color:var(--text-muted); font-weight:500; margin-top:3px; }

  .meas-item{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    padding:12px 4px;
    border-bottom:1px solid #F1F4F7;
  }
  .meas-item:last-child{ border-bottom:none; padding-bottom:0; }
  .meas-left{ display:flex; align-items:center; gap:11px; min-width:0; }
  .meas-avatar{
    width:30px; height:30px; border-radius:9px;
    background:var(--aqua-soft); color:var(--steel);
    display:flex; align-items:center; justify-content:center;
    font-size:11px; font-weight:700; flex-shrink:0;
  }
  .meas-name{ font-size:12.5px; font-weight:700; color:var(--navy); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .meas-sub{ font-size:11px; color:var(--text-muted); font-weight:500; margin-top:1px; }
  .meas-value{ font-size:13px; font-weight:800; color:var(--navy); white-space:nowrap; }

  .link-see-all{
    display:block;
    text-align:center;
    font-size:12px;
    font-weight:700;
    color:var(--steel);
    padding-top:14px;
    cursor:pointer;
  }
  .link-see-all:hover{ color:var(--navy); }

  /* ===================== RESPONSIVE ===================== */
  @media (max-width:1180px){
    .summary-grid{ grid-template-columns:repeat(3, 1fr); }
    .charts-grid{ grid-template-columns:1fr; }
  }
  @media (max-width:900px){
    .summary-grid{ grid-template-columns:repeat(2, 1fr); }
    .bottom-grid{ grid-template-columns:1fr; }
    .topbar-search{ display:none; }
  }
  @media (max-width:760px){
    .dashboard-view{ --sidebar-w:76px; }
    .sidebar-brand .wordmark, .nav-label, .nav-item span, .sidebar-user .name, .sidebar-user .role{ display:none; }
    .sidebar-brand{ justify-content:center; padding:20px 0; }
    .nav-item{ justify-content:center; }
    .sidebar-user{ justify-content:center; }
    .summary-grid{ grid-template-columns:repeat(2, 1fr); }
    .content{ padding:20px 16px 32px; }
  }


  .topbar-profile {
    border: none;
    background: transparent;
    font-family: inherit;
  }

</style>
