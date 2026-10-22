"""Etapa 6: oportunidad de registro (M5), rendimiento de los listados de KPI
y mediciones (M8) y datos que usan el Dashboard y la navegación desde
notificaciones.

Calendario: KPI mensual 2027, plazo general de 5 días. Enero cierra el
31/01 y su plazo ordinario termina el 05/02."""

import json
from datetime import date, datetime
from decimal import Decimal
from unittest import mock

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APITestCase

from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.usuarios.models import Rol, Usuario

from .models import (
    Alerta,
    EstadoCumplimiento,
    Frecuencia,
    IndicadorKPI,
    Medicion,
    RangoKPI,
    ResponsableKPI,
    SolicitudAmpliacionPlazo,
)
from .serializers import IndicadorKPISerializer, MedicionSerializer
from .services import (
    cerrar_mediciones_vencidas,
    crear_rangos_provisionales,
    obtener_o_crear_meta_vigente,
    obtener_o_crear_periodo,
)

HOY = date(2027, 2, 3)


def crear_usuario(username, rol_nombre, **extra):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123', **extra)
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


def momento(anio, mes, dia, hora=10, minuto=0):
    return timezone.make_aware(datetime(anio, mes, dia, hora, minuto))


class Etapa6Base(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('admin_e6', 'Administrador de planificación')
        self.ana = crear_usuario('ana_e6', 'Ejecutor operativo')
        self.consulta = crear_usuario('consulta_e6', 'Usuario de consulta')
        self.sistema = crear_usuario('sistema_e6', 'Administrador del sistema')

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.favorable = EstadoCumplimiento.objects.get(nombre='Favorable')
        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)
        self.plan = PlanEstrategico.objects.create(
            titulo='Plan e6', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan, texto_objetivo='OG', creado_por=self.admin,
        )
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual, objetivo_general=self.objetivo_general,
            texto_objetivo='OE', creado_por=self.admin,
        )
        self.kpi = self.crear_kpi('KPI cartera')

    def crear_kpi(self, nombre, estado='autorizado', ponderacion=None):
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico, frecuencia=self.frecuencia, nombre=nombre,
            formula_medicion='Resultado', unidad_medida='%', valor_meta=Decimal('85'),
            estado=estado, creado_por=self.admin, ponderacion=ponderacion,
        )
        crear_rangos_provisionales(kpi)
        return kpi

    def medicion(self, kpi, mes, valor='90', registro=None, automatica=False):
        medicion = Medicion.objects.create(
            indicador=kpi,
            meta=obtener_o_crear_meta_vigente(kpi),
            periodo=obtener_o_crear_periodo(kpi, date(2027, mes, 1)),
            estado_cumplimiento=self.favorable,
            fecha_medicion=obtener_o_crear_periodo(kpi, date(2027, mes, 1)).fecha_fin,
            valor_resultado=None if automatica else Decimal(valor),
            cierre_automatico=automatica,
            registrado_por=None if automatica else self.ana,
        )

        if registro is not None:
            # fecha_registro es auto_now_add: se fija la del escenario.
            Medicion.objects.filter(pk=medicion.pk).update(fecha_registro=registro)
            medicion.refresh_from_db()

        return medicion

    def ampliacion(self, kpi, mes, extraordinaria):
        from datetime import timedelta

        periodo = obtener_o_crear_periodo(kpi, date(2027, mes, 1))
        ordinaria = periodo.fecha_fin + timedelta(days=5)

        return SolicitudAmpliacionPlazo.objects.create(
            indicador=kpi, periodo=periodo, solicitante=self.ana,
            motivo='x', dias_solicitados=10, dias_autorizados=(extraordinaria - ordinaria).days,
            fecha_limite_ordinaria=ordinaria, fecha_limite_extraordinaria=extraordinaria,
            estado='autorizada', revisado_por=self.admin,
        )

    def get(self, url, usuario=None, fecha=HOY):
        self.client.force_authenticate(user=usuario or self.consulta)

        with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
            return self.client.get(url)

    def oportunidad(self, medicion):
        return self.get(f'/api/mediciones/{medicion.id}/').data['oportunidad_registro']


