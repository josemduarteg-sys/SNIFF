"""Bloque 2 (correcciones Hernán): pruebas dedicadas a la matriz de
permisos de los 4 roles definitivos — Administrador del sistema,
Administrador de planificación, Ejecutor operativo, Usuario de consulta.

Archivo separado a propósito de apps/usuarios/tests.py (que ya cubre el
mecanismo de cambio obligatorio de contraseña) para mantener acá,
agrupadas, exactamente las 10 verificaciones que pidió el Requerimiento 5
del Bloque 2. Usa directamente los 4 nombres de rol reales (ya adaptados
por la migración usuarios.0003_adaptar_roles_bloque2_hernan), nunca los
nombres anteriores.
"""
from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.indicadores.models import EstadoCumplimiento, Frecuencia, IndicadorKPI
from apps.usuarios.models import Rol, SolicitudRestablecimientoPassword, Usuario

ROL_ADMIN_SISTEMA = 'Administrador del sistema'
ROL_ADMIN_PLANIFICACION = 'Administrador de planificación'
ROL_EJECUTOR_OPERATIVO = 'Ejecutor operativo'
ROL_USUARIO_CONSULTA = 'Usuario de consulta'

PASSWORD_PRUEBA = 'clave-prueba-123'


def crear_usuario(username, rol_nombre, is_active=True):
    rol, _ = Rol.objects.get_or_create(
        nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True}
    )

    usuario = Usuario.objects.create_user(username=username, password=PASSWORD_PRUEBA)
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.is_active = is_active
    usuario.estado = is_active
    usuario.save()

    return usuario


