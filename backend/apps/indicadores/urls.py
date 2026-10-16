from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ConfiguracionMedicionesView,
    FrecuenciaViewSet,
    IndicadorKPIViewSet,
    MetaKPIViewSet,
    ResponsableKPIViewSet,
    EstadoCumplimientoViewSet,
    RangoKPIViewSet,
    PeriodoMedicionViewSet,
    MedicionViewSet,
    AlertaViewSet,
)

router = DefaultRouter()
router.register(r'frecuencias', FrecuenciaViewSet, basename='frecuencias')
router.register(r'indicadores-kpi', IndicadorKPIViewSet, basename='indicadores-kpi')
router.register(r'metas-kpi', MetaKPIViewSet, basename='metas-kpi')
router.register(r'responsables-kpi', ResponsableKPIViewSet, basename='responsables-kpi')
router.register(r'estados-cumplimiento', EstadoCumplimientoViewSet, basename='estados-cumplimiento')
router.register(r'rangos-kpi', RangoKPIViewSet, basename='rangos-kpi')
router.register(r'periodos-medicion', PeriodoMedicionViewSet, basename='periodos-medicion')
router.register(r'mediciones', MedicionViewSet, basename='mediciones')
router.register(r'alertas', AlertaViewSet, basename='alertas')

urlpatterns = [
    path('configuracion-mediciones/', ConfiguracionMedicionesView.as_view(), name='configuracion-mediciones'),
    path('', include(router.urls)),
]

