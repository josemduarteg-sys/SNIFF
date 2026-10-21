"""Etapa 4 (cierre): bitácora de procesos automáticos — usuario NULL solo
para eventos del sistema, visibles como "Sistema". Hallazgo M7."""

from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework import status
from rest_framework.test import APITestCase

from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.indicadores.models import EstadoCumplimiento, Frecuencia, IndicadorKPI, Medicion
from apps.indicadores.services import crear_rangos_provisionales
from apps.usuarios.models import Rol, Usuario

from .models import Bitacora
from .services import (
    MODULO_TAREAS_AUTOMATICAS,
    registrar_bitacora,
    registrar_bitacora_obligatoria,
    registrar_bitacora_seguro,
    registrar_bitacora_sistema,
)


def crear_usuario(username, rol_nombre, **extra):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123', **extra)
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class BitacoraSistemaBase(APITestCase):
    def setUp(self):
        self.admin_sistema = crear_usuario('admin_bitacora_sistema', 'Administrador del sistema')
        self.admin = crear_usuario('admin_planif_sistema', 'Administrador de planificación')

    def crear_kpi_autorizado(self):
        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        plan = PlanEstrategico.objects.create(
            titulo='Plan sistema', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        objetivo_general = ObjetivoGeneral.objects.create(plan_estrategico=plan, texto_objetivo='OG', creado_por=self.admin)
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )
        objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual, objetivo_general=objetivo_general, texto_objetivo='OE', creado_por=self.admin,
        )
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=objetivo_especifico, frecuencia=Frecuencia.objects.create(nombre='Mensual', estado=True),
            nombre='KPI tareas', formula_medicion='Resultado', unidad_medida='%', valor_meta=Decimal('85'),
            estado='autorizado', creado_por=self.admin,
        )
        crear_rangos_provisionales(kpi)
        return kpi

    def registros_sistema(self):
        return Bitacora.objects.filter(usuario__isnull=True, modulo=MODULO_TAREAS_AUTOMATICAS)


class UsuarioNuloSoloParaSistemaTests(BitacoraSistemaBase):
    def test_registro_del_sistema_queda_sin_usuario_ni_ip(self):
        registro = registrar_bitacora_sistema('actualizar', 'Tareas automáticas', 'Prueba')

        registro.refresh_from_db()
        self.assertIsNone(registro.usuario)
        self.assertIsNone(registro.ip_usuario)
        self.assertEqual(registro.origen, 'sistema')
        self.assertEqual(registro.autor, 'Sistema')
        self.assertEqual(str(registro), 'Sistema - actualizar - Tareas automáticas')

    def test_las_acciones_de_usuario_siguen_exigiendo_un_usuario(self):
        for funcion in (registrar_bitacora, registrar_bitacora_obligatoria):
            with self.assertRaises(ValueError):
                funcion(usuario=None, accion='crear', modulo='X', descripcion='Sin usuario')

        # La variante "segura" no interrumpe, pero tampoco crea una fila sin usuario.
        self.assertIsNone(registrar_bitacora_seguro(usuario=None, accion='crear', modulo='X', descripcion='Sin usuario'))
        self.assertFalse(Bitacora.objects.filter(usuario__isnull=True).exists())

    def test_registros_de_usuarios_conservan_su_usuario(self):
        humano = registrar_bitacora(self.admin, 'crear', 'Áreas', 'Creó el área X.')
        registrar_bitacora_sistema('actualizar', 'Tareas automáticas', 'Evento')

        humano.refresh_from_db()
        self.assertEqual(humano.usuario, self.admin)
        self.assertEqual(humano.origen, 'usuario')
        self.assertEqual(humano.autor, self.admin.username)


