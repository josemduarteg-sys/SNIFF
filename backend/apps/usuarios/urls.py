from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CambiarPasswordView,
    RolViewSet,
    SolicitarRestablecimientoPasswordView,
    SolicitudRestablecimientoPasswordViewSet,
    UsuarioActualView,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register(r'roles', RolViewSet, basename='roles')
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')
router.register(
    r'solicitudes-restablecimiento',
    SolicitudRestablecimientoPasswordViewSet,
    basename='solicitudes-restablecimiento',
)

urlpatterns = [
    path('usuarios/me/', UsuarioActualView.as_view(), name='usuario-actual'),
    path(
        'usuarios/cambiar-password/',
        CambiarPasswordView.as_view(),
        name='cambiar-password',
    ),
    path(
        'usuarios/solicitar-restablecimiento/',
        SolicitarRestablecimientoPasswordView.as_view(),
        name='solicitar-restablecimiento',
    ),
    path('', include(router.urls)),
]

