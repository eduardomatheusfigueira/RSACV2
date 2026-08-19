@echo off
title RSAC V2 - Interface Local
if exist "RSAC_Local.exe" (
    start "" "RSAC_Local.exe"
) else (
    python scripts\local_launcher.py
)