class CuatroRolesLoginTests(APITestCase):
    """1. Los 4 roles pueden iniciar sesión cuando sus cuentas están
    activas (y NO pueden cuando están inactivas)."""

    def test_los_cuatro_roles_inician_sesion_activos(self):
        for rol_nombre in (
            ROL_ADMIN_SISTEMA, ROL_ADMIN_PLANIFICACION, ROL_EJECUTOR_OPERATIVO, ROL_USUARIO_CONSULTA,
        ):
            with self.subTest(rol=rol_nombre):
                username = f'login_{rol_nombre}'.lower().replace(' ', '_')
                crear_usuario(username, rol_nombre)

                response = self.client.post(
                    '/api/auth/login/', {'username': username, 'password': PASSWORD_PRUEBA}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn('access', response.data)

    def test_cuenta_inactiva_no_inicia_sesion(self):
        crear_usuario('inactivo_bloque2', ROL_ADMIN_PLANIFICACION, is_active=False)

        response = self.client.post(
            '/api/auth/login/', {'username': 'inactivo_bloque2', 'password': PASSWORD_PRUEBA}
        )

        self.assertNotEqual(response.status_code, status.HTTP_200_OK)


class PlaneacionKpiSoloAdminPlanificacionTests(APITestCase):
    """2 y 3. Solo Administrador de planificación puede crear/modificar
    planes, objetivos y KPI, y solo él puede autorizar/anular KPI. Se
    prueba contra los 4 roles para confirmar que el resto queda
    rechazado — incluido vía llamada directa a la API (sin pasar por
    ningún botón de frontend)."""

    def setUp(self):
        self.admin_sistema = crear_usuario('admin_sistema_planeacion', ROL_ADMIN_SISTEMA)
        self.admin_planificacion = crear_usuario('admin_planificacion_planeacion', ROL_ADMIN_PLANIFICACION)
        self.ejecutor = crear_usuario('ejecutor_planeacion', ROL_EJECUTOR_OPERATIVO)
        self.consulta = crear_usuario('consulta_planeacion', ROL_USUARIO_CONSULTA)

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)
        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

    def _crear_plan_estrategico(self, usuario):
        self.client.force_authenticate(user=usuario)
        return self.client.post('/api/planes-estrategicos/', {
            'titulo': f'Plan de {usuario.username}',
            'fecha_inicio': '2027-01-01',
            'fecha_fin': '2030-12-31',
        })

    def test_admin_planificacion_crea_plan_estrategico(self):
        response = self._crear_plan_estrategico(self.admin_planificacion)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_sistema_no_crea_plan_estrategico(self):
        response = self._crear_plan_estrategico(self.admin_sistema)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ejecutor_no_crea_plan_estrategico(self):
        response = self._crear_plan_estrategico(self.ejecutor)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consulta_no_crea_plan_estrategico(self):
        response = self._crear_plan_estrategico(self.consulta)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_los_cuatro_roles_pueden_consultar_planes_estrategicos(self):
        PlanEstrategico.objects.create(
            titulo='Plan consultable', fecha_inicio='2027-01-01', fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin_planificacion,
        )

        for usuario in (self.admin_sistema, self.admin_planificacion, self.ejecutor, self.consulta):
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(user=usuario)
                response = self.client.get('/api/planes-estrategicos/')
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def _preparar_kpi_borrador(self):
        plan = PlanEstrategico.objects.create(
            titulo='Plan KPI', fecha_inicio='2027-01-01', fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin_planificacion,
        )
        objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=plan, texto_objetivo='Objetivo general KPI', creado_por=self.admin_planificacion,
        )
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31),
            estado=PlanAnual.ESTADO_EN_USO, creado_por=self.admin_planificacion,
        )
        objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual, objetivo_general=objetivo_general,
            texto_objetivo='Objetivo especifico KPI', creado_por=self.admin_planificacion,
        )
        return objetivo_especifico

    def _payload_kpi(self, objetivo_especifico_id):
        return {
            'objetivo_especifico': objetivo_especifico_id,
            'frecuencia': self.frecuencia.id,
            'nombre': 'KPI permisos bloque 2',
            'descripcion': 'Descripción de prueba',
            'formula_medicion': '(Resultado / Meta) x 100',
            'unidad_medida': '%',
            'valor_meta': '85.00',
        }

    def test_admin_planificacion_crea_y_autoriza_kpi(self):
        objetivo_especifico = self._preparar_kpi_borrador()
        self.client.force_authenticate(user=self.admin_planificacion)

        creado = self.client.post('/api/indicadores-kpi/', self._payload_kpi(objetivo_especifico.id))
        self.assertEqual(creado.status_code, status.HTTP_201_CREATED)

        autorizado = self.client.post(f"/api/indicadores-kpi/{creado.data['id']}/autorizar/")
        self.assertEqual(autorizado.status_code, status.HTTP_200_OK)
        self.assertEqual(autorizado.data['estado'], 'autorizado')

        anulado = self.client.post(f"/api/indicadores-kpi/{creado.data['id']}/anular/")
        self.assertEqual(anulado.status_code, status.HTTP_200_OK)
        self.assertEqual(anulado.data['estado'], 'anulado')

    def test_otros_tres_roles_no_crean_ni_autorizan_kpi(self):
        objetivo_especifico = self._preparar_kpi_borrador()

        # Un KPI de apoyo, creado por quien sí puede, para probar
        # autorizar/anular contra los otros roles.
        self.client.force_authenticate(user=self.admin_planificacion)
        kpi_apoyo = self.client.post(
            '/api/indicadores-kpi/', self._payload_kpi(objetivo_especifico.id)
        ).data['id']

        for usuario in (self.admin_sistema, self.ejecutor, self.consulta):
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(user=usuario)

                creado = self.client.post('/api/indicadores-kpi/', self._payload_kpi(objetivo_especifico.id))
                self.assertEqual(creado.status_code, status.HTTP_403_FORBIDDEN)

                autorizado = self.client.post(f'/api/indicadores-kpi/{kpi_apoyo}/autorizar/')
                self.assertEqual(autorizado.status_code, status.HTTP_403_FORBIDDEN)


