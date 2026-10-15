# run_etl_completo.ps1
# Orquestador del pipeline medallion: bronze -> silver -> normalizado -> gold
# Uso: .\run_etl_completo.ps1  (sin aplicar incremental)
#      .\run_etl_completo.ps1 -ApplyIncremental  (aplica incremental con --apply)

param(
  [switch]$ApplyIncremental
)

$ErrorActionPreference = "Stop"

$PY = ".\.venv\Scripts\python.exe"

function Write-Step {
  param([string]$Msg)
  Write-Host "`n========================================"
  Write-Host " $Msg"
  Write-Host "========================================`n"
}

try {
  Write-Step "FASE 0: INGESTA INCREMENTAL (bronze)"
  if ($ApplyIncremental) {
    Write-Host "Ejecutando: etl_incremental.py --apply"
    & $PY evidencia\etl_incremental.py --apply
  } else {
    Write-Host "Ejecutando: etl_incremental.py (solo lectura/checkpoint)"
    & $PY evidencia\etl_incremental.py
  }
  if ($LASTEXITCODE -ne 0) { throw "etl_incremental.py terminó con código $LASTEXITCODE" }

  Write-Step "FASE 1: LIMPIEZA (bronze -> silver)"
  Write-Host "Ejecutando: etl_silver.py"
  & $PY evidencia\etl_silver.py
  if ($LASTEXITCODE -ne 0) { throw "etl_silver.py terminó con código $LASTEXITCODE" }

  Write-Step "FASE 2: NORMALIZACION 3FN (silver -> normalizado)"
  Write-Host "Ejecutando: etl_normalizado.py"
  & $PY evidencia\etl_normalizado.py
  if ($LASTEXITCODE -ne 0) { throw "etl_normalizado.py terminó con código $LASTEXITCODE" }

  Write-Step "FASE 3: CAPA GOLD (normalizado/silver -> gold)"
  Write-Host "Ejecutando: etl_gold.py"
  & $PY evidencia\etl_gold.py
  if ($LASTEXITCODE -ne 0) { throw "etl_gold.py terminó con código $LASTEXITCODE" }

  Write-Step "ETL COMPLETO FINALIZADO CON EXITO"
  Write-Host "Evidencias esperadas: 01-09 (y 10-11 si se ejecutan por separado)."
  Write-Host "Validaciones gold: 08_reproduccion_gold.txt y 09_resultados_gold.txt deben mostrar 0 diferencias."
}
catch {
  Write-Error "ERROR EN ORQUESTACION: $_"
  exit 1
}
