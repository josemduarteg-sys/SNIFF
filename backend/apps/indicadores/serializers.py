import os

from rest_framework import serializers

from .models import (
    Frecuencia,
    IndicadorKPI,
    MetaKPI,
    ResponsableKPI,
    EstadoCumplimiento,
    RangoKPI,
    PeriodoMedicion,
    Medicion,
    Alerta,
    validar_archivo_evidencia,
)


class FrecuenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frecuencia
        fields = [
            'id',
            'nombre',
            'descripcion',
            'estado',
        ]
        read_only_fields = ['id']


class IndicadorKPISerializer(serializers.ModelSerializer):
    objetivo_especifico_texto = serializers.CharField(
        source='objetivo_especifico.texto_objetivo', read_only=True
    )
    plan_anual = serializers.SerializerMethodField()
    plan_anual_nombre = serializers.SerializerMethodField()
    plan_anual_estado = serializers.SerializerMethodField()
    plan_estrategico = serializers.SerializerMethodField()
    plan_estrategico_titulo = serializers.SerializerMethodField()
    # Expuesto solo para que el frontend pueda ocultar acciones cuando el
    # Plan estratégico ancestro está Cerrado. El bloqueo real lo aplica la
    # validación de abajo (ver validate() e IndicadorKPI.esta_bloqueado()).
    plan_estrategico_estado = serializers.SerializerMethodField()
    anio = serializers.ReadOnlyField()
    fecha_inicio_vigencia = serializers.ReadOnlyField()
    fecha_fin_vigencia = serializers.ReadOnlyField()
    frecuencia_nombre = serializers.CharField(source='frecuencia.nombre', read_only=True)
    autorizado_por_username = serializers.CharField(source='autorizado_por.username', read_only=True)
    creado_por_username = serializers.CharField(source='creado_por.username', read_only=True)
    puede_modificarse = serializers.SerializerMethodField()
    # Bloque 5 — seguimiento acumulado del KPI: calculados en cada
    # serialización a partir de las Mediciones reales (nunca almacenados
    # en el modelo, ver services.calcular_promedio_acumulado_kpi).
    promedio_acumulado = serializers.SerializerMethodField()
    cantidad_mediciones = serializers.SerializerMethodField()
    estado_acumulado_id = serializers.SerializerMethodField()
    estado_acumulado_nombre = serializers.SerializerMethodField()
    estado_acumulado_color = serializers.SerializerMethodField()

    class Meta:
        model = IndicadorKPI
        fields = [
            'id',
            'objetivo_especifico',
            'objetivo_especifico_texto',
            'plan_anual',
            'plan_anual_nombre',
            'plan_anual_estado',
            'plan_estrategico',
            'plan_estrategico_titulo',
            'plan_estrategico_estado',
            'anio',
            'frecuencia',
            'frecuencia_nombre',
            'nombre',
            'descripcion',
            'formula_medicion',
            'unidad_medida',
            'valor_meta',
            'fecha_inicio_vigencia',
            'fecha_fin_vigencia',
            'estado',
            'fecha_autorizacion',
            'autorizado_por',
            'autorizado_por_username',
            'creado_por',
            'creado_por_username',
            'puede_modificarse',
            'promedio_acumulado',
            'cantidad_mediciones',
            'estado_acumulado_id',
            'estado_acumulado_nombre',
            'estado_acumulado_color',
            'fecha_creacion',
        ]
        read_only_fields = [
            'id',
            'fecha_creacion',
            'estado',
            'fecha_autorizacion',
            'autorizado_por',
            'autorizado_por_username',
            'creado_por',
            'creado_por_username',
            'puede_modificarse',
            'promedio_acumulado',
            'cantidad_mediciones',
            'estado_acumulado_id',
            'estado_acumulado_nombre',
            'estado_acumulado_color',
        ]
        # DRF genera automáticamente un UniqueTogetherValidator a partir de
        # la UniqueConstraint del modelo (objetivo_especifico, nombre), que
        # correría antes que validate() con un mensaje técnico en
        # non_field_errors (mismo problema ya corregido en PlanAnualSerializer
        # durante Bloque 2). Se desactiva acá para que el único chequeo de
        # duplicado sea el de validate(), con mensaje en español natural. La
        # constraint del modelo/base de datos sigue intacta.
        validators = []

    def get_plan_anual(self, obj):
        return obj.plan_anual.id

    def get_plan_anual_nombre(self, obj):
        return obj.plan_anual.nombre

    def get_plan_anual_estado(self, obj):
        return obj.plan_anual.estado

    def get_plan_estrategico(self, obj):
        return obj.plan_estrategico.id

    def get_plan_estrategico_titulo(self, obj):
        return obj.plan_estrategico.titulo

    def get_plan_estrategico_estado(self, obj):
        return obj.plan_estrategico.estado

    def get_puede_modificarse(self, obj):
        return obj.puede_modificarse()

    def _promedio_acumulado_cacheado(self, obj):
        # Los 5 campos acumulados de abajo comparten el mismo promedio y el
        # mismo estado calculados; se cachean en la instancia para no
        # repetir las mismas consultas varias veces por cada KPI serializado.
        if not hasattr(obj, '_promedio_acumulado_cache'):
            from .services import calcular_promedio_acumulado_kpi

            obj._promedio_acumulado_cache = calcular_promedio_acumulado_kpi(obj)

        return obj._promedio_acumulado_cache

    def _estado_acumulado_cacheado(self, obj):
        if not hasattr(obj, '_estado_acumulado_cache'):
            from .services import obtener_estado_acumulado_kpi

            obj._estado_acumulado_cache = obtener_estado_acumulado_kpi(
                obj, self._promedio_acumulado_cacheado(obj),
            )

        return obj._estado_acumulado_cache

    def get_promedio_acumulado(self, obj):
        return self._promedio_acumulado_cacheado(obj)

    def get_cantidad_mediciones(self, obj):
        from .services import contar_mediciones_kpi

        return contar_mediciones_kpi(obj)

    def get_estado_acumulado_id(self, obj):
        estado = self._estado_acumulado_cacheado(obj)
        return estado.id if estado else None

    def get_estado_acumulado_nombre(self, obj):
        estado = self._estado_acumulado_cacheado(obj)
        return estado.nombre if estado else None

    def get_estado_acumulado_color(self, obj):
        estado = self._estado_acumulado_cacheado(obj)
        return estado.color if estado else None

    def validate(self, attrs):
        from apps.estrategia.services import plan_anual_esta_bloqueado

        instance = self.instance
        objetivo_especifico = attrs.get(
            'objetivo_especifico', getattr(instance, 'objetivo_especifico', None)
        )

        if not objetivo_especifico:
            raise serializers.ValidationError({
                'objetivo_especifico': 'Seleccioná el objetivo específico del KPI.'
            })

        if instance is None:
            # Creación: solo dentro de un Plan anual En uso, cuyo Plan
            # estratégico no esté Cerrado (plan_anual_esta_bloqueado ya
            # contempla ambos casos).
            plan_anual = objetivo_especifico.plan_anual

            if not plan_anual.esta_en_uso() or plan_anual_esta_bloqueado(plan_anual):
                raise serializers.ValidationError({
                    'objetivo_especifico': (
                        'Solo se pueden crear KPI sobre un objetivo específico '
                        'cuyo Plan anual esté En uso.'
                    )
                })
        else:
            if instance.esta_bloqueado():
                raise serializers.ValidationError(
                    'El Plan anual o el Plan estratégico de este KPI están '
                    'Cerrados y no permiten modificaciones.'
                )

            if not instance.puede_modificarse():
                campos_bloqueados = {
                    'objetivo_especifico',
                    'frecuencia',
                    'nombre',
                    'descripcion',
                    'formula_medicion',
                    'unidad_medida',
                    'valor_meta',
                }

                campos_intentados = campos_bloqueados.intersection(set(attrs.keys()))

                if campos_intentados:
                    raise serializers.ValidationError(
                        'El KPI ya está autorizado y no permite modificar sus datos principales.'
                    )

            # Si se intenta reasociar el KPI a otro objetivo específico,
            # ese nuevo contexto también debe estar en uso y no bloqueado.
            if 'objetivo_especifico' in attrs:
                nuevo_plan_anual = objetivo_especifico.plan_anual

                if not nuevo_plan_anual.esta_en_uso() or plan_anual_esta_bloqueado(nuevo_plan_anual):
                    raise serializers.ValidationError({
                        'objetivo_especifico': (
                            'El objetivo específico seleccionado debe pertenecer a un '
                            'Plan anual En uso.'
                        )
                    })

        formula_medicion = attrs.get('formula_medicion', getattr(instance, 'formula_medicion', None))

        if formula_medicion is None or not formula_medicion.strip():
            raise serializers.ValidationError({
                'formula_medicion': 'Ingresá la fórmula de medición.'
            })

        nombre = attrs.get('nombre', getattr(instance, 'nombre', None))

        if not nombre or not nombre.strip():
            raise serializers.ValidationError({
                'nombre': 'Ingresá el nombre del KPI.'
            })

        duplicados = IndicadorKPI.objects.filter(
            objetivo_especifico=objetivo_especifico,
            nombre=nombre,
        )

        if instance is not None:
            duplicados = duplicados.exclude(pk=instance.pk)

        if duplicados.exists():
            raise serializers.ValidationError({
                'nombre': 'Ya existe un KPI con ese nombre para este objetivo específico.'
            })

        unidad_medida = attrs.get('unidad_medida', getattr(instance, 'unidad_medida', None))

        if not unidad_medida:
            raise serializers.ValidationError({
                'unidad_medida': 'Seleccioná la unidad de medida del KPI.'
            })

        valor_meta = attrs.get('valor_meta')

        if valor_meta is None and instance is not None and 'valor_meta' not in attrs:
            valor_meta = instance.valor_meta

        if valor_meta is None:
            raise serializers.ValidationError({
                'valor_meta': 'Ingresá la meta del KPI.'
            })

        if unidad_medida == '%' and (valor_meta < 0 or valor_meta > 100):
            raise serializers.ValidationError({
                'valor_meta': 'Cuando la unidad de medida es porcentaje, la meta debe estar entre 0 y 100.'
            })

        frecuencia = attrs.get('frecuencia', getattr(instance, 'frecuencia', None))

        if not frecuencia:
            raise serializers.ValidationError({
                'frecuencia': 'Seleccioná la frecuencia del KPI.'
            })

        return attrs


class MetaKPISerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )

    class Meta:
        model = MetaKPI
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'valor_meta',
            'fecha_inicio',
            'fecha_fin',
            'estado',
        ]
        read_only_fields = ['id']


class ResponsableKPISerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )
    usuario_username = serializers.CharField(
        source='usuario.username',
        read_only=True
    )

    class Meta:
        model = ResponsableKPI
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'usuario',
            'usuario_username',
            'fecha_asignacion',
            'estado',
        ]
        read_only_fields = ['id', 'fecha_asignacion']


class EstadoCumplimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoCumplimiento
        fields = [
            'id',
            'nombre',
            'descripcion',
            'color',
            'estado',
        ]
        read_only_fields = ['id']


class RangoKPISerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )
    estado_cumplimiento_nombre = serializers.CharField(
        source='estado_cumplimiento.nombre',
        read_only=True
    )

    class Meta:
        model = RangoKPI
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'estado_cumplimiento',
            'estado_cumplimiento_nombre',
            'valor_minimo',
            'valor_maximo',
            'estado',
        ]
        read_only_fields = ['id']


class PeriodoMedicionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoMedicion
        fields = [
            'id',
            'tipo_periodo',
            'fecha_inicio',
            'fecha_fin',
            'anio',
            'mes',
            'semana',
            'dia',
            'descripcion',
        ]
        read_only_fields = ['id']


