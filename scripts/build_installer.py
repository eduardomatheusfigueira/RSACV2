#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Build do Instalador Oficial Windows (.exe)
Compila o backend Python em binário autônomo e gera o instalador Inno Setup (.exe):
- dist_bin/Revsist-Setup.exe
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    os.system("")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
BACKEND_DIR = ROOT_DIR / "backend"
DIST_DIR = ROOT_DIR / "dist_bin"
SCRIPTS_DIR = ROOT_DIR / "scripts"


def run_cmd(cmd, cwd=ROOT_DIR, desc=""):
    print(f"\n[*] {desc}...")
    proc = subprocess.run(cmd, cwd=str(cwd), shell=True)
    if proc.returncode != 0:
        print(f"[X] Falha na etapa: {desc}")
        sys.exit(1)


def find_iscc() -> str:
    """Localiza o compilador Inno Setup no sistema."""
    candidates = [
        shutil.which("iscc"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return "iscc"


def main():
    print("═" * 65)
    print("       🚀 GERANDO INSTALADOR OFICIAL DO REVSIST (.EXE)")
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
        # O parser de HTML dos coletores SciELO/BDTD é escolhido por string
        # ("lxml"), então a análise estática do PyInstaller não o enxerga.
        # Sem estas linhas o executável sobe sem lxml e a raspagem zera.
        f'--hidden-import=lxml '
        f'--hidden-import=lxml.etree '
        f'--hidden-import=lxml._elementpath '
        f'--hidden-import=bs4 '
        f'"{BACKEND_DIR / "run.py"}"'
    )
    run_cmd(backend_cmd, desc="Compilando backend Python em binário autônomo")

    # 2. Build do Electron Vite
    npm_bin = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    run_cmd(f'"{npm_bin}" run build', cwd=FRONTEND_DIR, desc="Compilando interface e processos Electron")

    # 3. Gerar arquivos desembalados do Electron
    npx_bin = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
    run_cmd(f'"{npx_bin}" electron-builder --dir', cwd=FRONTEND_DIR, desc="Preparando pacote da aplicação")

    # 4. Compilar instalador oficial com Inno Setup
    iscc_path = find_iscc()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    iss_file = SCRIPTS_DIR / "installer.iss"
    run_cmd(f'"{iscc_path}" /Qp "{iss_file}"', desc="Compilando instalador executável (Inno Setup)")

    setup_file = DIST_DIR / "Revsist-Setup.exe"
    print("\n" + "═" * 65)
    print("🎉 SUCESSO! O instalador autônomo está pronto para distribuição:")
    print(f"  📦 {setup_file}")
    print("═" * 65 + "\n")


if __name__ == "__main__":
    main()
