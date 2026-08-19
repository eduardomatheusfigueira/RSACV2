@echo off
title RSAC V2 - Servidor Remoto & Cloudflare
if exist "RSAC_Server.exe" (
    start "" "RSAC_Server.exe"
) else (
    python scripts\server_launcher.py
)
