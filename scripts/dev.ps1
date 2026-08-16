# Script de Desenvolvimento — RSAC V2
# Inicia backend Python + frontend Electron em paralelo

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RSAC V2 — Modo Desenvolvimento" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Iniciar Backend Python
Write-Host "[1/2] Iniciando Backend Python (FastAPI)..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "python" `
    -ArgumentList "run.py", "--port", "8000", "--reload", "--debug" `
    -WorkingDirectory "$PSScriptRoot\..\backend" `
    -PassThru -NoNewWindow

Write-Host "  Backend PID: $($backendJob.Id)" -ForegroundColor Green
Write-Host "  Backend URL: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  Swagger UI:  http://127.0.0.1:8000/api/docs" -ForegroundColor Green
Write-Host ""

# Aguardar backend ficar pronto
Write-Host "  Aguardando backend..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Iniciar Frontend Electron
Write-Host "[2/2] Iniciando Frontend Electron + React..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\..\frontend"
npm run dev

# Cleanup ao sair
Write-Host ""
Write-Host "Encerrando backend Python..." -ForegroundColor Yellow
Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
Write-Host "Finalizado." -ForegroundColor Green
