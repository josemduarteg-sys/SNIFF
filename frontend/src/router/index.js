import { createRouter, createWebHistory } from 'vue-router'
import { estaAutenticado } from '../services/authService'

import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import EstrategiasView from '../views/EstrategiasView.vue'
import ObjetivosView from '../views/ObjetivosView.vue'
import IndicadoresView from '../views/IndicadoresView.vue'
import MedicionesView from '../views/MedicionesView.vue'
import ConfiguracionView from '../views/ConfiguracionView.vue'

const routes = [
  {
    path: '/',
    redirect: () => {
      return estaAutenticado() ? '/dashboard' : '/login'
    },
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: {
      public: true,
    },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/estrategias',
    name: 'estrategias',
    component: EstrategiasView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/objetivos',
    name: 'objetivos',
    component: ObjetivosView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/indicadores',
    name: 'indicadores',
    component: IndicadoresView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/mediciones',
    name: 'mediciones',
    component: MedicionesView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/configuracion',
    name: 'configuracion',
    component: ConfiguracionView,
    meta: {
      requiresAuth: true,
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const autenticado = estaAutenticado()

  if (to.meta.requiresAuth && !autenticado) {
    return '/login'
  }

  if (to.path === '/login' && autenticado) {
    return '/dashboard'
  }

  return true
})

export default router