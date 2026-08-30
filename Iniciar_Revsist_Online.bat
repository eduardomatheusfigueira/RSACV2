@echo off
title Revsist — Servidor Online (revsist.com)
echo ================================================================
echo   Iniciando Revsist — Servidor Online (revsist.com)
echo ================================================================
echo   Backend API:   http://127.0.0.1:8000
echo   Frontend Web:  http://127.0.0.1:8000
echo   Dominio Web:   https://revsist.com
echo ================================================================
echo.

start "Revsist — Backend & Frontend" cmd /k "cd /d ""%~dp0backend"" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 >nul

start https://revsist.com
