"""Bloque 2 (correcciones Hernán): adapta el catálogo de roles a los 4
perfiles definitivos — Administrador del sistema, Administrador de
planificación, Ejecutor operativo, Usuario de consulta.

Decisiones tomadas con el cliente antes de ejecutar esta migración
(auditoría previa: 3 usuarios en el rol "Administrador" conflaba ambos
roles nuevos, por eso se repartieron explícitamente en vez de asumir):

- Rol "Administrador" (id conservado) se renombra a "Administrador del
  sistema". Los usuarios 'jose' y 'qa_kpi_debug' quedan ahí sin tocar su
  FK (jose es superusuario técnico de Django; qa_kpi_debug es la cuenta
  técnica de pruebas de este proyecto).
- Se crea el rol nuevo "Administrador de planificación" y se reasigna
  explícitamente a él únicamente el usuario 'jduarte'.
- Rol "Usuario operativo" (id conservado) se renombra a "Ejecutor
  operativo". No se toca la FK de ningún usuario (mvargas, mgonzalez
  siguen apuntando al mismo id).
- Rol "Usuario de consulta" no se renombra (coincide exactamente con el
  nombre definitivo). Sin usuarios asignados actualmente.
- Rol "Supervisor" (0 usuarios) se desactiva (estado=False) y se
  conserva como histórico, sin renombrar ni reutilizar.

No se elimina ningún Rol ni Usuario. No se modifica contraseñas, datos
personales ni historial. Reversible: el `reverse_code` deshace los
renombres y reactiva Supervisor, dejando sin embargo a 'jduarte' en el
nuevo rol de planificación si éste no se elimina (no se re-fusiona de
vuelta al id original para no arriesgar perder la distinción si ya se
creó más historial sobre esa asignación)."""

from django.db import migrations


NOMBRE_ADMIN_ANTERIOR = 'Administrador'
NOMBRE_ADMIN_SISTEMA = 'Administrador del sistema'
NOMBRE_ADMIN_PLANIFICACION = 'Administrador de planificación'
NOMBRE_OPERATIVO_ANTERIOR = 'Usuario operativo'
NOMBRE_EJECUTOR_OPERATIVO = 'Ejecutor operativo'
NOMBRE_SUPERVISOR = 'Supervisor'

USUARIOS_A_ADMIN_PLANIFICACION = ['jduarte']


def adaptar_roles(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Usuario = apps.get_model('usuarios', 'Usuario')

    rol_admin = Rol.objects.filter(nombre=NOMBRE_ADMIN_ANTERIOR).first()
    if rol_admin:
        rol_admin.nombre = NOMBRE_ADMIN_SISTEMA
        rol_admin.save(update_fields=['nombre'])

    rol_admin_planificacion, _ = Rol.objects.get_or_create(
        nombre=NOMBRE_ADMIN_PLANIFICACION,
        defaults={
            'descripcion': (
                'Gestiona planes estratégicos, planes anuales, objetivos, '
                'KPI y sus catálogos (áreas, frecuencias, estados de '
                'cumplimiento, rangos KPI) y revisa las alertas de '
                'cumplimiento.'
            ),
            'estado': True,
        },
    )

    Usuario.objects.filter(username__in=USUARIOS_A_ADMIN_PLANIFICACION).update(
        rol=rol_admin_planificacion
    )

    rol_operativo = Rol.objects.filter(nombre=NOMBRE_OPERATIVO_ANTERIOR).first()
    if rol_operativo:
        rol_operativo.nombre = NOMBRE_EJECUTOR_OPERATIVO
        rol_operativo.save(update_fields=['nombre'])

    Rol.objects.filter(nombre=NOMBRE_SUPERVISOR).update(estado=False)


def revertir_roles(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')

    rol_admin = Rol.objects.filter(nombre=NOMBRE_ADMIN_SISTEMA).first()
    if rol_admin:
        rol_admin.nombre = NOMBRE_ADMIN_ANTERIOR
        rol_admin.save(update_fields=['nombre'])

    rol_operativo = Rol.objects.filter(nombre=NOMBRE_EJECUTOR_OPERATIVO).first()
    if rol_operativo:
        rol_operativo.nombre = NOMBRE_OPERATIVO_ANTERIOR
        rol_operativo.save(update_fields=['nombre'])

    Rol.objects.filter(nombre=NOMBRE_SUPERVISOR).update(estado=True)

    # El rol "Administrador de planificación" y la reasignación de
    # jduarte se dejan como están: fusionarlos de vuelta a "Administrador"
    # automáticamente podría pisar una asignación de rol hecha después de
    # aplicar esta migración. Revertir eso, si hace falta, se hace a mano.


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_usuario_debe_cambiar_password_and_more'),
    ]

    operations = [
        migrations.RunPython(adaptar_roles, revertir_roles),
    ]
