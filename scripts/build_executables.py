#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Build Executável Desktop
Compila o executável unificado do aplicativo com PyInstaller:
- Revsist.exe (Aplicativo Desktop com Backend Integrado)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image

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
ICON_PNG = ROOT_DIR / "frontend" / "resources" / "icon-256.png"
ICON_ICO = ROOT_DIR / "brand" / "icon.ico"


def ensure_icon_ico():
    """Gera o arquivo .ico a partir do PNG se não existir."""
    if not ICON_ICO.exists() and ICON_PNG.exists():
        print("[*] Convertendo ícone da marca para .ico...")
        ICON_ICO.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(ICON_PNG)
        img.save(
            ICON_ICO,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        print(f"[✓] Ícone gerado em: {ICON_ICO}")
    return ICON_ICO if ICON_ICO.exists() else None


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

