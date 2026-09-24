from datetime import date
from rest_framework import serializers

from .models import (
    Frecuencia,
    TipoCalculo,
    FuenteDato,
    IndicadorKPI,
    MetaKPI,
    ResponsableKPI,
    EstadoCumplimiento,
    RangoKPI,
    PeriodoMedicion,
    Medicion,
    Alerta,
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


class TipoCalculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCalculo
        fields = [
            'id',
            'nombre',
            'descripcion',
            'estado',
        ]
        read_only_fields = ['id']


class FuenteDatoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuenteDato
        fields = [
            'id',
            'nombre',
            'descripcion',
            'estado',
        ]
        read_only_fields = ['id']


class IndicadorKPISerializer(serializers.ModelSerializer):
    # source actualizado tras el rename Objetivo->ObjetivoGeneral (Bloque 1
    # del rediseño): ObjetivoGeneral ya no tiene `nombre`, tiene
    # `texto_objetivo`. Se mantiene el nombre de campo `objetivo_nombre`
    # para no romper el frontend que ya lo consume.
    objetivo_nombre = serializers.CharField(source='objetivo.texto_objetivo', read_only=True)
    frecuencia_nombre = serializers.CharField(source='frecuencia.nombre', read_only=True)
    tipo_calculo_nombre = serializers.CharField(source='tipo_calculo.nombre', read_only=True)
    fuente_dato_nombre = serializers.CharField(source='fuente_dato.nombre', read_only=True)
    autorizado_por_username = serializers.CharField(source='autorizado_por.username', read_only=True)
    creado_por_username = serializers.CharField(source='creado_por.username', read_only=True)
    puede_modificarse = serializers.SerializerMethodField()

    class Meta:
        model = IndicadorKPI
        fields = [
            'id',
            'objetivo',
            'objetivo_nombre',
            'frecuencia',
            'frecuencia_nombre',
            'tipo_calculo',
            'tipo_calculo_nombre',
            'fuente_dato',
            'fuente_dato_nombre',
            'nombre',
            'descripcion',
            'unidad_medida',
            'valor_meta',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'fecha_autorizacion',
            'autorizado_por',
            'autorizado_por_username',
            'creado_por',
            'creado_por_username',
            'puede_modificarse',
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
        ]

    def get_puede_modificarse(self, obj):
        return obj.puede_modificarse()

    def validate(self, attrs):
        instance = self.instance

        if instance and not instance.puede_modificarse():
            campos_bloqueados = {
                'objetivo',
                'frecuencia',
                'tipo_calculo',
                'fuente_dato',
                'nombre',
                'descripcion',
                'unidad_medida',
                'valor_meta',
                'fecha_inicio',
                'fecha_fin',
            }

            campos_intentados = campos_bloqueados.intersection(set(attrs.keys()))

            if campos_intentados:
                raise serializers.ValidationError(
                    'El KPI ya está autorizado y no permite modificar sus datos principales.'
                )

        fecha_inicio = attrs.get('fecha_inicio', getattr(instance, 'fecha_inicio', None))
        fecha_fin = attrs.get('fecha_fin', getattr(instance, 'fecha_fin', None))

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                'La fecha de finalización no puede ser anterior a la fecha de inicio.'
            )

        unidad_medida = attrs.get('unidad_medida', getattr(instance, 'unidad_medida', None))
        valor_meta = attrs.get('valor_meta')

        if valor_meta is None and instance is not None and 'valor_meta' not in attrs:
            valor_meta = instance.valor_meta

        if unidad_medida == '%' and valor_meta is not None:
            if valor_meta < 0 or valor_meta > 100:
                raise serializers.ValidationError({
                    'valor_meta': 'Cuando la unidad de medida es porcentaje, la meta debe estar entre 0 y 100.'
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
    mes_medicion = serializers.CharField(write_only=True, required=False, allow_blank=True)
    indicador_nombre = serializers.CharField(source='indicador.nombre', read_only=True)
    unidad_medida = serializers.CharField(source='indicador.unidad_medida', read_only=True)
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
        read_only=True
    )
    porcentaje_cumplimiento = serializers.SerializerMethodField()

    class Meta:
        model = Medicion
        fields = [
            'id',
            'indicador',
            'indicador_nombre',
            'unidad_medida',
            'meta',
            'valor_meta',
            'estado_cumplimiento',
            'estado_cumplimiento_nombre',
            'estado_cumplimiento_color',
            'periodo',
            'periodo_nombre',
            'mes_medicion',
            'registrado_por',
            'registrado_por_username',
            'archivo_importado',
            'consulta_dw',
            'fecha_medicion',
            'valor_resultado',
            'porcentaje_cumplimiento',
            'observacion',
            'observaciones',
            'evidencia',
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
            'periodo_nombre',
            'valor_meta',
            'observaciones',
            'registrado_por',
            'registrado_por_username',
        ]

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

    def obtener_fechas_mes(self, mes_medicion):
        try:
            anio_texto, mes_texto = mes_medicion.split('-')
            anio = int(anio_texto)
            mes = int(mes_texto)
        except (ValueError, AttributeError):
            raise serializers.ValidationError({
                'mes_medicion': 'El mes de medición debe tener formato YYYY-MM.'
            })

        if mes < 1 or mes > 12:
            raise serializers.ValidationError({
                'mes_medicion': 'El mes de medición no es válido.'
            })

        fecha_inicio = date(anio, mes, 1)

        if mes == 12:
            fecha_fin = date(anio, 12, 31)
        else:
            fecha_fin = date(anio, mes + 1, 1) - date.resolution

        return anio, mes, fecha_inicio, fecha_fin

    def obtener_o_crear_periodo_mensual(self, mes_medicion):
        anio, mes, fecha_inicio, fecha_fin = self.obtener_fechas_mes(mes_medicion)

        periodo, _ = PeriodoMedicion.objects.get_or_create(
            tipo_periodo='mensual',
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            defaults={
                'anio': anio,
                'mes': mes,
                'descripcion': f'Periodo {mes:02d}/{anio}',
            }
        )

        return periodo

    def obtener_o_crear_meta_para_indicador(self, indicador):
        meta_existente = MetaKPI.objects.filter(
            indicador=indicador,
            estado='vigente',
        ).order_by('-fecha_inicio').first()

        if meta_existente:
            return meta_existente

        if indicador.valor_meta is None:
            raise serializers.ValidationError({
                'indicador': 'El KPI seleccionado no tiene una meta configurada.'
            })

        if not indicador.fecha_inicio:
            raise serializers.ValidationError({
                'indicador': 'El KPI seleccionado no tiene fecha de inicio configurada.'
            })

        meta, _ = MetaKPI.objects.get_or_create(
            indicador=indicador,
            valor_meta=indicador.valor_meta,
            fecha_inicio=indicador.fecha_inicio,
            fecha_fin=indicador.fecha_fin,
            estado='vigente',
        )

        return meta

    def preparar_datos_mensuales(self, attrs):
        from .services import formatear_periodo, obtener_siguiente_periodo_esperado

        indicador = attrs.get('indicador') or getattr(self.instance, 'indicador', None)
        mes_medicion = attrs.pop('mes_medicion', None)

        if not indicador:
            raise serializers.ValidationError({
                'indicador': 'Seleccioná el KPI.'
            })

        meta = self.obtener_o_crear_meta_para_indicador(indicador)
        attrs['meta'] = meta

        if mes_medicion:
            periodo = self.obtener_o_crear_periodo_mensual(mes_medicion)
            attrs['periodo'] = periodo
            attrs['fecha_medicion'] = periodo.fecha_fin

            fecha_periodo = periodo.fecha_inicio

            fecha_inicio_kpi = date(
                indicador.fecha_inicio.year,
                indicador.fecha_inicio.month,
                1,
            )

            fecha_fin_kpi = date(
                indicador.fecha_fin.year,
                indicador.fecha_fin.month,
                1,
            )

            if fecha_periodo < fecha_inicio_kpi or fecha_periodo > fecha_fin_kpi:
                raise serializers.ValidationError({
                    'mes_medicion': 'El periodo seleccionado está fuera de la vigencia del KPI.'
                })

            medicion_existente = Medicion.objects.filter(
                indicador=indicador,
                periodo=periodo,
            ).exclude(
                id=self.instance.id if self.instance else None
            ).exists()

            if medicion_existente:
                raise serializers.ValidationError({
                    'mes_medicion': 'Ya existe una medición registrada para este KPI en el mes seleccionado.'
                })

            es_edicion_mismo_periodo = (
                self.instance is not None
                and getattr(self.instance, 'periodo_id', None) == periodo.id
            )

            if not es_edicion_mismo_periodo:
                periodo_esperado = obtener_siguiente_periodo_esperado(
                    indicador,
                    excluir_medicion_id=self.instance.id if self.instance else None,
                )

                if fecha_periodo != periodo_esperado:
                    raise serializers.ValidationError({
                        'mes_medicion': (
                            f'El siguiente periodo esperado para este KPI es '
                            f'{formatear_periodo(periodo_esperado)}. '
                            f'No se puede registrar {formatear_periodo(fecha_periodo)} '
                            f'porque hay periodos anteriores pendientes.'
                        )
                    })
        elif not self.instance:
            raise serializers.ValidationError({
                'mes_medicion': 'Seleccioná el mes que se va a medir.'
            })

        return attrs

    def validate(self, attrs):
        indicador = attrs.get('indicador') or getattr(self.instance, 'indicador', None)

        if not indicador:
            raise serializers.ValidationError({
                'indicador': 'Debe seleccionar un KPI.'
            })

        if indicador.estado != 'autorizado':
            raise serializers.ValidationError({
                'indicador': 'Solo se pueden registrar mediciones para KPI activos.'
            })

        if not indicador.valor_meta:
            raise serializers.ValidationError({
                'indicador': 'El KPI seleccionado no tiene una meta configurada.'
            })

        if not indicador.fecha_inicio or not indicador.fecha_fin:
            raise serializers.ValidationError({
                'indicador': 'El KPI seleccionado no tiene vigencia configurada.'
            })

        valor_resultado = attrs.get('valor_resultado')

        if valor_resultado is None and self.instance is not None and 'valor_resultado' not in attrs:
            valor_resultado = self.instance.valor_resultado

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

        attrs = self.preparar_datos_mensuales(attrs)

        indicador = attrs.get('indicador') or getattr(self.instance, 'indicador', None)
        meta = attrs.get('meta') or getattr(self.instance, 'meta', None)

        if indicador and meta and meta.indicador_id != indicador.id:
            raise serializers.ValidationError(
                'La meta seleccionada no pertenece al indicador indicado.'
            )

        return attrs

    def create(self, validated_data):
        from apps.auditoria.services import registrar_bitacora
        from .services import (
            generar_alerta_para_medicion,
            obtener_estado_para_medicion,
            resolver_alertas_periodo_vencido,
        )

        indicador = validated_data.get('indicador')
        meta = validated_data.get('meta')
        valor_resultado = validated_data.get('valor_resultado')

        estado = obtener_estado_para_medicion(
            indicador=indicador,
            meta=meta,
            valor_resultado=valor_resultado,
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

        alerta = generar_alerta_para_medicion(medicion)
        resolver_alertas_periodo_vencido(medicion, usuario=usuario)

        registrar_bitacora(
            usuario=usuario,
            accion='crear',
            modulo='mediciones',
            descripcion=(
                f'Se registró una medición para el indicador '
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
                    f'Se generó una alerta automática para el indicador '
                    f'"{medicion.indicador.nombre}".'
                ),
                request=request,
            )

        return medicion

    def update(self, instance, validated_data):
        from apps.auditoria.services import registrar_bitacora
        from .services import (
            generar_alerta_para_medicion,
            obtener_estado_para_medicion,
            resolver_alertas_periodo_vencido,
        )

        indicador = validated_data.get('indicador', instance.indicador)
        meta = validated_data.get('meta', instance.meta)
        valor_resultado = validated_data.get(
            'valor_resultado',
            instance.valor_resultado
        )

        estado = obtener_estado_para_medicion(
            indicador=indicador,
            meta=meta,
            valor_resultado=valor_resultado,
        )

        if estado is None:
            raise serializers.ValidationError(
                'No se encontró un estado de cumplimiento válido para esta medición.'
            )

        validated_data['estado_cumplimiento'] = estado

        medicion = super().update(instance, validated_data)

        request = self.context.get('request')
        usuario = request.user if request and request.user.is_authenticated else medicion.registrado_por

        alerta = generar_alerta_para_medicion(medicion)
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

