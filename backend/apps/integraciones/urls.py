from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ArchivoImportadoViewSet,
    ConexionDWViewSet,
    ConsultaDWViewSet,
)

router = DefaultRouter()
router.register(r'archivos-importados', ArchivoImportadoViewSet, basename='archivos-importados')
router.register(r'conexiones-dw', ConexionDWViewSet, basename='conexiones-dw')
router.register(r'consultas-dw', ConsultaDWViewSet, basename='consultas-dw')

urlpatterns = [
    path('', include(router.urls)),
]