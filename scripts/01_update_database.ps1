$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host " AI Career Agent - Database Update"
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = "C:\AI-Career-Agent"

if (!(Test-Path $ProjectRoot)) {
    Write-Host "Projeto não encontrado em $ProjectRoot" -ForegroundColor Red
    exit
}

Set-Location $ProjectRoot

if (!(Test-Path ".\app\database\sqlite_db.py")) {
    Write-Host "sqlite_db.py não encontrado." -ForegroundColor Red
    exit
}

if (!(Test-Path ".\backup")) {
    New-Item -ItemType Directory ".\backup" | Out-Null
}

$Date = Get-Date -Format "yyyyMMdd_HHmmss"

Copy-Item `
".\app\database\sqlite_db.py" `
".\backup\sqlite_db_$Date.py"

Write-Host ""
Write-Host "Backup criado." -ForegroundColor Green

Write-Host ""
Write-Host "======================================" -ForegroundColor Yellow
Write-Host "ATENÇÃO"
Write-Host "======================================"
Write-Host ""
Write-Host "Substitua agora:"
Write-Host ""
Write-Host "app\database\sqlite_db.py"
Write-Host ""
Write-Host "pela versão da Sprint 1.1."
Write-Host ""

Read-Host "Pressione ENTER quando terminar"

Write-Host ""
Write-Host "Executando testes..."
Write-Host ""

python run.py

if ($LASTEXITCODE -eq 0) {

    Write-Host ""
    Write-Host "Projeto iniciado com sucesso." -ForegroundColor Green

}
else {

    Write-Host ""
    Write-Host "Erro durante a execução." -ForegroundColor Red

}