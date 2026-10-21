from rest_framework.permissions import SAFE_METHODS, BasePermission

# Bloque 2 (correcciones Hernán): los 4 roles definitivos de la
# aplicación. Los nombres deben coincidir EXACTAMENTE (en minúsculas, sin
# espacios al borde) con Rol.nombre tras la migración
# usuarios.0003_adaptar_roles_bloque2_hernan — ese es el único lugar que
# los crea/renombra.
ROL_ADMIN_SISTEMA = 'administrador del sistema'
ROL_ADMIN_PLANIFICACION = 'administrador de planificación'
ROL_EJECUTOR_OPERATIVO = 'ejecutor operativo'
ROL_USUARIO_CONSULTA = 'usuario de consulta'


def obtener_nombre_rol(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return ''

    rol_nombre = getattr(getattr(user, 'rol', None), 'nombre', '') or ''
    return rol_nombre.lower().strip()


def es_administrador_sistema(user):
    """Administrador del sistema: cuentas, roles, solicitudes de
    restablecimiento, bitácora. NO incluye planificación/KPI (ver
    es_administrador_planificacion) — ésa es justamente la separación que
    pidió el cliente en el Bloque 2.

    is_staff/is_superuser YA NO son, por sí solos, una autorización
    general sobre la aplicación (así lo pidió explícitamente la matriz de
    permisos). Se usan únicamente como resguardo técnico para un
    superusuario de Django que todavía no tiene un Rol de aplicación
    asignado (p. ej. recién creado con createsuperuser) — en cuanto se le
    asigna un Rol, manda ese Rol."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if obtener_nombre_rol(user) == ROL_ADMIN_SISTEMA:
        return True

    if user.rol_id is None and user.is_superuser:
        return True

    return False


def es_administrador_planificacion(user):
    """Administrador de planificación: planes estratégicos/anuales,
    objetivos, KPI (crear/editar/autorizar/anular), catálogos de
    planificación (Área, Frecuencia, EstadoCumplimiento, RangoKPI,
    PeriodoMedicion, MetaKPI) y revisión de alertas de cumplimiento de
    KPI. NO incluye registrar mediciones ni administrar usuarios."""
    return obtener_nombre_rol(user) == ROL_ADMIN_PLANIFICACION


def es_ejecutor_operativo(user):
    """Ejecutor operativo: registra mediciones y adjunta su evidencia.
    NO puede crear ni modificar planes, objetivos ni KPI — solo
    consultarlos (ver PermisoPlaneacion/PermisoIndicadorKPI: GET siempre
    permitido a cualquier autenticado)."""
    return obtener_nombre_rol(user) == ROL_EJECUTOR_OPERATIVO


def es_usuario_consulta(user):
    """Usuario de consulta: navegación de solo lectura sobre toda la
    aplicación. Nunca true para ninguna verificación de escritura; existe
    como helper explícito para el frontend/documentación, no se usa para
    bloquear nada acá (el bloqueo real es que ninguna de las funciones de
    arriba lo reconoce como válido para escribir)."""
    return obtener_nombre_rol(user) == ROL_USUARIO_CONSULTA


# Alias de compatibilidad: algunas vistas/código heredado podían importar
# `es_administrador` a secas. Antes del Bloque 2 ese nombre conflaba
# sistema+planificación; ahora apunta explícitamente a administrador del
# sistema (nunca a planificación) para no reabrir esa conflación por
# accidente. No queda ningún uso real de este alias tras el Bloque 2 (se
# audit贸 cada ViewSet), se conserva solo por si algo externo lo importa.
es_administrador = es_administrador_sistema


class EsAdministradorSistema(BasePermission):
    message = 'No tenés permisos para administrar usuarios.'

    def has_permission(self, request, view):
        return es_administrador_sistema(request.user)


class PermisoIntegracionesSoloLectura(BasePermission):
    """Etapa 2 (auditoría A4): el módulo de integraciones (CSV / Data
    Warehouse) está fuera del alcance entregado y no tiene interfaz. Se
    deja en la alternativa más restrictiva que no rompe dependencias:
    consulta solo para Administrador del sistema (configuración técnica) y
    ninguna escritura para nadie — los ViewSets además limitan
    http_method_names a lectura. Habilitar escrituras requiere una
    decisión explícita del cliente."""

    message = 'El módulo de integraciones no está habilitado para este perfil.'

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS and es_administrador_sistema(request.user)


class PermisoPlaneacion(BasePermission):
    """Planeación (Área, planes estratégicos/anuales, objetivos): consulta
    libre para cualquier autenticado; crear/editar exclusivo de
    Administrador de planificación."""

    message = 'No tenés permisos para modificar esta información.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return es_administrador_planificacion(request.user)


class PermisoEstrategiaObjetivo(PermisoPlaneacion):
    """Plan estratégico / Plan anual / Objetivo general: además de
    PermisoPlaneacion, las transiciones de estado (poner en uso / cerrar)
    también son de Administrador de planificación (antes eran exclusivas
    de "administrador" conflado; ahora ese rol es justamente quien
    gestiona la planificación).

    No hay una restricción de objeto adicional más allá de
    PermisoPlaneacion: los bloqueos por estado (título/periodo congelados
    En uso, todo congelado Cerrado) ya los aplica el serializer para
    cualquier rol — ver apps/estrategia/serializers.py."""

    ACCIONES_SOLO_ADMIN_PLANIFICACION = ('poner_en_uso', 'cerrar', 'completar_vigencia')

    def has_permission(self, request, view):
        if getattr(view, 'action', None) in self.ACCIONES_SOLO_ADMIN_PLANIFICACION:
            return es_administrador_planificacion(request.user)

        return super().has_permission(request, view)


class PermisoIndicadorKPI(BasePermission):
    """Indicador KPI: consulta libre; crear/editar/autorizar/anular
    exclusivo de Administrador de planificación. DELETE (si llega a
    usarse) queda en el mismo dueño del recurso — no se le da a Ejecutor
    ni a Administrador del sistema, que no son dueños de este dominio."""

    message = 'No tenés permisos para modificar indicadores KPI.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return es_administrador_planificacion(request.user)


class PermisoMedicion(BasePermission):
    """Medición (y su evidencia, que viaja en el mismo payload): consulta
    y descarga de evidencia libres para cualquier autenticado (vía GET);
    registrar/editar exclusivo de Ejecutor operativo. DELETE (si llega a
    usarse) se mantiene con Administrador de planificación por ser la
    operación más sensible del recurso — igual que ya pasaba antes del
    Bloque 2 (DELETE quedaba reservado al rol "admin", más restrictivo
    que crear/editar); acá eso significa que ni siquiera Ejecutor, que sí
    puede crear/editar, puede borrar.

    Etapa 1 (auditoría M3): MedicionViewSet ya no expone DELETE
    (http_method_names), así que ninguna medición se borra físicamente; la
    rama de DELETE de abajo solo decide si el rechazo es 405 o 403."""

    message = 'No tenés permisos para registrar o modificar mediciones.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        if request.method == 'DELETE':
            return es_administrador_planificacion(request.user)

        return es_ejecutor_operativo(request.user)


class PermisoCatalogoSoloAdmin(BasePermission):
    """Catálogos de planeación/KPI (Frecuencia, EstadoCumplimiento,
    RangoKPI, PeriodoMedicion, MetaKPI, ResponsableKPI, Alerta): consulta
    libre; escritura exclusiva de Administrador de planificación.

    Decisión explícita del Bloque 2: estos catálogos son insumo directo
    de KPI/planificación, NO de administración de sistema — por eso el
    nombre de la clase ya no corresponde a su dueño real, pero se
    conserva para no renombrarla en cada ViewSet que la importa."""

    message = 'No tenés permisos para modificar este catálogo.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return es_administrador_planificacion(request.user)


class PermisoSolicitudAmpliacion(BasePermission):
    """Etapa 5: solicitudes de días adicionales para registrar mediciones.
    Solo dos roles participan: el Ejecutor operativo solicita, consulta las
    suyas y puede retirarlas; el Administrador de planificación consulta
    todas y las autoriza o rechaza. Administrador del sistema y Usuario de
    consulta no tienen acceso (ni siquiera de lectura). Qué solicitudes ve
    cada uno lo filtra el ViewSet."""

    message = 'No tenés permisos para gestionar solicitudes de días adicionales.'

    ACCIONES_EJECUTOR = ('create', 'retirar')
    ACCIONES_ADMIN_PLANIFICACION = ('autorizar', 'rechazar')

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        accion = getattr(view, 'action', None)

        if accion in self.ACCIONES_EJECUTOR:
            return es_ejecutor_operativo(request.user)

        if accion in self.ACCIONES_ADMIN_PLANIFICACION:
            return es_administrador_planificacion(request.user)

        if request.method in SAFE_METHODS:
            return es_ejecutor_operativo(request.user) or es_administrador_planificacion(request.user)

        return False
