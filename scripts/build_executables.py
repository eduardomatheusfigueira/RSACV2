#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Build Executables
Compila os 2 executáveis do projeto com PyInstaller:
1. RSAC_Server.exe  (Servidor Backend + Cloudflare Tunnel + Web Remoto)
2. RSAC_Local.exe   (Interface Local Desktop)
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


def create_batch_launchers():
    """Cria arquivos .bat rápidos na raiz para conveniência adicional."""
    server_bat = ROOT_DIR / "Iniciar_Servidor.bat"
    local_bat = ROOT_DIR / "Iniciar_Interface_Local.bat"

    with open(server_bat, "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write("title RSAC V2 - Servidor Remoto & Cloudflare\n")
        f.write("if exist \"RSAC_Server.exe\" (\n")
        f.write("    start \"\" \"RSAC_Server.exe\"\n")
        f.write(") else (\n")
        f.write("    python scripts\\server_launcher.py\n")
        f.write(")\n")

    with open(local_bat, "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write("title RSAC V2 - Interface Local\n")
        f.write("if exist \"RSAC_Local.exe\" (\n")
        f.write("    start \"\" \"RSAC_Local.exe\"\n")
        f.write(") else (\n")
        f.write("    python scripts\\local_launcher.py\n")
        f.write(")\n")

    print("[✓] Arquivos Iniciar_Servidor.bat e Iniciar_Interface_Local.bat criados na raiz.")


def build_exe(script_path: Path, output_name: str, icon_path: Path | None):
    """Executa o PyInstaller para compilar um script Python em executável .exe."""
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
        "--hidden-import=qrcode",
        "--hidden-import=qrcode.constants",
        "--hidden-import=qrcode.image.base",
        "--hidden-import=colorama",
    ]

    if icon_path and icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    cmd.append(str(script_path))

    proc = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if proc.returncode != 0:
        print(f"[X] Erro ao compilar {output_name}.exe")
        return False

    # Copiar o executável gerado para a raiz do projeto para fácil acesso
    src_exe = DIST_DIR / f"{output_name}.exe"
    dst_exe = ROOT_DIR / f"{output_name}.exe"
    if src_exe.exists():
        shutil.copy2(src_exe, dst_exe)
        print(f"[✓] Executável criado e movido para: {dst_exe}")
        return True

    return False


def main():
    icon_path = ensure_icon_ico()

    # 1. Compilar RSAC_Server.exe
    server_ok = build_exe(SCRIPTS_DIR / "server_launcher.py", "RSAC_Server", icon_path)

    # 2. Compilar RSAC_Local.exe
    local_ok = build_exe(SCRIPTS_DIR / "local_launcher.py", "RSAC_Local", icon_path)

    # 3. Criar arquivos .bat auxiliares
    create_batch_launchers()

    # 4. Limpeza de diretórios temporários de build
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)

    # Remover arquivos .spec gerados
    for spec in ROOT_DIR.glob("*.spec"):
        try:
            spec.unlink()
        except Exception:
            pass

    print("\n" + "═" * 60)
    if server_ok and local_ok:
        print("🎉 SUCESSO! Ambos os executáveis foram gerados na raiz:")
        print(f"  1. 🚀 {ROOT_DIR / 'RSAC_Server.exe'}")
        print(f"  2. 💻 {ROOT_DIR / 'RSAC_Local.exe'}")
    else:
        print("⚠️ Houve falhas durante a compilação. Verifique os logs acima.")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
