from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CambiarPasswordView,
    RolViewSet,
    UsuarioActualView,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register(r'roles', RolViewSet, basename='roles')
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path('usuarios/me/', UsuarioActualView.as_view(), name='usuario-actual'),
    path(
        'usuarios/cambiar-password/',
        CambiarPasswordView.as_view(),
        name='cambiar-password',
    ),
    path('', include(router.urls)),
]

