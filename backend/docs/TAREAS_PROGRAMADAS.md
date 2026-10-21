# Tarea diaria de mediciones (cierre automático y alertas)

> **Estado: preparada, NO activada.** No registres la tarea hasta resolver el
> hallazgo C2 (primer periodo de un KPI incorporado a mitad de año) de la
> auditoría del 20/10/2026. C3 ya está resuelto: las omisiones se guardan como
> "Sin registro" (sin resultado numérico), no como 0.00. Aun así, ejecutarla hoy
> crearía omisiones para periodos anteriores a la incorporación de los KPI, que
> no pueden borrarse desde la aplicación.

## Qué hace

`python manage.py ejecutar_tareas_mediciones` ejecuta, en este orden:

1. `cerrar_mediciones_vencidas`: por cada KPI autorizado cuyo Plan anual y Plan
   estratégico no estén Cerrados, cierra **en orden** todos los periodos cuyo
   plazo de registro (cierre del periodo + `ConfiguracionMediciones.dias_plazo_registro`)
   ya venció sin medición. Cada cierre queda como medición "Sin registro"
   (resultado vacío, no entra en el promedio) con su alerta "Periodo sin registro".

   Etapa 5 (días adicionales):
   - Antes de cerrar, las solicitudes de ampliación **pendientes** cuyo plazo
     máximo (límite ordinario + 10 días) ya pasó quedan **Vencidas**, y las de
     KPI anulados, de planes Cerrados o de periodos que ya tienen medición
     quedan **Sin efecto**. Cada cambio deja un registro del Sistema en la bitácora
     y un aviso al solicitante.
   - Con una ampliación **autorizada**, el plazo del periodo es la fecha
     extraordinaria.
   - Una solicitud **pendiente** detiene el cierre de ese periodo hasta su plazo
     máximo inclusive. La salida informa "KPI en espera por ampliación pendiente".
2. `generar_alertas_periodos_vencidos`: crea la alerta de periodo vencido del
   siguiente periodo pendiente de cada KPI, si todavía no existe.

El cierre va primero porque resuelve las alertas de los periodos que acaba de cubrir.

| Propiedad | Cómo se garantiza |
|---|---|
| Idempotencia | El siguiente periodo siempre se calcula desde la última medición guardada; la restricción única `(indicador, periodo)` impide duplicados aunque el proceso se repita. |
| Orden | Los periodos atrasados se procesan uno por uno, del más antiguo al más reciente. |
| Recuperación | Si la tarea no corrió durante días, una sola ejecución pone todo al día. |
| Ejecuciones simultáneas | En PostgreSQL, un *advisory lock* hace que una segunda ejecución termine sin hacer nada (código 1). Se libera solo si el proceso muere. |
| Errores | Un error en un KPI no detiene los demás; se informa en la salida y el comando termina con código 1. |
| Simulación | `--simular` hace todo el cálculo dentro de una transacción que siempre se revierte. |

## Horario

Una vez por día, **a las 00:15 hora de Guatemala** (`TIME_ZONE = America/Guatemala`;
el sistema usa `timezone.localdate()`). Un periodo cuyo plazo vence el día D se
cierra en la primera ejecución del día D+1, así que el registro manual siempre
está disponible durante todo el último día del plazo.

## Desarrollo (Windows, sin tarea programada)

```powershell
cd backend
venv\Scripts\python.exe manage.py ejecutar_tareas_mediciones --simular
```

Para revisar solo el cierre: `venv\Scripts\python.exe manage.py cerrar_mediciones_vencidas --simular`.

## Servidor Windows (Programador de tareas)

El script [`backend/scripts/tareas_mediciones.ps1`](../scripts/tareas_mediciones.ps1)
ejecuta el comando y agrega la salida a `backend/logs/tareas_mediciones_AAAA-MM.log`
(archivos excluidos de Git por `*.log`).

Registro de la tarea (ajustar la ruta y la cuenta de servicio):

```powershell
schtasks /Create /TN "SNIFF\Tareas de mediciones" /SC DAILY /ST 00:15 `
  /RU "<cuenta de servicio>" /RP `
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\ruta\SNIFF\backend\scripts\tareas_mediciones.ps1"
```

En la pestaña **Configuración** de la tarea:

- Marcar *Ejecutar la tarea lo antes posible si se omitió un inicio programado*.
- *Si la tarea ya se está ejecutando*: **No iniciar una nueva instancia**.
- Detener la tarea si se ejecuta durante más de 1 hora.

## Servidor Linux (cron)

```cron
15 0 * * * cd /ruta/SNIFF/backend && TZ=America/Guatemala venv/bin/python manage.py ejecutar_tareas_mediciones >> logs/tareas_mediciones_$(date +\%Y-\%m).log 2>&1
```

## Pasos para activarla (cuando se resuelvan C2 y C3)

1. Respaldo de PostgreSQL con `pg_dump` y de `backend/media/`.
2. `ejecutar_tareas_mediciones --simular` y revisión de cada cierre que se haría.
3. Confirmar con el responsable funcional los KPI afectados.
4. Registrar la tarea como se indica arriba.
5. Al día siguiente, revisar el log: código de salida 0 y cierres esperados.

## Monitoreo

- El historial del Programador de tareas muestra el código de salida de cada día.
- El log mensual contiene la fecha, cada cierre, cada alerta creada y el resumen.
- Pendiente (hallazgo M7): registrar cada ejecución también en la bitácora.
