import { createRouter, createWebHistory } from 'vue-router'
import { debeCambiarPassword, estaAutenticado } from '../services/authService'

import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import PlanesEstrategicosView from '../views/PlanesEstrategicosView.vue'
import ObjetivosGeneralesView from '../views/ObjetivosGeneralesView.vue'
import PlanesAnualesView from '../views/PlanesAnualesView.vue'
import ObjetivosEspecificosView from '../views/ObjetivosEspecificosView.vue'
import IndicadoresView from '../views/IndicadoresView.vue'
import MedicionesView from '../views/MedicionesView.vue'
import ConfiguracionView from '../views/ConfiguracionView.vue'
import AreasView from '../views/AreasView.vue'
import UsuariosView from '../views/UsuariosView.vue'
import CambioPasswordObligatorioView from '../views/CambioPasswordObligatorioView.vue'
import BitacoraView from '../views/BitacoraView.vue'

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
    path: '/planes-estrategicos',
    name: 'planes-estrategicos',
    component: PlanesEstrategicosView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/objetivos-generales',
    name: 'objetivos-generales',
    component: ObjetivosGeneralesView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/planes-anuales',
    name: 'planes-anuales',
    component: PlanesAnualesView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/objetivos-especificos',
    name: 'objetivos-especificos',
    component: ObjetivosEspecificosView,
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
  {
    path: '/areas',
    name: 'areas',
    component: AreasView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/usuarios',
    name: 'usuarios',
    component: UsuariosView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/cambio-password-obligatorio',
    name: 'cambio-password-obligatorio',
    component: CambioPasswordObligatorioView,
    meta: {
      requiresAuth: true,
      permitePasswordTemporal: true,
    },
  },
  {
    path: '/bitacora',
    name: 'bitacora',
    component: BitacoraView,
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

  if (autenticado && debeCambiarPassword()) {
    if (!to.meta.permitePasswordTemporal) {
      return '/cambio-password-obligatorio'
    }

    return true
  }

  if (to.path === '/login' && autenticado) {
    return '/dashboard'
  }

  if (to.path === '/cambio-password-obligatorio' && autenticado) {
    return '/dashboard'
  }

  return true
})

export default router