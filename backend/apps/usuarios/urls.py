from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RolViewSet, UsuarioViewSet

router = DefaultRouter()
router.register(r'roles', RolViewSet, basename='roles')
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path('', include(router.urls)),
]

