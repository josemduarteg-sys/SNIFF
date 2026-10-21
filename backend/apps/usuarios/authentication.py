from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


def usuario_puede_autenticarse(user):
    """Etapa 2 (auditoría A3): regla única de "cuenta habilitada" para
    SimpleJWT (SIMPLE_JWT['USER_AUTHENTICATION_RULE']), que la aplica al
    iniciar sesión y al renovar el access token. Además de is_active (la
    regla por defecto de SimpleJWT) exige el `estado` funcional de SNIFF,
    que el módulo de Usuarios gestiona junto con is_active: así renovar un
    token nunca devuelve acceso a una cuenta inactivada."""
    return user is not None and user.is_active and user.estado is not False

RUTAS_PERMITIDAS_CON_PASSWORD_TEMPORAL = (
    '/api/auth/login/',
    '/api/auth/refresh/',
    '/api/auth/logout/',
    '/api/usuarios/me/',
    '/api/usuarios/cambiar-password/',
    '/api/usuarios/solicitar-restablecimiento/',
)


class JWTAuthenticationConControlPasswordTemporal(JWTAuthentication):
    """Igual que JWTAuthentication, pero bloquea el uso del resto de la API
    mientras el usuario tenga debe_cambiar_password=True, dejando pasar
    únicamente las rutas necesarias para iniciar sesión, consultar su
    propio perfil y cambiar la contraseña."""

    def get_user(self, validated_token):
        # Etapa 2 (A3): un access token emitido antes de inactivar la cuenta
        # deja de servir en la siguiente petición (401 -> el frontend
        # intenta renovar -> la renovación también se rechaza).
        usuario = super().get_user(validated_token)

        if not usuario_puede_autenticarse(usuario):
            raise AuthenticationFailed('La cuenta de usuario está inactiva.', code='user_inactive')

        return usuario

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
