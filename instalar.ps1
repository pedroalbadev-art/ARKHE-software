# instalar.ps1
# ----------------------------------------------------------------------
# Instalacion del sistema en Windows. Ejecutar en PowerShell, dentro de
# la carpeta del proyecto:
#
#     .\instalar.ps1
#
# SI WINDOWS BLOQUEA EL SCRIPT ("la ejecucion de scripts esta
# deshabilitada en este sistema"), use UNA de estas dos opciones. Ninguna
# cambia la configuracion permanente del equipo:
#
#   a) Ejecutarlo permitiendo solo esta vez:
#        powershell -ExecutionPolicy Bypass -File .\instalar.ps1
#
#   b) Permitir scripts solo en esta ventana de PowerShell y luego correrlo:
#        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#        .\instalar.ps1
#
# Si descargo el proyecto como ZIP y Windows lo marca como "de internet":
#        Unblock-File .\instalar.ps1
#
# QUE HACE:
#   1. Comprueba que Python 3.10 o superior este instalado.
#   2. Crea el entorno virtual venv\ (si no existe).
#   3. Instala las dependencias (requirements-dev.txt, que incluye las de
#      requirements.txt y pytest).
#   4. Ejecuta scripts\preparar_base.py, que pregunta los datos de MySQL,
#      crea el .env, la base de datos, las tablas y los datos de ejemplo.
#
# QUE NO HACE: no modifica ni borra una base de datos que ya exista y no
# sobrescribe un archivo .env existente. En ambos casos se detiene o lo
# respeta (ver scripts\preparar_base.py).
#
# Nota: este archivo no lleva tildes a proposito. Windows PowerShell 5.1
# lee los .ps1 sin marca de codificacion como ANSI y las mostraria mal.
# ----------------------------------------------------------------------

$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot

function Paso($texto) {
    Write-Host ""
    Write-Host "== $texto" -ForegroundColor Cyan
}

function Detener($texto) {
    Write-Host ""
    Write-Host $texto -ForegroundColor Red
    exit 1
}

# ---- 1. Python -------------------------------------------------------
Paso "1/4  Comprobando Python"
$python = $null
foreach ($candidato in @("python", "py")) {
    if (Get-Command $candidato -ErrorAction SilentlyContinue) {
        & $candidato -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $python = $candidato
            break
        }
    }
}
if (-not $python) {
    Detener "No se encontro Python 3.10 o superior. Instalelo desde https://www.python.org/downloads/ (marque 'Add python.exe to PATH') y vuelva a ejecutar este script."
}
& $python --version

# ---- 2. Entorno virtual ----------------------------------------------
Paso "2/4  Entorno virtual (venv)"
$pythonVenv = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (Test-Path $pythonVenv) {
    Write-Host "Ya existe: se reutiliza."
} else {
    & $python -m venv venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $pythonVenv)) {
        Detener "No se pudo crear el entorno virtual."
    }
    Write-Host "Creado en venv\"
}

# ---- 3. Dependencias -------------------------------------------------
Paso "3/4  Instalando dependencias (puede tardar un minuto)"
& $pythonVenv -m pip install --disable-pip-version-check -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) {
    Detener "No se pudieron instalar las dependencias. Revise su conexion a internet y vuelva a intentarlo."
}

# ---- 4. Base de datos y .env -----------------------------------------
Paso "4/4  Base de datos"
& $pythonVenv scripts\preparar_base.py
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "La instalacion NO termino (ver el mensaje de arriba). Puede corregir y volver a ejecutar .\instalar.ps1" -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Instalacion terminada." -ForegroundColor Green
Write-Host "Para iniciar el sistema:"
Write-Host "    venv\Scripts\activate"
Write-Host "    python app.py"
Write-Host "y abra http://localhost:5000 en el navegador."
Write-Host "Para ejecutar las pruebas:  pytest"
