"""Etapa 2 (auditoría B2): límites de intentos para el inicio de sesión y
la solicitud de restablecimiento de contraseña.

Usa el throttling incluido en Django REST Framework (sin dependencias
nuevas). Los contadores viven en la caché `default` de Django y expiran
solos al terminar cada ventana: no existe bloqueo permanente de cuentas.

Tasas configurables por variables de entorno (ver config/settings.py,
SNIFF_LIMITES_SOLICITUDES). Una tasa vacía desactiva ese límite.

La IP se obtiene con SimpleRateThrottle.get_ident(), que respeta
REST_FRAMEWORK['NUM_PROXIES']: con 0 (valor por defecto del proyecto) usa
REMOTE_ADDR e ignora X-Forwarded-For, que un cliente puede falsificar.
Detrás de un proxy inverso hay que fijar NUM_PROXIES al número de proxies
de confianza; si no, todos los usuarios compartirían la IP del proxy.
"""

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class LimiteSolicitudes(SimpleRateThrottle):
    # La tasa se lee de settings en cada uso (no al importar el módulo),
    # para que override_settings funcione en pruebas.
    def get_rate(self):
        return settings.SNIFF_LIMITES_SOLICITUDES.get(self.scope) or None

    def clave_por_ip(self, request):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}

    def valor_enviado(self, request, campo):
        datos = request.data if hasattr(request.data, 'get') else {}
        return datos.get(campo)

    def clave_por_valor(self, valor):
        valor = str(valor or '').strip().lower()

        if not valor:
            return None

        return self.cache_format % {'scope': self.scope, 'ident': valor}


class LimiteLoginPorIP(LimiteSolicitudes):
    scope = 'login_ip'

    def get_cache_key(self, request, view):
        return self.clave_por_ip(request)


class LimiteLoginPorUsuario(LimiteSolicitudes):
    """Frena el ataque a una cuenta concreta desde varias IP. Cuenta por
    nombre de usuario ingresado, exista o no la cuenta."""

    scope = 'login_usuario'

    def get_cache_key(self, request, view):
        return self.clave_por_valor(self.valor_enviado(request, 'username'))


class LimiteRestablecimientoPorIP(LimiteSolicitudes):
    scope = 'restablecimiento_ip'

    def get_cache_key(self, request, view):
        return self.clave_por_ip(request)


class LimiteRestablecimientoPorIdentificador(LimiteSolicitudes):
    """Cuenta por identificador ingresado, exista o no la cuenta: la
    respuesta al alcanzar el límite es la misma en ambos casos, así que no
    revela si la cuenta existe."""

    scope = 'restablecimiento_identificador'

    def get_cache_key(self, request, view):
        return self.clave_por_valor(self.valor_enviado(request, 'identificador'))
