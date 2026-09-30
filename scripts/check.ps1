param([switch]$Install)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    py -3.11 -m venv (Join-Path $projectRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Verificação falhou (código $LASTEXITCODE)." }
}

if ($Install) {
    & $python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Verificação falhou (código $LASTEXITCODE)." }
    & $python -m pip install -r (Join-Path $projectRoot "requirements-dev.txt")
    if ($LASTEXITCODE -ne 0) { throw "Verificação falhou (código $LASTEXITCODE)." }
}

$missing = & $python -c "import importlib.util; print(','.join(n for n in ('pytest','ruff','mypy') if importlib.util.find_spec(n) is None))"
if ($missing) {
    throw "Dependências de desenvolvimento ausentes: $missing. Execute .\scripts\check.ps1 -Install"
}

Push-Location $projectRoot
try {
    & $python -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Verificação falhou (código $LASTEXITCODE)." }
    & $python -m compileall -q app
    if ($LASTEXITCODE -ne 0) { throw "Verificação falhou (código $LASTEXITCODE)." }
    & $python -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "Verificação falhou (código $LASTEXITCODE)." }
    & $python -m mypy app
    if ($LASTEXITCODE -ne 0) { throw "Verificação falhou (código $LASTEXITCODE)." }
    & $python -m pytest --cov=app --cov-report=term --cov-fail-under=70
    if ($LASTEXITCODE -ne 0) { throw "Verificação falhou (código $LASTEXITCODE)." }
} finally {
    Pop-Location
}
