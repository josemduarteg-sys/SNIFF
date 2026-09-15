from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BitacoraViewSet, NotificacionViewSet

router = DefaultRouter()
router.register(r'bitacora', BitacoraViewSet, basename='bitacora')
router.register(r'notificaciones', NotificacionViewSet, basename='notificaciones')

urlpatterns = [
    path('', include(router.urls)),
]

