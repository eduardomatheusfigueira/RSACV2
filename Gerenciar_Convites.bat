@echo off
title Revsist — Gerenciador de Convites
chcp 65001 >nul
cd /d "%~dp0"

echo ======================================================================
echo    REVSIST v2.0 — GERENCIADOR INTERATIVO DE CONVITES
echo ======================================================================
echo.

rem Verificar se existe o ambiente virtual do backend
if exist "%~dp0backend\.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0backend\.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_EXE=python"
    ) else (
        echo [ERRO] Python não foi encontrado no seu computador nem no backend\.venv.
        echo Por favor, instale o Python 3.11+ ou configure o ambiente virtual.
        echo.
        pause
        exit /b 1
    )
)

echo  Iniciando a máquina interativa de convites...
echo.

"%PY_EXE%" scripts\gerenciador_convites.py

if %errorlevel% neq 0 (
    echo.
    echo [AVISO] O gerenciador de convites foi encerrado com código %errorlevel%.
    pause
)
