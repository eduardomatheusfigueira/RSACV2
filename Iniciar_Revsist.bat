@echo off
title Revsist — Aplicativo Desktop
if exist "Revsist.exe" (
    start "" "Revsist.exe"
) else (
    python scripts\launcher.py
)
