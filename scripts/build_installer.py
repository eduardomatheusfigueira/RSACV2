#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Build do Instalador Oficial Windows (.exe)
Compila o backend Python em binário autônomo e gera o instalador NSIS completo:
- RSAC V2-Setup-2.0.0.exe (ou RSAC-Setup.exe)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
BACKEND_DIR = ROOT_DIR / "backend"
DIST_DIR = ROOT_DIR / "dist_bin"
RELEASE_DIR = FRONTEND_DIR / "release"


def run_cmd(cmd, cwd=ROOT_DIR, desc=""):
    print(f"\n[*] {desc}...")
    proc = subprocess.run(cmd, cwd=str(cwd), shell=True)
    if proc.returncode != 0:
        print(f"[X] Falha na etapa: {desc}")
        sys.exit(1)


def main():
    print("═" * 65)
    print("       🚀 GERANDO INSTALADOR OFICIAL DO RSAC V2 (.EXE)")
    print("═" * 65)

    # 1. Compilar o backend em pacote autônomo
    backend_cmd = (
        f'"{sys.executable}" -m PyInstaller --noconfirm --onedir '
        f'--name rsac-backend '
        f'--distpath "{FRONTEND_DIR / "resources" / "backend"}" '
        f'--workpath "{ROOT_DIR / "build_temp" / "backend_build"}" '
        f'--hidden-import=uvicorn.logging '
        f'--hidden-import=uvicorn.loops '
        f'--hidden-import=uvicorn.loops.auto '
        f'--hidden-import=uvicorn.protocols '
        f'--hidden-import=uvicorn.protocols.http '
        f'--hidden-import=uvicorn.protocols.http.auto '
        f'--hidden-import=uvicorn.protocols.websockets '
        f'--hidden-import=uvicorn.protocols.websockets.auto '
        f'--hidden-import=uvicorn.lifespans '
        f'--hidden-import=uvicorn.lifespans.on '
        f'--hidden-import=sqlalchemy.dialects.sqlite '
        f'"{BACKEND_DIR / "run.py"}"'
    )
    run_cmd(backend_cmd, desc="Compilando backend Python em binário autônomo")

    # 2. Build do Electron Vite
    npm_bin = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    run_cmd(f'"{npm_bin}" run build', cwd=FRONTEND_DIR, desc="Compilando interface e processos Electron")

    # 3. Pacote do Instalador NSIS
    npx_bin = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
    run_cmd(f'"{npx_bin}" electron-builder --win', cwd=FRONTEND_DIR, desc="Gerando instalador executável (NSIS)")

    # 4. Copiar instalador para dist_bin
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    setup_file = RELEASE_DIR / "RSAC V2-Setup-2.0.0.exe"
    if setup_file.exists():
        dst = DIST_DIR / "RSAC-Setup.exe"
        shutil.copy2(setup_file, dst)
        print(f"\n[✓] Instalador copiado para: {dst}")

    print("\n" + "═" * 65)
    print("🎉 SUCESSO! O instalador autônomo está pronto para distribuição:")
    print(f"  📦 {setup_file}")
    print(f"  📦 {DIST_DIR / 'RSAC-Setup.exe'}")
    print("═" * 65 + "\n")


if __name__ == "__main__":
    main()