class OportunidadRegistroTests(Etapa6Base):
    """Criterio de Hernán (06/10/2026): días entre el cierre del periodo
    (31/01/2027) y el registro. Oportuno día 0, Demorado días 1 y 2, Tardío
    del día 3 al vencimiento, Fuera de plazo después del plazo efectivo y
    Sin registro para los periodos cerrados sin medición."""

    def registrada_el(self, dia_febrero=None, kpi=None, mes=1, **momento_extra):
        registro = momento(2027, 1, 31, **momento_extra) if dia_febrero is None else momento(2027, 2, dia_febrero, **momento_extra)
        return self.medicion(kpi or self.kpi, mes, registro=registro)

    def datos(self, medicion):
        return self.get(f'/api/mediciones/{medicion.id}/').data

    def assertOportunidad(self, medicion, categoria, con_ampliacion=False):
        datos = self.datos(medicion)
        self.assertEqual(datos['oportunidad_registro'], categoria)
        self.assertEqual(datos['registrada_con_ampliacion'], con_ampliacion)

    def test_dia_0_oportuno(self):
        self.assertOportunidad(self.registrada_el(), 'Oportuno')

    def test_dia_0_al_final_del_dia_en_hora_de_guatemala(self):
        # 31/01 a las 23:30 en Guatemala (05:30 del 01/02 en UTC) sigue siendo el día 0.
        self.assertOportunidad(self.registrada_el(hora=23, minuto=30), 'Oportuno')

    def test_dias_1_y_2_demorado(self):
        for dia in (1, 2):
            medicion = self.registrada_el(dia)
            self.assertOportunidad(medicion, 'Demorado')
            medicion.delete()

    def test_dias_3_4_y_5_tardio(self):
        for dia in (3, 4, 5):
            medicion = self.registrada_el(dia)
            self.assertOportunidad(medicion, 'Tardío')
            medicion.delete()

    def test_plazo_ordinario_de_diez_dias_mantiene_los_umbrales(self):
        from .models import ConfiguracionMediciones

        configuracion = ConfiguracionMediciones.obtener()
        configuracion.dias_plazo_registro = 10
        configuracion.save()

        for dia, categoria in ((1, 'Demorado'), (3, 'Tardío'), (9, 'Tardío'), (10, 'Tardío'), (11, 'Fuera de plazo')):
            medicion = self.registrada_el(dia)
            self.assertOportunidad(medicion, categoria)
            medicion.delete()

    def test_registro_dentro_de_una_ampliacion_autorizada_es_tardio_e_identificado(self):
        self.ampliacion(self.kpi, 1, date(2027, 2, 12))

        for dia in (6, 12):
            medicion = self.registrada_el(dia)
            self.assertOportunidad(medicion, 'Tardío', con_ampliacion=True)
            medicion.delete()

        # Dentro del plazo ordinario no cuenta como ampliación aunque exista una.
        dentro = self.registrada_el(4)
        self.assertOportunidad(dentro, 'Tardío', con_ampliacion=False)

    def test_despues_del_plazo_efectivo_es_fuera_de_plazo(self):
        self.assertOportunidad(self.registrada_el(6), 'Fuera de plazo')

        otro = self.crear_kpi('KPI con ampliación')
        self.ampliacion(otro, 1, date(2027, 2, 12))
        self.assertOportunidad(self.registrada_el(13, kpi=otro), 'Fuera de plazo')

    def test_ampliacion_no_autorizada_no_cuenta(self):
        SolicitudAmpliacionPlazo.objects.create(
            indicador=self.kpi, periodo=obtener_o_crear_periodo(self.kpi, date(2027, 1, 1)), solicitante=self.ana,
            motivo='x', dias_solicitados=10, fecha_limite_ordinaria=date(2027, 2, 5), estado='rechazada',
        )

        self.assertOportunidad(self.registrada_el(8), 'Fuera de plazo')

    def test_periodo_cerrado_sin_registro(self):
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 6)):
            cerrar_mediciones_vencidas()

        omision = Medicion.objects.get(indicador=self.kpi, cierre_automatico=True)
        self.assertOportunidad(omision, 'Sin registro')

    def test_datos_historicos_retroactivos_son_fuera_de_plazo(self):
        """Como las 22 mediciones reales: KPI creado en septiembre con sus
        periodos de enero a agosto registrados ese mismo día."""
        retroactivas = [self.medicion(self.kpi, mes, registro=momento(2027, 9, 27)) for mes in range(1, 9)]
        registro_original = [m.fecha_registro for m in retroactivas]

        listado = {m['id']: m for m in self.get('/api/mediciones/').data}

        self.assertEqual({listado[m.id]['oportunidad_registro'] for m in retroactivas}, {'Fuera de plazo'})
        # La consulta no modifica la fecha original de registro.
        for medicion, original in zip(retroactivas, registro_original):
            medicion.refresh_from_db()
            self.assertEqual(medicion.fecha_registro, original)

    def test_una_sola_categoria_por_medicion_en_el_listado(self):
        self.ampliacion(self.kpi, 3, date(2027, 4, 12))
        self.registrada_el()
        self.medicion(self.kpi, 2, registro=momento(2027, 3, 1))
        self.medicion(self.kpi, 3, registro=momento(2027, 4, 10))
        self.medicion(self.kpi, 4, registro=momento(2027, 6, 1))

        categorias = [m['oportunidad_registro'] for m in sorted(self.get('/api/mediciones/').data, key=lambda m: m['fecha_medicion'])]

        self.assertEqual(categorias, ['Oportuno', 'Demorado', 'Tardío', 'Fuera de plazo'])

    def test_la_categoria_no_cambia_resultados_ni_promedios(self):
        self.medicion(self.kpi, 1, valor='80', registro=momento(2027, 2, 2))
        self.medicion(self.kpi, 2, valor='60', registro=momento(2027, 4, 1))

        kpi = self.get(f'/api/indicadores-kpi/{self.kpi.id}/').data
        self.assertEqual(Decimal(str(kpi['promedio_acumulado'])), Decimal('70.00'))
        self.assertEqual(kpi['cantidad_mediciones'], 2)


