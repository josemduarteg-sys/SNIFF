from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView, 
TokenRefreshView,
)


urlpatterns = [
    path('admin/', admin.site.urls),

    #autenticacion
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    

    #apis del sistema
    path('api/', include('apps.estrategia.urls')),
    path('api/', include('apps.indicadores.urls')),
    path('api/', include('apps.integraciones.urls')),
    path('api/', include('apps.usuarios.urls')),
    path('api/', include('apps.auditoria.urls')),

]

