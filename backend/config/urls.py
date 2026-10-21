from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.usuarios.views import LoginView, LogoutView


urlpatterns = [
    path('admin/', admin.site.urls),

    #autenticacion
    # Etapa 2 (B2): se retiró 'api-auth/' (login de sesión de la API
    # navegable de DRF): el frontend no lo usa y era un segundo inicio de
    # sesión sin límite de intentos.
    path('api/auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    

    #apis del sistema
    path('api/', include('apps.estrategia.urls')),
    path('api/', include('apps.indicadores.urls')),
    path('api/', include('apps.integraciones.urls')),
    path('api/', include('apps.usuarios.urls')),
    path('api/', include('apps.auditoria.urls')),

]

