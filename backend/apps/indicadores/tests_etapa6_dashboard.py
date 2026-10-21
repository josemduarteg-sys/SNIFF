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
    def test_a_tiempo_el_dia_del_cierre_y_el_ultimo_dia_del_plazo_ordinario(self):
        dia_cierre = self.medicion(self.kpi, 1, registro=momento(2027, 1, 31))
        self.assertEqual(self.oportunidad(dia_cierre), 'A tiempo')

        Medicion.objects.filter(pk=dia_cierre.pk).update(fecha_registro=momento(2027, 2, 5, 23, 30))
        self.assertEqual(self.oportunidad(dia_cierre), 'A tiempo')

    def test_dentro_del_plazo_ordinario_ya_no_es_retraso(self):
        # Antes de la Etapa 6 esto era "Con retraso" por ser posterior al cierre.
        medicion = self.medicion(self.kpi, 1, registro=momento(2027, 2, 3))

        datos = self.get(f'/api/mediciones/{medicion.id}/').data
        self.assertEqual(datos['oportunidad_registro'], 'A tiempo')
        self.assertFalse(datos['registrada_con_ampliacion'])

    def test_con_ampliacion_autorizada(self):
        self.ampliacion(self.kpi, 1, date(2027, 2, 12))

        for dia in (6, 12):
            medicion = self.medicion(self.kpi, 1, registro=momento(2027, 2, dia))
            datos = self.get(f'/api/mediciones/{medicion.id}/').data
            self.assertEqual(datos['oportunidad_registro'], 'Con ampliación', dia)
            self.assertTrue(datos['registrada_con_ampliacion'])
            medicion.delete()

    def test_despues_del_plazo_efectivo_es_retraso(self):
        sin_ampliacion = self.medicion(self.kpi, 1, registro=momento(2027, 2, 6))
        self.assertEqual(self.oportunidad(sin_ampliacion), 'Con retraso')

        otro = self.crear_kpi('KPI con ampliación')
        self.ampliacion(otro, 1, date(2027, 2, 12))
        tras_ampliacion = self.medicion(otro, 1, registro=momento(2027, 2, 13))
        self.assertEqual(self.oportunidad(tras_ampliacion), 'Con retraso')

    def test_ampliacion_no_autorizada_no_cuenta(self):
        SolicitudAmpliacionPlazo.objects.create(
            indicador=self.kpi, periodo=obtener_o_crear_periodo(self.kpi, date(2027, 1, 1)), solicitante=self.ana,
            motivo='x', dias_solicitados=10, fecha_limite_ordinaria=date(2027, 2, 5), estado='rechazada',
        )
        medicion = self.medicion(self.kpi, 1, registro=momento(2027, 2, 8))

        self.assertEqual(self.oportunidad(medicion), 'Con retraso')

    def test_periodo_sin_registro(self):
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 6)):
            cerrar_mediciones_vencidas()

        omision = Medicion.objects.get(indicador=self.kpi, cierre_automatico=True)
        datos = self.get(f'/api/mediciones/{omision.id}/').data
        self.assertEqual(datos['oportunidad_registro'], 'Sin registro')
        self.assertFalse(datos['registrada_con_ampliacion'])

    def test_una_sola_categoria_por_medicion_en_el_listado(self):
        self.ampliacion(self.kpi, 2, date(2027, 3, 12))
        self.medicion(self.kpi, 1, registro=momento(2027, 2, 2))
        Medicion.objects.filter(indicador=self.kpi).delete()
        self.medicion(self.kpi, 1, registro=momento(2027, 2, 2))
        self.medicion(self.kpi, 3, registro=momento(2027, 4, 20))

        listado = self.get('/api/mediciones/').data
        categorias = {m['oportunidad_registro'] for m in listado}

        self.assertEqual(len(listado), 2)
        self.assertTrue(categorias <= {'A tiempo', 'Con retraso', 'Con ampliación', 'Sin registro'})

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