class MedicionSerializer(serializers.ModelSerializer):
    """Bloque 4: el usuario ya NO elige periodo/fecha de medición — el
    backend los determina siempre a partir de `obtener_info_siguiente_periodo`
    (única fuente de verdad, compartida con el endpoint `siguiente-periodo`
    y con el cierre automático). En edición, solo se permiten tocar
    valor_resultado/observacion/evidencia."""

    indicador_nombre = serializers.CharField(source='indicador.nombre', read_only=True)
    unidad_medida = serializers.CharField(source='indicador.unidad_medida', read_only=True)
    indicador_plan_estrategico_titulo = serializers.CharField(
        source='indicador.plan_estrategico.titulo', read_only=True
    )
    indicador_plan_anual_nombre = serializers.CharField(
        source='indicador.plan_anual.nombre', read_only=True
    )
    indicador_objetivo_especifico_texto = serializers.CharField(
        source='indicador.objetivo_especifico.texto_objetivo', read_only=True
    )
    indicador_frecuencia_nombre = serializers.CharField(
        source='indicador.frecuencia.nombre', read_only=True
    )
    periodo_nombre = serializers.SerializerMethodField()
    valor_meta = serializers.SerializerMethodField()
    observaciones = serializers.CharField(source='observacion', read_only=True)
    estado_cumplimiento = serializers.PrimaryKeyRelatedField(read_only=True)
    estado_cumplimiento_nombre = serializers.CharField(
        source='estado_cumplimiento.nombre',
        read_only=True
    )
    estado_cumplimiento_color = serializers.CharField(
        source='estado_cumplimiento.color',
        read_only=True
    )
    registrado_por_username = serializers.CharField(
        source='registrado_por.username',
        read_only=True,
        default=None,
    )
    porcentaje_cumplimiento = serializers.SerializerMethodField()
    evidencia = serializers.FileField(
        required=False,
        allow_null=True,
        write_only=True,
        validators=[validar_archivo_evidencia],
    )
    evidencia_nombre = serializers.SerializerMethodField()
    tiene_evidencia = serializers.SerializerMethodField()
    puede_modificarse = serializers.SerializerMethodField()
    # Bloque 5: promedio acumulado del KPI HASTA esta medición (ordenado por
    # PeriodoMedicion, no por fecha_registro) — distinto del resultado del
    # propio periodo (valor_resultado) y del porcentaje_cumplimiento legacy.
    promedio_acumulado_hasta_medicion = serializers.SerializerMethodField()
    estado_acumulado_hasta_medicion_nombre = serializers.SerializerMethodField()
    estado_acumulado_hasta_medicion_color = serializers.SerializerMethodField()

    class Meta:
        model = Medicion
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'unidad_medida',
            'indicador_plan_estrategico_titulo',
            'indicador_plan_anual_nombre',
            'indicador_objetivo_especifico_texto',
            'indicador_frecuencia_nombre',
            'meta',
            'valor_meta',
            'estado_cumplimiento',
            'estado_cumplimiento_nombre',
            'estado_cumplimiento_color',
            'periodo',
            'periodo_nombre',
            'registrado_por',
            'registrado_por_username',
            'archivo_importado',
            'consulta_dw',
            'fecha_medicion',
            'valor_resultado',
            'porcentaje_cumplimiento',
            'promedio_acumulado_hasta_medicion',
            'estado_acumulado_hasta_medicion_nombre',
            'estado_acumulado_hasta_medicion_color',
            'observacion',
            'observaciones',
            'evidencia',
            'evidencia_nombre',
            'tiene_evidencia',
            'cierre_automatico',
            'puede_modificarse',
            'fecha_registro',
        ]
        read_only_fields = [
            'id',
            'meta',
            'estado_cumplimiento',
            'periodo',
            'fecha_medicion',
            'fecha_registro',
            'porcentaje_cumplimiento',
            'promedio_acumulado_hasta_medicion',
            'estado_acumulado_hasta_medicion_nombre',
            'estado_acumulado_hasta_medicion_color',
            'periodo_nombre',
            'valor_meta',
            'observaciones',
            'registrado_por',
            'registrado_por_username',
            'cierre_automatico',
            'puede_modificarse',
        ]
        # Mismo motivo que en los demás serializers de este proyecto desde
        # Bloque 2: se desactiva el UniqueTogetherValidator automático de
        # DRF (derivado de unique_medicion_por_indicador_periodo) porque acá
        # el periodo ni siquiera lo envía el cliente — la disponibilidad ya
        # la resuelve obtener_info_siguiente_periodo() en validate().
        validators = []

    def get_periodo_nombre(self, obj):
        if not obj.periodo:
            return None

        if obj.periodo.descripcion:
            return obj.periodo.descripcion

        if obj.periodo.fecha_inicio and obj.periodo.fecha_fin:
            return f'{obj.periodo.fecha_inicio} - {obj.periodo.fecha_fin}'

        if obj.periodo.fecha_inicio:
            return str(obj.periodo.fecha_inicio)

        return f'Periodo {obj.periodo.id}'

    def get_valor_meta(self, obj):
        if obj.meta:
            return obj.meta.valor_meta

        if obj.indicador and obj.indicador.valor_meta is not None:
            return obj.indicador.valor_meta

        return None

    def get_porcentaje_cumplimiento(self, obj):
        return round(obj.calcular_cumplimiento(), 2)

    def _estado_acumulado_hasta_medicion_cacheado(self, obj):
        # Comparte el cálculo entre los 3 campos "..._hasta_medicion" de
        # abajo para no repetir la misma consulta por cada uno.
        if not hasattr(obj, '_estado_acumulado_hasta_medicion_cache'):
            from .services import calcular_promedio_acumulado_kpi, obtener_estado_acumulado_kpi

            promedio = calcular_promedio_acumulado_kpi(obj.indicador, hasta_periodo=obj.periodo)
            estado = obtener_estado_acumulado_kpi(obj.indicador, promedio)
            obj._estado_acumulado_hasta_medicion_cache = (promedio, estado)

        return obj._estado_acumulado_hasta_medicion_cache

    def get_promedio_acumulado_hasta_medicion(self, obj):
        promedio, _ = self._estado_acumulado_hasta_medicion_cacheado(obj)
        return promedio

    def get_estado_acumulado_hasta_medicion_nombre(self, obj):
        _, estado = self._estado_acumulado_hasta_medicion_cacheado(obj)
        return estado.nombre if estado else None

    def get_estado_acumulado_hasta_medicion_color(self, obj):
        _, estado = self._estado_acumulado_hasta_medicion_cacheado(obj)
        return estado.color if estado else None

    def get_evidencia_nombre(self, obj):
        if not obj.evidencia:
            return None

        return os.path.basename(obj.evidencia.name)

    def get_tiene_evidencia(self, obj):
        return bool(obj.evidencia)

    def get_puede_modificarse(self, obj):
        if obj.cierre_automatico:
            return False

        return not obj.indicador.esta_bloqueado()

    def validate(self, attrs):
        from .services import obtener_info_siguiente_periodo

        instance = self.instance

        if instance is not None:
            if instance.cierre_automatico:
                raise serializers.ValidationError(
                    'Esta medición fue cerrada automáticamente y no puede modificarse.'
                )

            if instance.indicador.esta_bloqueado():
                raise serializers.ValidationError(
                    'El Plan anual o el Plan estratégico de este KPI están Cerrados y '
                    'no permiten modificar mediciones.'
                )

            campos_permitidos = {'valor_resultado', 'observacion', 'evidencia'}
            campos_no_permitidos = set(attrs.keys()) - campos_permitidos

            if campos_no_permitidos:
                raise serializers.ValidationError(
                    'Solo se pueden modificar el resultado, la observación y la '
                    'evidencia de una medición existente.'
                )

            # REGLA V2 (inmutabilidad de la evidencia): una vez que una
            # Medicion ya tiene un archivo de evidencia, ese archivo queda
            # fijo como respaldo histórico — no puede reemplazarse ni
            # eliminarse. Se rechaza acá, en backend, en cuanto la clave
            # 'evidencia' aparece en la petición (sea un archivo nuevo o un
            # intento de vaciarla), sin depender de que el frontend oculte
            # el control. Una Medicion que todavía NO tiene evidencia sigue
            # pudiendo recibir una por esta vía (caso reportado aparte, no
            # se inventa una regla nueva para ese otro caso en esta tarea).
            if instance.evidencia and 'evidencia' in attrs:
                raise serializers.ValidationError(
                    'Esta medición ya tiene una evidencia adjunta. No puede reemplazarse '
                    'ni eliminarse: queda como respaldo histórico.'
                )

            indicador = instance.indicador
        else:
            indicador = attrs.get('indicador')

            if not indicador:
                raise serializers.ValidationError({
                    'indicador': 'Debe seleccionar un KPI.'
                })

            if indicador.esta_bloqueado():
                raise serializers.ValidationError(
                    'El Plan anual o el Plan estratégico de este KPI están Cerrados.'
                )

            info = obtener_info_siguiente_periodo(indicador)

            if not info['disponible']:
                raise serializers.ValidationError({'indicador': info['motivo']})

            attrs['_info_periodo'] = info

        valor_resultado = attrs.get('valor_resultado')

        if valor_resultado is None and instance is not None and 'valor_resultado' not in attrs:
            valor_resultado = instance.valor_resultado

        if valor_resultado is not None:
            if valor_resultado < 0:
                raise serializers.ValidationError({
                    'valor_resultado': 'El valor obtenido no puede ser negativo.'
                })

            if indicador.unidad_medida == '%' and valor_resultado > 100:
                raise serializers.ValidationError({
                    'valor_resultado': (
                        'Cuando la unidad de medida es porcentaje, el resultado '
                        'no puede ser mayor a 100.'
                    )
                })

        return attrs

    def create(self, validated_data):
        from apps.auditoria.services import registrar_bitacora
        from .services import (
            actualizar_alerta_cumplimiento_kpi,
            obtener_estado_para_medicion,
            obtener_o_crear_meta_vigente,
            obtener_o_crear_periodo,
            resolver_alertas_periodo_vencido,
        )

        info = validated_data.pop('_info_periodo')
        indicador = validated_data['indicador']

        periodo = obtener_o_crear_periodo(indicador, info['fecha_inicio_periodo'])
        meta = obtener_o_crear_meta_vigente(indicador)

        validated_data['periodo'] = periodo
        validated_data['meta'] = meta
        validated_data['fecha_medicion'] = info['fecha_cierre']
        validated_data['cierre_automatico'] = False

        estado = obtener_estado_para_medicion(
            indicador=indicador,
            meta=meta,
            valor_resultado=validated_data.get('valor_resultado'),
        )

        if estado is None:
            raise serializers.ValidationError(
                'No se encontró un estado de cumplimiento válido para esta medición.'
            )

        validated_data['estado_cumplimiento'] = estado

        medicion = super().create(validated_data)

        request = self.context.get('request')
        usuario = (
            request.user
            if request and request.user.is_authenticated
            else medicion.registrado_por
        )

        alerta = actualizar_alerta_cumplimiento_kpi(medicion.indicador, medicion_actual=medicion)
        resolver_alertas_periodo_vencido(medicion, usuario=usuario)

        registrar_bitacora(
            usuario=usuario,
            accion='crear',
            modulo='mediciones',
            descripcion=(
                f'Se registró una medición para el indicador '
                f'"{medicion.indicador.nombre}" (periodo {medicion.periodo.descripcion}) '
                f'con resultado {medicion.valor_resultado}.'
            ),
            request=request,
        )

        if alerta:
            registrar_bitacora(
                usuario=usuario,
                accion='crear',
                modulo='alertas',
                descripcion=(
                    f'Se generó una alerta automática para el indicador '
                    f'"{medicion.indicador.nombre}".'
                ),
                request=request,
            )

        return medicion

    def update(self, instance, validated_data):
        from apps.auditoria.services import registrar_bitacora
        from .services import (
            actualizar_alerta_cumplimiento_kpi,
            obtener_estado_para_medicion,
            resolver_alertas_periodo_vencido,
        )

        evidencia_anterior = instance.evidencia
        reemplaza_evidencia = 'evidencia' in validated_data

        valor_resultado = validated_data.get('valor_resultado', instance.valor_resultado)

        estado = obtener_estado_para_medicion(
            indicador=instance.indicador,
            meta=instance.meta,
            valor_resultado=valor_resultado,
        )

        if estado is None:
            raise serializers.ValidationError(
                'No se encontró un estado de cumplimiento válido para esta medición.'
            )

        validated_data['estado_cumplimiento'] = estado

        medicion = super().update(instance, validated_data)

        # Reemplazo de evidencia (punto 31): evita dejar el archivo anterior
        # huérfano en el almacenamiento local cuando se sube uno nuevo.
        if reemplaza_evidencia and evidencia_anterior and evidencia_anterior != medicion.evidencia:
            evidencia_anterior.delete(save=False)

        request = self.context.get('request')
        usuario = request.user if request and request.user.is_authenticated else medicion.registrado_por

        alerta = actualizar_alerta_cumplimiento_kpi(medicion.indicador, medicion_actual=medicion)
        resolver_alertas_periodo_vencido(medicion, usuario=usuario)

        registrar_bitacora(
            usuario=usuario,
            accion='actualizar',
            modulo='mediciones',
            descripcion=(
                f'Se actualizó una medición para el indicador '
                f'"{medicion.indicador.nombre}" con resultado '
                f'{medicion.valor_resultado}.'
            ),
            request=request,
        )

        if alerta:
            registrar_bitacora(
                usuario=usuario,
                accion='crear',
                modulo='alertas',
                descripcion=(
                    f'Se generó o actualizó una alerta automática para el indicador '
                    f'"{medicion.indicador.nombre}".'
                ),
                request=request,
            )

        return medicion


class AlertaSerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(
        source='indicador.nombre',
        read_only=True
    )
    revisado_por_username = serializers.CharField(
        source='revisado_por.username',
        read_only=True
    )

    class Meta:
        model = Alerta
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'medicion',
            'tipo_alerta',
            'mensaje',
            'estado_alerta',
            'fecha_generacion',
            'fecha_revision',
            'revisado_por',
            'revisado_por_username',
        ]
        read_only_fields = ['id', 'fecha_generacion']

