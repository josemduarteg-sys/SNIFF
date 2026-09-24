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


class PermisoEstrategiaObjetivo(PermisoPlaneacion):
    """Plan estratégico / Objetivo general: además de PermisoPlaneacion, las
    transiciones de estado (poner en uso / cerrar) son exclusivas de
    administrador.

    No hay una restricción de objeto adicional más allá de PermisoPlaneacion:
    los bloqueos por estado (título/periodo congelados En uso, todo
    congelado Cerrado) ya los aplica el serializer para cualquier rol,
    incluido administrador — ver apps/estrategia/serializers.py. El modelo
    anterior de "editable solo mientras 'en_revision'" no tiene equivalente
    en el nuevo flujo Borrador/En uso/Cerrado (la descripción, por ejemplo,
    debe seguir siendo editable por cualquier rol con permiso de planeación
    mientras el plan esté En uso)."""

    ACCIONES_SOLO_ADMIN = ('poner_en_uso', 'cerrar')

    def has_permission(self, request, view):
        if getattr(view, 'action', None) in self.ACCIONES_SOLO_ADMIN:
            return es_administrador(request.user)

        return super().has_permission(request, view)


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
