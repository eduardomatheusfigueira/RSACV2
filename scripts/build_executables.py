#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Build Executável Desktop
Compila o executável unificado do aplicativo com PyInstaller:
- Revsist.exe (Aplicativo Desktop com Backend Integrado)
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
SCRIPTS_DIR = ROOT_DIR / "scripts"
DIST_DIR = ROOT_DIR / "dist_bin"
BUILD_DIR = ROOT_DIR / "build_temp"
# Único .ico do projeto, escrito por `brand/generate_brand_assets.py` a partir
# da geometria da marca. Este script mantinha o seu próprio, derivado de um PNG
# de 256 px e gravado em `brand/icon.ico` — uma segunda cópia, de pior origem,
# que ninguém regerava. Foi ela que ficou para trás quando o produto mudou de
# nome. Uma marca, um arquivo.
ICON_ICO = ROOT_DIR / "frontend" / "build" / "icon.ico"


def ensure_icon_ico():
    """Confere que o ícone da marca foi gerado; não o inventa."""
    if ICON_ICO.exists():
        return ICON_ICO
    print(f"[!] Ícone não encontrado em {ICON_ICO}.")
    print("    Rode: python brand/generate_brand_assets.py")
    return None


def create_batch_launcher():
    """Cria o arquivo Iniciar_Revsist.bat na raiz para conveniência."""
    launcher_bat = ROOT_DIR / "Iniciar_Revsist.bat"
    with open(launcher_bat, "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write("title Revsist — Aplicativo Desktop\n")
        f.write("if exist \"Revsist.exe\" (\n")
        f.write("    start \"\" \"Revsist.exe\"\n")
        f.write(") else (\n")
        f.write("    python scripts\\launcher.py\n")
        f.write(")\n")

    print("[✓] Arquivo Iniciar_Revsist.bat atualizado na raiz.")


def build_exe(script_path: Path, output_name: str, icon_path: Path | None):
    """Executa o PyInstaller para compilar o executável."""
    print(f"\n{'='*60}")
    print(f"[*] Compilando {output_name}.exe a partir de {script_path.name}...")
    print(f"{'='*60}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--console",
        "--name",
        output_name,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--hidden-import=colorama",
        # Parser de HTML dos coletores SciELO/BDTD: referenciado por string,
        # invisível à análise estática do PyInstaller (ver app/harvesters/html_parser.py).
        "--hidden-import=lxml",
        "--hidden-import=lxml.etree",
        "--hidden-import=lxml._elementpath",
        "--hidden-import=bs4",
    ]

    if icon_path and icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    cmd.append(str(script_path))

    proc = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if proc.returncode != 0:
        print(f"[X] Erro ao compilar {output_name}.exe")
        return False

    src_exe = DIST_DIR / f"{output_name}.exe"
    dst_exe = ROOT_DIR / f"{output_name}.exe"
    if src_exe.exists():
        try:
            shutil.copy2(src_exe, dst_exe)
            print(f"[✓] Executável criado e movido para: {dst_exe}")
        except PermissionError:
            print(f"[!] Aviso: Não foi possível sobrescrever {dst_exe} pois o processo está em execução.")
            print(f"[✓] Novo executável disponível em: {src_exe}")
        return True

    return False


def main():
    icon_path = ensure_icon_ico()

    # Compilar Revsist.exe único
    ok = build_exe(SCRIPTS_DIR / "launcher.py", "Revsist", icon_path)

    create_batch_launcher()

    # Limpeza de temporários
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)

    for spec in ROOT_DIR.glob("*.spec"):
        try:
            spec.unlink()
        except Exception:
            pass

    print("\n" + "═" * 60)
    if ok:
        print("🎉 SUCESSO! Executável oficial gerado na raiz:")
        print(f"  👉 {ROOT_DIR / 'Revsist.exe'}")
        print(f"  👉 {ROOT_DIR / 'Iniciar_Revsist.bat'}")
    else:
        print("⚠️ Houve falhas durante a compilação. Verifique os logs acima.")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()

