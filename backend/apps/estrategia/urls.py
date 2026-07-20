from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AreaViewSet, EstrategiaViewSet, ObjetivoViewSet

router = DefaultRouter()
router.register(r'areas', AreaViewSet, basename='areas')
router.register(r'estrategias', EstrategiaViewSet, basename='estrategias')
router.register(r'objetivos', ObjetivoViewSet, basename='objetivos')

urlpatterns = [
    path('', include(router.urls)),
]

