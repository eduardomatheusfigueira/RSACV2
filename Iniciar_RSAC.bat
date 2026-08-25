@echo off
title RSAC V2 — Aplicativo Local
if exist "RSAC.exe" (
    start "" "RSAC.exe"
) else if exist "RSAC_Local.exe" (
    start "" "RSAC_Local.exe"
) else (
    python scripts\local_launcher.py
)
