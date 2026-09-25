from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AreaViewSet,
    ObjetivoEspecificoViewSet,
    ObjetivoGeneralViewSet,
    PlanAnualViewSet,
    PlanEstrategicoViewSet,
)

router = DefaultRouter()
router.register(r'areas', AreaViewSet, basename='areas')
router.register(r'planes-estrategicos', PlanEstrategicoViewSet, basename='planes-estrategicos')
router.register(r'objetivos-generales', ObjetivoGeneralViewSet, basename='objetivos-generales')
router.register(r'planes-anuales', PlanAnualViewSet, basename='planes-anuales')
router.register(r'objetivos-especificos', ObjetivoEspecificoViewSet, basename='objetivos-especificos')

urlpatterns = [
    path('', include(router.urls)),
]
