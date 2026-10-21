from .services import registrar_bitacora_obligatoria


class BitacoraCatalogoMixin:
    """Etapa 4 (auditoría M7): registra en bitácora la creación y los
    cambios de un catálogo (quién, cuándo y qué operación). Una edición que
    no cambia ningún valor no deja registro, para no duplicar entradas por
    reenvíos del mismo formulario.

    Cada ViewSet define:
    - modulo_bitacora: texto del módulo en la bitácora.
    - describir_para_bitacora(instancia): cómo se nombra el registro.

    Solo se usa con catálogos de planificación: sus valores no son
    sensibles, así que el detalle incluye valor anterior y nuevo. No
    recalcula nada: un cambio de rango afecta solo a lo que se clasifique
    después (ver obtener_estado_por_cumplimiento)."""

    modulo_bitacora = ''

    def describir_para_bitacora(self, instancia):
        return str(instancia)

    def perform_create(self, serializer):
        instancia = serializer.save()

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion='crear',
            modulo=self.modulo_bitacora,
            descripcion=f'Creó {self.describir_para_bitacora(instancia)}.',
            request=self.request,
        )

    def perform_update(self, serializer):
        campos = list(serializer.validated_data.keys())
        antes = {campo: getattr(serializer.instance, campo) for campo in campos}

        instancia = serializer.save()

        cambios = [
            (campo, antes[campo], getattr(instancia, campo))
            for campo in campos
            if getattr(instancia, campo) != antes[campo]
        ]

        if not cambios:
            return

        if [campo for campo, _, _ in cambios] == ['estado'] and isinstance(cambios[0][2], bool):
            verbo = 'Reactivó' if cambios[0][2] else 'Desactivó'
            descripcion = f'{verbo} {self.describir_para_bitacora(instancia)}.'
            accion = 'actualizar' if cambios[0][2] else 'eliminar'
        else:
            detalle = '; '.join(
                f'{campo}: {self._texto(anterior)} → {self._texto(nuevo)}'
                for campo, anterior, nuevo in cambios
            )
            descripcion = f'Actualizó {self.describir_para_bitacora(instancia)} ({detalle}).'
            accion = 'actualizar'

        registrar_bitacora_obligatoria(
            usuario=self.request.user,
            accion=accion,
            modulo=self.modulo_bitacora,
            descripcion=descripcion,
            request=self.request,
        )

    @staticmethod
    def _texto(valor):
        if valor is None:
            return 'vacío'

        if isinstance(valor, bool):
            return 'activo' if valor else 'inactivo'

        return str(valor)
