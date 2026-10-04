from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

RUTAS_PERMITIDAS_CON_PASSWORD_TEMPORAL = (
    '/api/auth/login/',
    '/api/auth/refresh/',
    '/api/usuarios/me/',
    '/api/usuarios/cambiar-password/',
    '/api/usuarios/solicitar-restablecimiento/',
)


class JWTAuthenticationConControlPasswordTemporal(JWTAuthentication):
    """Igual que JWTAuthentication, pero bloquea el uso del resto de la API
    mientras el usuario tenga debe_cambiar_password=True, dejando pasar
    únicamente las rutas necesarias para iniciar sesión, consultar su
    propio perfil y cambiar la contraseña."""

    def authenticate(self, request):
        resultado = super().authenticate(request)

        if resultado is None:
            return resultado

        usuario, token = resultado

        if (
            getattr(usuario, 'debe_cambiar_password', False)
            and request.path not in RUTAS_PERMITIDAS_CON_PASSWORD_TEMPORAL
        ):
            raise PermissionDenied(
                'Debés cambiar tu contraseña antes de continuar utilizando el sistema.'
            )

        return resultado
