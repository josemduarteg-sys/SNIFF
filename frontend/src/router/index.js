import { createRouter, createWebHistory } from 'vue-router'
import { debeCambiarPassword, estaAutenticado, obtenerRolAlmacenado } from '../services/authService'
import { esAdministradorPlanificacion, esAdministradorSistema } from '../utils/permisos'

import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import PlanesEstrategicosView from '../views/PlanesEstrategicosView.vue'
import ObjetivosGeneralesView from '../views/ObjetivosGeneralesView.vue'
import PlanesAnualesView from '../views/PlanesAnualesView.vue'
import IndicadoresView from '../views/IndicadoresView.vue'
import MedicionesView from '../views/MedicionesView.vue'
import ConfiguracionView from '../views/ConfiguracionView.vue'
import AreasView from '../views/AreasView.vue'
import UsuariosView from '../views/UsuariosView.vue'
import CambioPasswordObligatorioView from '../views/CambioPasswordObligatorioView.vue'
import BitacoraView from '../views/BitacoraView.vue'
import MapaEstrategicoView from '../views/MapaEstrategicoView.vue'

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
    // Deshabilitada temporalmente (pedido de Hernán, 06/10/2026): un enlace
    // o una URL guardada lleva a Indicadores. ObjetivosEspecificosView.vue y
    // la API se conservan para poder reactivarla.
    path: '/objetivos-especificos',
    redirect: '/indicadores',
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
      verificarAcceso: esAdministradorPlanificacion,
    },
  },
  {
    path: '/usuarios',
    name: 'usuarios',
    component: UsuariosView,
    meta: {
      requiresAuth: true,
      verificarAcceso: esAdministradorSistema,
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
      verificarAcceso: esAdministradorSistema,
    },
  },
  {
    path: '/mapa-estrategico',
    name: 'mapa-estrategico',
    component: MapaEstrategicoView,
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

  // Bloque 2: protección de rutas por rol. Las páginas de navegación de
  // planificación/KPI/mediciones quedan SIN restricción acá a propósito
  // (el Usuario de consulta debe poder navegarlas, de solo lectura — los
  // botones de escritura ya se ocultan por componente). Solo las páginas
  // exclusivas de un rol (Áreas, Usuarios, Bitácora) usan
  // meta.verificarAcceso. La autorización real y definitiva es la del
  // backend; esto solo evita exponer la pantalla en la navegación.
  if (autenticado && to.meta.verificarAcceso) {
    const usuarioActual = { rol: obtenerRolAlmacenado() }

    if (!to.meta.verificarAcceso(usuarioActual)) {
      return '/dashboard'
    }
  }

  return true
})

export default router