# Etapa 3 (auditoría C1): ejecuta la tarea diaria de mediciones de SNIFF y
# deja el resultado en backend\logs\tareas_mediciones_AAAA-MM.log.
#
# NO registra ninguna tarea programada: solo es el script que la tarea
# llamará. Ver backend\docs\TAREAS_PROGRAMADAS.md.
#
# Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tareas_mediciones.ps1 -Simular
#   powershell -NoProfile -ExecutionPolicy Bypass -File tareas_mediciones.ps1

param(
    [switch]$Simular
)

$ErrorActionPreference = 'Stop'

$backend = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backend 'venv\Scripts\python.exe'
$manage = Join-Path $backend 'manage.py'
$carpetaLogs = Join-Path $backend 'logs'
$archivoLog = Join-Path $carpetaLogs ("tareas_mediciones_{0}.log" -f (Get-Date -Format 'yyyy-MM'))

if (-not (Test-Path $carpetaLogs)) {
    New-Item -ItemType Directory -Path $carpetaLogs | Out-Null
}

$argumentos = @($manage, 'ejecutar_tareas_mediciones')
if ($Simular) {
    $argumentos += '--simular'
}

Set-Location $backend

# Salida y errores van al mismo archivo (se agregan, nunca se sobrescriben).
& $python @argumentos *>> $archivoLog
$codigo = $LASTEXITCODE

Add-Content -Path $archivoLog -Value ("[{0}] Código de salida: {1}`r`n" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $codigo)

# El programador de tareas registra como fallo cualquier código distinto de 0.
exit $codigo
