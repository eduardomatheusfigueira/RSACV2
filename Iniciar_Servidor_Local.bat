@echo off
title Revsist — Servidor Local (Web)
echo ================================================================
echo   Iniciando Revsist — Servidor Local (Web)
echo ================================================================
echo   Backend API:   http://127.0.0.1:8000
echo   Frontend Web:  http://localhost:5173
echo ================================================================
echo.

start "Revsist — Backend API" cmd /k "cd /d ""%~dp0backend"" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 >nul

start "Revsist — Frontend Web" cmd /k "cd /d ""%~dp0frontend"" && npm run dev:web"

timeout /t 3 >nul

start http://localhost:5173
