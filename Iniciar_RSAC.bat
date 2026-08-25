@echo off
title RSAC V2 — Aplicativo Desktop
if exist "RSAC.exe" (
    start "" "RSAC.exe"
) else (
    python scripts\launcher.py
)
