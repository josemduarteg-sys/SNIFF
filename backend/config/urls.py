from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.estrategia.urls')),
    path('api/', include('apps.indicadores.urls')),
    path('api/', include('apps.integraciones.urls')),
    path('api/', include('apps.usuarios.urls')),
    path('api/', include('apps.auditoria.urls'))
    
]