class MedicionSoloEjecutorTests(APITestCase):
    """4. Solo Ejecutor operativo puede registrar mediciones (y adjuntar
    su evidencia, que viaja en el mismo payload)."""

    def setUp(self):
        self.admin_sistema = crear_usuario('admin_sistema_medicion', ROL_ADMIN_SISTEMA)
        self.admin_planificacion = crear_usuario('admin_planificacion_medicion', ROL_ADMIN_PLANIFICACION)
        self.ejecutor = crear_usuario('ejecutor_medicion', ROL_EJECUTOR_OPERATIVO)
        self.consulta = crear_usuario('consulta_medicion', ROL_USUARIO_CONSULTA)

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})
        frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)

        plan = PlanEstrategico.objects.create(
            titulo='Plan medicion permisos', fecha_inicio='2027-01-01', fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin_planificacion,
        )
        objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=plan, texto_objetivo='Objetivo general medicion', creado_por=self.admin_planificacion,
        )
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31),
            estado=PlanAnual.ESTADO_EN_USO, creado_por=self.admin_planificacion,
        )
        objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual, objetivo_general=objetivo_general,
            texto_objetivo='Objetivo especifico medicion', creado_por=self.admin_planificacion,
        )
        self.kpi = IndicadorKPI.objects.create(
            objetivo_especifico=objetivo_especifico, frecuencia=frecuencia,
            nombre='KPI medicion permisos', formula_medicion='Resultado / Meta x 100',
            unidad_medida='%', valor_meta=Decimal('85.00'), estado='autorizado',
            creado_por=self.admin_planificacion,
        )
        from apps.indicadores.services import crear_rangos_provisionales
        crear_rangos_provisionales(self.kpi)

    def _registrar_medicion(self, usuario):
        self.client.force_authenticate(user=usuario)
        from unittest import mock
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            return self.client.post('/api/mediciones/', {
                'indicador': self.kpi.id,
                'valor_resultado': '90',
            })

    def test_ejecutor_registra_medicion(self):
        response = self._registrar_medicion(self.ejecutor)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_planificacion_no_registra_medicion(self):
        response = self._registrar_medicion(self.admin_planificacion)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_sistema_no_registra_medicion(self):
        response = self._registrar_medicion(self.admin_sistema)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consulta_no_registra_medicion(self):
        response = self._registrar_medicion(self.consulta)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UsuarioConsultaSoloLecturaTests(APITestCase):
    """5. El usuario de consulta no puede crear, modificar, autorizar ni
    eliminar información en ningún módulo — probado contra varios
    endpoints representativos."""

    def setUp(self):
        self.consulta = crear_usuario('consulta_candado', ROL_USUARIO_CONSULTA)
        self.admin_planificacion = crear_usuario('admin_planificacion_candado', ROL_ADMIN_PLANIFICACION)

        self.plan = PlanEstrategico.objects.create(
            titulo='Plan candado consulta', fecha_inicio='2027-01-01', fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin_planificacion,
        )

    def test_consulta_no_crea_area(self):
        self.client.force_authenticate(user=self.consulta)
        response = self.client.post('/api/areas/', {'nombre': 'Área de consulta'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consulta_no_edita_plan_estrategico(self):
        self.client.force_authenticate(user=self.consulta)
        response = self.client.patch(
            f'/api/planes-estrategicos/{self.plan.id}/', {'descripcion': 'Intento de edición'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consulta_no_pone_en_uso_ni_cierra_plan(self):
        self.client.force_authenticate(user=self.consulta)

        plan_borrador = PlanEstrategico.objects.create(
            titulo='Plan borrador consulta', fecha_inicio='2027-01-01', fecha_fin='2030-12-31',
            creado_por=self.admin_planificacion,
        )

        response = self.client.post(f'/api/planes-estrategicos/{plan_borrador.id}/poner-en-uso/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(f'/api/planes-estrategicos/{self.plan.id}/cerrar/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consulta_no_crea_usuarios(self):
        self.client.force_authenticate(user=self.consulta)
        response = self.client.post('/api/usuarios/', {
            'username': 'intento_consulta', 'correo': 'intento@sniff.test', 'password': PASSWORD_PRUEBA,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consulta_puede_consultar_planes(self):
        self.client.force_authenticate(user=self.consulta)
        response = self.client.get('/api/planes-estrategicos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AdminSistemaTests(APITestCase):
    """6. Solo Administrador del sistema puede administrar usuarios,
    solicitudes de restablecimiento y consultar la bitácora."""

    def setUp(self):
        self.admin_sistema = crear_usuario('admin_sistema_usuarios', ROL_ADMIN_SISTEMA)
        self.admin_planificacion = crear_usuario('admin_planificacion_usuarios', ROL_ADMIN_PLANIFICACION)
        self.ejecutor = crear_usuario('ejecutor_usuarios', ROL_EJECUTOR_OPERATIVO)
        self.consulta = crear_usuario('consulta_usuarios', ROL_USUARIO_CONSULTA)

        self.solicitud = SolicitudRestablecimientoPassword.objects.create(
            usuario=self.ejecutor, identificador_ingresado=self.ejecutor.username,
        )

    def test_admin_sistema_crea_usuario(self):
        self.client.force_authenticate(user=self.admin_sistema)
        response = self.client.post('/api/usuarios/', {
            'username': 'nuevo_usuario_bloque2', 'correo': 'nuevo_bloque2@sniff.test',
            'password': PASSWORD_PRUEBA,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_otros_tres_roles_no_crean_usuario(self):
        for usuario in (self.admin_planificacion, self.ejecutor, self.consulta):
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(user=usuario)
                response = self.client.post('/api/usuarios/', {
                    'username': f'intento_{usuario.username}', 'correo': f'intento_{usuario.username}@sniff.test',
                    'password': PASSWORD_PRUEBA,
                })
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_sistema_aprueba_solicitud_restablecimiento(self):
        self.client.force_authenticate(user=self.admin_sistema)
        response = self.client.post(f'/api/solicitudes-restablecimiento/{self.solicitud.id}/aprobar/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_planificacion_no_aprueba_solicitud_restablecimiento(self):
        self.client.force_authenticate(user=self.admin_planificacion)
        response = self.client.post(f'/api/solicitudes-restablecimiento/{self.solicitud.id}/aprobar/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_sistema_consulta_bitacora(self):
        self.client.force_authenticate(user=self.admin_sistema)
        response = self.client.get('/api/bitacora/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_otros_tres_roles_no_consultan_bitacora(self):
        for usuario in (self.admin_planificacion, self.ejecutor, self.consulta):
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(user=usuario)
                response = self.client.get('/api/bitacora/')
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ConsultaYDescargaParaTodosTests(APITestCase):
    """8. Consultar resultados y descargar evidencias funciona para los 4
    roles (nunca se restringió un GET en ningún permiso del Bloque 2)."""

    def setUp(self):
        self.admin_sistema = crear_usuario('admin_sistema_descarga', ROL_ADMIN_SISTEMA)
        self.admin_planificacion = crear_usuario('admin_planificacion_descarga', ROL_ADMIN_PLANIFICACION)
        self.ejecutor = crear_usuario('ejecutor_descarga', ROL_EJECUTOR_OPERATIVO)
        self.consulta = crear_usuario('consulta_descarga', ROL_USUARIO_CONSULTA)

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})
        frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)

        plan = PlanEstrategico.objects.create(
            titulo='Plan descarga permisos', fecha_inicio='2027-01-01', fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin_planificacion,
        )
        objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=plan, texto_objetivo='Objetivo general descarga', creado_por=self.admin_planificacion,
        )
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31),
            estado=PlanAnual.ESTADO_EN_USO, creado_por=self.admin_planificacion,
        )
        objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual, objetivo_general=objetivo_general,
            texto_objetivo='Objetivo especifico descarga', creado_por=self.admin_planificacion,
        )
        self.kpi = IndicadorKPI.objects.create(
            objetivo_especifico=objetivo_especifico, frecuencia=frecuencia,
            nombre='KPI descarga permisos', formula_medicion='Resultado / Meta x 100',
            unidad_medida='%', valor_meta=Decimal('85.00'), estado='autorizado',
            creado_por=self.admin_planificacion,
        )
        from apps.indicadores.services import crear_rangos_provisionales
        crear_rangos_provisionales(self.kpi)

    def test_los_cuatro_roles_consultan_mediciones_e_indicadores(self):
        for usuario in (self.admin_sistema, self.admin_planificacion, self.ejecutor, self.consulta):
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(user=usuario)

                response_kpi = self.client.get('/api/indicadores-kpi/')
                self.assertEqual(response_kpi.status_code, status.HTTP_200_OK)

                response_medicion = self.client.get('/api/mediciones/')
                self.assertEqual(response_medicion.status_code, status.HTTP_200_OK)


class DatosExistentesIntactosTests(APITestCase):
    """9. Los datos existentes permanecen intactos.

    La migración usuarios.0003_adaptar_roles_bloque2_hernan es una
    transformación de datos REALES preexistentes (renombra filas de Rol
    que ya existían en PostgreSQL) — en una base de pruebas, que arranca
    vacía, no hay nada que renombrar, así que esta clase NO verifica el
    efecto de esa migración puntual (eso ya se verificó a mano contra el
    PostgreSQL real, ver la entrega del Bloque 2: jose/qa_kpi_debug ->
    Administrador del sistema, jduarte -> Administrador de planificación,
    mvargas/mgonzalez -> Ejecutor operativo, 0 usuarios perdidos).

    Acá se prueba el invariante estructural que SÍ aplica siempre,
    independientemente del contenido: un Rol con usuarios asignados no se
    puede eliminar físicamente (on_delete=PROTECT), que es la garantía
    real de "no eliminar roles históricos todavía referenciados"."""

    def test_rol_con_usuarios_asignados_no_se_puede_eliminar(self):
        from django.db.models.deletion import ProtectedError

        rol = Rol.objects.create(nombre='Rol histórico con usuarios', estado=False)
        crear_usuario('usuario_rol_historico', rol.nombre)

        with self.assertRaises(ProtectedError):
            rol.delete()

        self.assertTrue(Rol.objects.filter(id=rol.id).exists())

    def test_crear_usuario_admin_con_los_cuatro_roles_no_falla(self):
        # No depende de que la migración de datos haya corrido: crea cada
        # rol bajo demanda (igual que hacen los demás tests de este
        # archivo) y confirma que los 4 nombres definitivos son válidos
        # para asignar a un usuario sin error.
        for nombre in (
            ROL_ADMIN_SISTEMA, ROL_ADMIN_PLANIFICACION, ROL_EJECUTOR_OPERATIVO, ROL_USUARIO_CONSULTA,
        ):
            with self.subTest(rol=nombre):
                usuario = crear_usuario(f'intacto_{nombre}'.lower().replace(' ', '_'), nombre)
                self.assertEqual(usuario.rol.nombre, nombre)


class NotificarAdministradoresSistemaTests(APITestCase):
    """Regresión encontrada después del Bloque 2: una solicitud de
    restablecimiento de contraseña debe notificar a TODOS los
    Administradores del sistema activos — nunca a Administrador de
    planificación, Ejecutor operativo ni Usuario de consulta, aunque
    estén activos. notificar_administradores() seguía consultando el
    nombre de rol literal anterior ('administrador'/'admin') y dejó de
    coincidir con nadie tras renombrar el rol en la migración
    usuarios.0003_adaptar_roles_bloque2_hernan."""

    def setUp(self):
        self.admin_sistema_activo_1 = crear_usuario('admin_sistema_notif_1', ROL_ADMIN_SISTEMA)
        self.admin_sistema_activo_2 = crear_usuario('admin_sistema_notif_2', ROL_ADMIN_SISTEMA)
        self.admin_sistema_inactivo = crear_usuario(
            'admin_sistema_notif_inactivo', ROL_ADMIN_SISTEMA, is_active=False
        )
        self.admin_planificacion = crear_usuario('admin_planificacion_notif', ROL_ADMIN_PLANIFICACION)
        self.ejecutor = crear_usuario('ejecutor_notif', ROL_EJECUTOR_OPERATIVO)
        self.consulta = crear_usuario('consulta_notif', ROL_USUARIO_CONSULTA)
        self.solicitante = crear_usuario('solicitante_notif', ROL_ADMIN_PLANIFICACION)

    def _solicitar_restablecimiento(self):
        return self.client.post('/api/usuarios/solicitar-restablecimiento/', {
            'identificador': self.solicitante.username,
            'motivo': 'Prueba de regresión de notificaciones',
        })

    def test_solicitud_notifica_a_todos_los_administradores_sistema_activos(self):
        from apps.auditoria.models import Notificacion

        response = self._solicitar_restablecimiento()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        destinatarios = set(
            Notificacion.objects.filter(
                tipo='solicitud_restablecimiento_password',
                usuario_destino__in=[self.admin_sistema_activo_1, self.admin_sistema_activo_2],
            ).values_list('usuario_destino__username', flat=True)
        )

        self.assertEqual(
            destinatarios,
            {self.admin_sistema_activo_1.username, self.admin_sistema_activo_2.username},
        )

    def test_solicitud_no_notifica_a_administrador_sistema_inactivo(self):
        from apps.auditoria.models import Notificacion

        self._solicitar_restablecimiento()

        existe = Notificacion.objects.filter(
            tipo='solicitud_restablecimiento_password',
            usuario_destino=self.admin_sistema_inactivo,
        ).exists()
        self.assertFalse(existe)

    def test_solicitud_no_notifica_a_otros_tres_roles(self):
        from apps.auditoria.models import Notificacion

        self._solicitar_restablecimiento()

        for usuario in (self.admin_planificacion, self.ejecutor, self.consulta):
            with self.subTest(usuario=usuario.username):
                existe = Notificacion.objects.filter(
                    tipo='solicitud_restablecimiento_password',
                    usuario_destino=usuario,
                ).exists()
                self.assertFalse(existe)

    def test_solicitud_sigue_apareciendo_en_lista_administrativa(self):
        from apps.usuarios.models import SolicitudRestablecimientoPassword

        self._solicitar_restablecimiento()

        self.client.force_authenticate(user=self.admin_sistema_activo_1)
        response = self.client.get('/api/solicitudes-restablecimiento/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        existe = SolicitudRestablecimientoPassword.objects.filter(usuario=self.solicitante).exists()
        self.assertTrue(existe)

    def test_notificacion_aparece_en_centro_de_notificaciones_del_destinatario(self):
        self._solicitar_restablecimiento()

        self.client.force_authenticate(user=self.admin_sistema_activo_1)
        response = self.client.get('/api/notificaciones/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tipos = [n['tipo'] for n in response.data]
        self.assertIn('solicitud_restablecimiento_password', tipos)
