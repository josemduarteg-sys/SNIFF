from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RolViewSet, UsuarioViewSet, UsuarioActualView

router = DefaultRouter()
router.register(r'roles', RolViewSet, basename='roles')
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path('usuarios/me/', UsuarioActualView.as_view(), name='usuario-actual'),
    path('', include(router.urls)),
]

