from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AreaViewSet, PlanEstrategicoViewSet, ObjetivoGeneralViewSet

router = DefaultRouter()
router.register(r'areas', AreaViewSet, basename='areas')
router.register(r'planes-estrategicos', PlanEstrategicoViewSet, basename='planes-estrategicos')
router.register(r'objetivos-generales', ObjetivoGeneralViewSet, basename='objetivos-generales')

urlpatterns = [
    path('', include(router.urls)),
]
