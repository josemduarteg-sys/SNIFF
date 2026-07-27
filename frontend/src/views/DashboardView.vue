<script setup>
defineProps({
  usuario: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['logout'])

function cerrarSesion() {
  emit('logout')
}
</script>

<template>
  <div class="dashboard-page">
    <aside class="sidebar">
      <div class="brand">
        <img src="../assets/images/sniff-logo.png" alt="Sniff" />
        <div>
          <h2>Sniff</h2>
          <p>Monitoreo Estratégico</p>
        </div>
      </div>

      <nav class="menu">
        <a class="active" href="#">Dashboard</a>
        <a href="#">Estrategias</a>
        <a href="#">Objetivos</a>
        <a href="#">Indicadores KPI</a>
        <a href="#">Mediciones</a>
        <a href="#">Alertas</a>
        <a href="#">Reportes</a>
        <a href="#">Usuarios</a>
      </nav>
    </aside>

    <main class="content">
      <header class="topbar">
        <div>
          <h1>Dashboard</h1>
          <p>Panel general de seguimiento estratégico e indicadores KPI.</p>
        </div>

        <div class="user-box">
          <div>
            <strong>{{ usuario.username }}</strong>
            <span>{{ usuario.rol_nombre }}</span>
          </div>

          <button @click="cerrarSesion">
            Cerrar sesión
          </button>
        </div>
      </header>

      <section class="cards">
        <article class="card">
          <span>Estrategias</span>
          <strong>0</strong>
          <p>Registradas en el sistema</p>
        </article>

        <article class="card">
          <span>Indicadores KPI</span>
          <strong>0</strong>
          <p>Indicadores activos</p>
        </article>

        <article class="card">
          <span>Mediciones</span>
          <strong>0</strong>
          <p>Mediciones recientes</p>
        </article>

        <article class="card alert">
          <span>Alertas</span>
          <strong>0</strong>
          <p>Pendientes de revisión</p>
        </article>
      </section>

      <section class="panel">
        <h2>Bienvenido, {{ usuario.username }}</h2>
        <p>
          El inicio de sesión ya funciona con JWT. Este dashboard es temporal;
          después conectaremos las tarjetas con los datos reales de la API.
        </p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  display: flex;
  background: #f6f9fa;
  color: #1d3557;
  font-family: 'Montserrat', Arial, sans-serif;
}

.sidebar {
  width: 270px;
  background: #1d3557;
  color: white;
  padding: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 36px;
}

.brand img {
  width: 48px;
  height: 48px;
  border-radius: 12px;
}

.brand h2 {
  margin: 0;
  font-size: 22px;
}

.brand p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #a8dadc;
}

.menu {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.menu a {
  color: #d8e6ef;
  text-decoration: none;
  padding: 12px 14px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 14px;
}

.menu a:hover,
.menu a.active {
  background: rgba(168, 218, 220, 0.15);
  color: white;
}

.content {
  flex: 1;
  padding: 30px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}

.topbar h1 {
  margin: 0;
  font-size: 30px;
}

.topbar p {
  margin: 6px 0 0;
  color: #6b7a8f;
}

.user-box {
  display: flex;
  align-items: center;
  gap: 16px;
  background: white;
  padding: 12px 14px;
  border-radius: 14px;
  box-shadow: 0 8px 20px rgba(29, 53, 87, 0.08);
}

.user-box div {
  display: flex;
  flex-direction: column;
  text-align: right;
}

.user-box span {
  color: #6b7a8f;
  font-size: 12px;
}

.user-box button {
  border: none;
  background: #1d3557;
  color: white;
  border-radius: 10px;
  padding: 9px 12px;
  cursor: pointer;
  font-weight: 700;
}

.cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 18px;
  margin-bottom: 24px;
}

.card,
.panel {
  background: white;
  border-radius: 18px;
  padding: 22px;
  box-shadow: 0 10px 25px rgba(29, 53, 87, 0.08);
}

.card span {
  color: #457b9d;
  font-weight: 700;
  font-size: 13px;
}

.card strong {
  display: block;
  margin-top: 12px;
  font-size: 34px;
}

.card p,
.panel p {
  color: #6b7a8f;
  margin-bottom: 0;
}

.card.alert strong {
  color: #f4a261;
}

.panel h2 {
  margin-top: 0;
}

@media (max-width: 900px) {
  .dashboard-page {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
  }

  .cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>