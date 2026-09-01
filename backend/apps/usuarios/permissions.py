from rest_framework.permissions import SAFE_METHODS, BasePermission

ROLES_OPERATIVOS = (
    'supervisor',
    'operativo',
    'usuario operativo',
)

ROLES_CONSULTA = (
    'consulta',
    'visualizador',
    'gerencia',
    'gerente',
    'usuario de consulta',
)


def obtener_nombre_rol(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return ''

    rol_nombre = getattr(getattr(user, 'rol', None), 'nombre', '') or ''
    return rol_nombre.lower().strip()


def es_administrador(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if user.is_superuser or user.is_staff:
        return True

    return obtener_nombre_rol(user) in ('administrador', 'admin')


def es_operativo_o_supervisor(user):
    return obtener_nombre_rol(user) in ROLES_OPERATIVOS


def es_consulta(user):
    return obtener_nombre_rol(user) in ROLES_CONSULTA


class EsAdministradorSistema(BasePermission):
    message = 'No tenés permisos para administrar usuarios.'

    def has_permission(self, request, view):
        return es_administrador(request.user)


class PermisoPlaneacion(BasePermission):
    """Estrategias, objetivos y catálogos de planeación (crear/editar: admin/supervisor/operativo)."""

    message = 'No tenés permisos para modificar esta información.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        if request.method == 'DELETE':
            return es_administrador(request.user)

        return es_administrador(request.user) or es_operativo_o_supervisor(request.user)


class PermisoIndicadorKPI(BasePermission):
    message = 'No tenés permisos para modificar indicadores KPI.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        if getattr(view, 'action', None) in ('autorizar', 'anular'):
            return es_administrador(request.user)

        if request.method == 'DELETE':
            return es_administrador(request.user)

        return es_administrador(request.user) or es_operativo_o_supervisor(request.user)


class PermisoMedicion(BasePermission):
    message = 'No tenés permisos para registrar o modificar mediciones.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        if request.method == 'DELETE':
            return es_administrador(request.user)

        return es_administrador(request.user) or es_operativo_o_supervisor(request.user)


class PermisoCatalogoSoloAdmin(BasePermission):
    message = 'Solo un administrador puede modificar este catálogo.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return es_administrador(request.user)