class ConsultaBitacoraTests(BitacoraSistemaBase):
    def setUp(self):
        super().setUp()
        self.humano = registrar_bitacora(self.admin, 'crear', 'Áreas', 'Creó el área X.')
        self.sistema = registrar_bitacora_sistema('actualizar', 'Tareas automáticas', 'Ejecución diaria')
        self.client.force_authenticate(user=self.admin_sistema)

    def ids(self, response):
        return {r['id'] for r in response.data}

    def test_la_api_muestra_sistema_y_origen(self):
        registros = {r['id']: r for r in self.client.get('/api/bitacora/').data}

        self.assertEqual(registros[self.sistema.id]['origen'], 'sistema')
        self.assertEqual(registros[self.sistema.id]['autor'], 'Sistema')
        self.assertIsNone(registros[self.sistema.id]['usuario'])
        self.assertIsNone(registros[self.sistema.id]['usuario_username'])
        self.assertEqual(registros[self.humano.id]['origen'], 'usuario')
        self.assertEqual(registros[self.humano.id]['usuario_username'], self.admin.username)

    def test_filtro_por_origen(self):
        self.assertEqual(self.ids(self.client.get('/api/bitacora/', {'origen': 'sistema'})), {self.sistema.id})
        self.assertEqual(self.ids(self.client.get('/api/bitacora/', {'origen': 'usuario'})), {self.humano.id})
        self.assertEqual(self.ids(self.client.get('/api/bitacora/')), {self.sistema.id, self.humano.id})

    def test_solo_el_administrador_del_sistema_consulta_la_bitacora(self):
        for rol in ('Administrador de planificación', 'Ejecutor operativo', 'Usuario de consulta'):
            self.client.force_authenticate(user=crear_usuario(f'sin_bitacora_{rol[:5]}', rol))
            self.assertEqual(self.client.get('/api/bitacora/', {'origen': 'sistema'}).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_de_django_lista_y_filtra_eventos_del_sistema(self):
        superusuario = Usuario.objects.create_superuser('super_admin_bitacora', 'super@sniff.test', 'clave-prueba-123')
        self.client.force_login(superusuario)

        respuesta = self.client.get('/admin/auditoria/bitacora/', {'origen': 'sistema'})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Sistema')


class TareasAutomaticasEnBitacoraTests(BitacoraSistemaBase):
    def ejecutar(self, comando, *argumentos, fecha=date(2027, 4, 3)):
        salida = StringIO()

        with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
            call_command(comando, *argumentos, stdout=salida)

        return salida.getvalue()

    def test_ejecucion_real_de_la_tarea_diaria_queda_registrada(self):
        self.crear_kpi_autorizado()

        self.ejecutar('ejecutar_tareas_mediciones')

        registro = self.registros_sistema().get()
        self.assertEqual(registro.accion, 'actualizar')
        self.assertIn('Tareas diarias de mediciones', registro.descripcion)
        self.assertIn('Cierres automáticos: 2', registro.descripcion)
        self.assertIn('Alertas creadas: 1', registro.descripcion)
        self.assertIn('Errores de cierre: 0', registro.descripcion)

    def test_la_simulacion_no_escribe_bitacora(self):
        self.crear_kpi_autorizado()

        self.ejecutar('ejecutar_tareas_mediciones', '--simular')
        self.ejecutar('cerrar_mediciones_vencidas', '--simular')

        self.assertFalse(Bitacora.objects.exists())

    def test_cada_comando_automatico_registra_su_ejecucion(self):
        self.crear_kpi_autorizado()

        self.ejecutar('cerrar_mediciones_vencidas')
        self.ejecutar('generar_alertas_periodos_vencidos')
        self.ejecutar('generar_recordatorios_pendientes')

        descripciones = list(self.registros_sistema().order_by('id').values_list('descripcion', flat=True))
        self.assertEqual(len(descripciones), 3)
        self.assertTrue(descripciones[0].startswith('Cierre de mediciones vencidas:'))
        self.assertTrue(descripciones[1].startswith('Alertas de periodos vencidos:'))
        self.assertTrue(descripciones[2].startswith('Recordatorios de pendientes:'))

    def test_errores_de_la_tarea_quedan_como_error(self):
        resultado_con_error = {
            'kpi_revisados': 1, 'cierres_creados': 0, 'kpi_bloqueados': 0, 'detalle': [],
            'errores': [{'indicador_id': 1, 'indicador': 'KPI', 'periodo': 'enero 2027', 'error': 'falla'}],
        }

        with mock.patch(
            'apps.indicadores.management.commands.ejecutar_tareas_mediciones.cerrar_mediciones_vencidas',
            return_value=resultado_con_error,
        ), self.assertRaises(CommandError):
            call_command('ejecutar_tareas_mediciones', stdout=StringIO())

        registro = self.registros_sistema().get()
        self.assertEqual(registro.accion, 'error')
        self.assertIn('Errores de cierre: 1', registro.descripcion)

    def test_fallo_de_bitacora_tras_la_tarea_no_revierte_ni_repite(self):
        kpi = self.crear_kpi_autorizado()

        with mock.patch(
            'apps.auditoria.services.registrar_bitacora_sistema', side_effect=RuntimeError('BD caída'),
        ), self.assertRaises(CommandError) as contexto:
            self.ejecutar('ejecutar_tareas_mediciones')

        mensaje = str(contexto.exception)
        self.assertIn('ya quedaron guardadas', mensaje)
        self.assertIn('No se revirtió ni se repitió nada', mensaje)
        self.assertIn('Cierres automáticos: 2', mensaje)
        # Los cierres confirmados se conservan, una sola vez.
        self.assertEqual(Medicion.objects.filter(indicador=kpi, cierre_automatico=True).count(), 2)
        self.assertFalse(Bitacora.objects.exists())

        # Una nueva ejecución no repite cierres ya confirmados.
        self.ejecutar('ejecutar_tareas_mediciones')
        self.assertEqual(Medicion.objects.filter(indicador=kpi, cierre_automatico=True).count(), 2)
        self.assertIn('Cierres automáticos: 0', self.registros_sistema().get().descripcion)