class ConsultasYEquivalenciaTests(Etapa6Base):
    """M8: los listados usan datos precargados. Se comprueba que la
    respuesta es idéntica a serializar cada objeto por separado (sin
    precarga) y que la cantidad de consultas no crece con los KPI."""

    def armar_escenario(self, cantidad_kpi):
        estado_pendiente, _ = EstadoCumplimiento.objects.get_or_create(
            nombre='Pendiente de actualización', defaults={'color': 'gris', 'estado': True},
        )
        inactivo = crear_usuario(f'inactivo_{cantidad_kpi}', 'Ejecutor operativo')
        inactivo.is_active = False
        inactivo.save()

        kpis = [self.kpi] + [self.crear_kpi(f'KPI {i}', ponderacion=Decimal('10')) for i in range(cantidad_kpi - 1)]
        self.crear_kpi('KPI anulado', estado='anulado', ponderacion=Decimal('30'))
        self.crear_kpi('KPI borrador', estado='borrador', ponderacion=Decimal('5'))

        for indice, kpi in enumerate(kpis):
            ResponsableKPI.objects.create(indicador=kpi, usuario=self.ana)
            ResponsableKPI.objects.create(indicador=kpi, usuario=inactivo)
            self.medicion(kpi, 1, valor=str(70 + indice), registro=momento(2027, 2, 2))
            self.medicion(kpi, 2, automatica=True)
            self.medicion(kpi, 3, valor='120', registro=momento(2027, 4, 2))
            Alerta.objects.create(indicador=kpi, tipo_alerta='Periodo vencido sin medición', mensaje='x')

        # Un KPI sin rangos activos (estado "Pendiente de actualización").
        RangoKPI.objects.filter(indicador=kpis[-1]).update(estado=False)
        # Una ampliación autorizada para el siguiente periodo de un KPI.
        self.ampliacion(kpis[0], 4, date(2027, 5, 15))
        return kpis, estado_pendiente

    def como_json(self, datos):
        return json.loads(JSONRenderer().render(datos))

    def test_listado_de_kpi_identico_sin_precarga(self):
        self.armar_escenario(4)

        listado = self.get('/api/indicadores-kpi/', fecha=date(2027, 5, 10)).json()

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 5, 10)):
            esperado = [
                self.como_json(IndicadorKPISerializer(IndicadorKPI.objects.get(pk=fila['id'])).data)
                for fila in listado
            ]

        self.assertEqual(len(listado), 6)
        self.assertEqual(listado, esperado)
        self.assertTrue(any(f['estado_acumulado_nombre'] == 'Pendiente de actualización' for f in listado))
        self.assertTrue(all(f['cantidad_responsables'] in (0, 1) for f in listado))

    def test_listado_de_mediciones_identico_sin_precarga(self):
        self.armar_escenario(3)

        listado = self.get('/api/mediciones/').json()
        esperado = [self.como_json(MedicionSerializer(Medicion.objects.get(pk=fila['id'])).data) for fila in listado]

        self.assertEqual(listado, esperado)

    def contar(self, url):
        with CaptureQueriesContext(connection) as contexto:
            self.assertEqual(self.get(url, fecha=date(2027, 5, 10)).status_code, status.HTTP_200_OK)

        # Sin el SAVEPOINT / RELEASE de la transacción de cada petición.
        return len([q for q in contexto.captured_queries if 'SAVEPOINT' not in q['sql']])

    def test_las_consultas_no_crecen_con_los_kpi(self):
        self.armar_escenario(2)
        pocos = {url: self.contar(url) for url in ('/api/indicadores-kpi/', '/api/mediciones/')}

        for i in range(6):
            kpi = self.crear_kpi(f'KPI extra {i}')
            self.medicion(kpi, 1, registro=momento(2027, 2, 2))
            self.medicion(kpi, 2, automatica=True)

        muchos = {url: self.contar(url) for url in ('/api/indicadores-kpi/', '/api/mediciones/')}

        self.assertEqual(pocos, muchos)
        # Antes de la Etapa 6: ~10 consultas por KPI y ~2 por medición.
        self.assertLessEqual(muchos['/api/indicadores-kpi/'], 10)
        self.assertLessEqual(muchos['/api/mediciones/'], 8)


