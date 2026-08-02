$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Crie o ambiente .venv e instale requirements-dev.txt antes de empacotar."
}

Push-Location $projectRoot
try {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Os testes falharam." }
    & $python -m PyInstaller --noconfirm --clean "AI-Career-Agent.spec"
    if ($LASTEXITCODE -ne 0) { throw "O empacotamento falhou." }
    Write-Host "Executável criado em dist\AI-Career-Agent.exe"
}
finally {
    Pop-Location
}