class IntegridadYPermisosTests(Etapa6Base):
    CAMPOS_KPI = {
        'id', 'plan_anual', 'plan_estrategico', 'promedio_acumulado', 'cantidad_mediciones',
        'cantidad_omisiones', 'cantidad_responsables', 'estado_acumulado_nombre', 'periodo_disponible',
        'periodo_disponible_motivo', 'ponderacion_total_ambito', 'ponderacion_pendiente_ambito',
    }
    CAMPOS_MEDICION = {
        'id', 'indicador', 'cierre_automatico', 'fecha_medicion', 'fecha_registro', 'tiene_evidencia',
        'registrada_con_ampliacion', 'oportunidad_registro', 'promedio_acumulado_hasta_medicion',
    }

    def test_las_respuestas_conservan_sus_campos(self):
        self.medicion(self.kpi, 1, registro=momento(2027, 2, 2))

        kpi = self.get('/api/indicadores-kpi/').data[0]
        medicion = self.get('/api/mediciones/').data[0]

        self.assertTrue(self.CAMPOS_KPI <= set(kpi))
        self.assertTrue(self.CAMPOS_MEDICION <= set(medicion))
        self.assertEqual(kpi['plan_anual'], self.plan_anual.id)
        self.assertEqual(kpi['plan_estrategico'], self.plan.id)

    def test_cuatro_roles_leen_kpi_mediciones_y_alertas_como_antes(self):
        alerta = Alerta.objects.create(indicador=self.kpi, tipo_alerta='Periodo vencido sin medición', mensaje='x')

        for usuario in (self.admin, self.ana, self.consulta, self.sistema):
            for url in ('/api/indicadores-kpi/', '/api/mediciones/', f'/api/alertas/{alerta.id}/'):
                self.assertEqual(self.get(url, usuario=usuario).status_code, status.HTTP_200_OK, (usuario, url))

        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(f'/api/alertas/{alerta.id}/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_alerta_inexistente_responde_404(self):
        self.assertEqual(self.get('/api/alertas/999999/').status_code, status.HTTP_404_NOT_FOUND)

    def test_alerta_de_periodo_sin_avisos_individuales(self):
        """Los avisos a responsables (que usaban /mediciones?indicador=&alerta=)
        se retiraron del flujo; la alerta se sigue creando y puede consultarse,
        y la pantalla de Mediciones sigue interpretando esos enlaces si existen."""
        ResponsableKPI.objects.create(indicador=self.kpi, usuario=self.ana)

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 1)):
            from .services import generar_alertas_periodos_vencidos

            generar_alertas_periodos_vencidos()

        alerta = Alerta.objects.get(indicador=self.kpi)

        from apps.auditoria.models import Notificacion

        self.assertFalse(Notificacion.objects.filter(usuario_destino=self.ana).exists())
        self.assertEqual(self.get(f'/api/alertas/{alerta.id}/', usuario=self.ana).data['indicador'], self.kpi.id)
