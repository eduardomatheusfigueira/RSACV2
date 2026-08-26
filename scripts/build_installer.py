#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Build do Instalador Oficial Windows (.exe)

Único caminho de empacotamento do produto. Três passos, cada um com uma
responsabilidade que não se repete em lugar nenhum:

  1. PyInstaller congela o backend Python em `frontend/resources/backend/`.
  2. electron-vite compila a interface e os processos do Electron; o
     electron-builder monta o diretório do aplicativo a partir de
     `frontend/electron-builder.yml` (alvo `dir` — ele **não** gera
     instalador).
  3. o Inno Setup transforma esse diretório em `dist_bin/RSAC-Setup.exe`, a
     partir de `scripts/installer.iss`.

Nome e versão do produto saem daqui para o Inno Setup, lidos de
`frontend/package.json`. É essa passagem que impede o executável gerado no
passo 2 e o procurado no passo 3 de divergirem — divergência que, quando
acontece, produz um instalador que instala e um atalho que não abre nada.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
BACKEND_DIR = ROOT_DIR / "backend"
DIST_DIR = ROOT_DIR / "dist_bin"
SCRIPTS_DIR = ROOT_DIR / "scripts"
PACKAGE_JSON = FRONTEND_DIR / "package.json"
DEFS_FILENAME = "installer_defs.generated.iss"


def run_cmd(cmd, cwd=ROOT_DIR, desc=""):
    """Executa um passo do build, abortando tudo se ele falhar."""
    print(f"\n[*] {desc}...")
    proc = subprocess.run(cmd, cwd=str(cwd), shell=True)
    if proc.returncode != 0:
        print(f"[X] Falha na etapa: {desc}")
        sys.exit(1)


def ler_identidade_do_produto() -> tuple[str, str]:
    """
    Nome e versão do produto, do `package.json`.

    É de lá que o electron-builder os tira para nomear o executável, então é
    de lá que o instalador precisa tirá-los também. Qualquer outra cópia seria
    uma segunda verdade esperando para discordar.
    """
    dados = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    nome = dados.get("productName") or dados["name"]
    return nome, dados["version"]


def escrever_definicoes_do_inno(
    nome: str, versao: str, app_exe: Path, unpacked_dir: Path
) -> Path:
    """
    Escreve o arquivo que o `installer.iss` inclui com nome, versão e caminhos.

    Escrever em vez de passar por `/D` na linha de comando não é preciosismo:
    "RSAC V2" tem um espaço, e um valor com espaço em `/D` atravessa o shell, a
    citação do Windows e o pré-processador do Inno antes de virar uma string —
    três camadas para combinar. Aqui a string já sai entre aspas, escrita por
    quem conhece o valor.
    """
    destino = SCRIPTS_DIR / DEFS_FILENAME
    # Caminho relativo ao próprio `.iss`, e não absoluto: é a forma que o Inno
    # já usava, mantém o arquivo gerado igual em qualquer máquina e evita
    # discutir com o pré-processador sobre barras invertidas.
    origem_relativa = os.path.relpath(unpacked_dir, SCRIPTS_DIR)
    conteudo = f'''; Gerado por scripts/build_installer.py — não edite, não versione.
; Os valores vêm de frontend/package.json e do que o electron-builder produziu.
#define MyAppName "{nome}"
#define MyAppVersion "{versao}"
#define MyAppExeName "{app_exe.name}"
#define UnpackedDir "{origem_relativa}"
'''
    destino.write_text(conteudo, encoding="utf-8")
    print(f"[✓] Definições do instalador escritas em {destino.name}")
    return destino


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
    nome_do_produto, versao_do_produto = ler_identidade_do_produto()

    print("═" * 65)
    print("       🚀 GERANDO INSTALADOR OFICIAL DO RSAC V2 (.EXE)")
    print("═" * 65)
    print(f"  Produto: {nome_do_produto} — versão {versao_do_produto}")
    print(f"  Origem:  {PACKAGE_JSON.relative_to(ROOT_DIR)}")

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
        # O pandas passou a ser importado dentro de `ExportService.generate_excel`
        # para sair do caminho de arranque. O PyInstaller enxerga importação em
        # corpo de função, mas declarar aqui torna a dependência explícita e
        # imune a uma reorganização futura do módulo.
        f'--hidden-import=pandas '
        f'"{BACKEND_DIR / "run.py"}"'
    )
    run_cmd(backend_cmd, desc="Compilando backend Python em binário autônomo")

    # 2. Build do Electron Vite
    npm_bin = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    run_cmd(f'"{npm_bin}" run build', cwd=FRONTEND_DIR, desc="Compilando interface e processos Electron")

    # 3. Gerar arquivos desembalados do Electron (alvo `dir`, sem instalador)
    npx_bin = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
    run_cmd(
        f'"{npx_bin}" electron-builder --win --dir',
        cwd=FRONTEND_DIR,
        desc="Preparando pacote da aplicação",
    )

    # 4. Compilar instalador oficial com Inno Setup
    unpacked_dir = FRONTEND_DIR / "release" / "win-unpacked"
    app_exe = unpacked_dir / f"{nome_do_produto}.exe"
    if not app_exe.is_file():
        # O Inno Setup empacotaria a pasta sem reclamar e o atalho instalado
        # apontaria para um executável inexistente — falha que só apareceria na
        # máquina de quem instalou. Melhor parar aqui.
        print(f"[X] Executável esperado não foi encontrado: {app_exe}")
        print("    O nome vem de 'productName' em frontend/package.json e precisa")
        print("    coincidir com o que o electron-builder gerou. Conteúdo da pasta:")
        for item in sorted(unpacked_dir.glob("*.exe")) if unpacked_dir.is_dir() else []:
            print(f"      • {item.name}")
        sys.exit(1)

    escrever_definicoes_do_inno(nome_do_produto, versao_do_produto, app_exe, unpacked_dir)

    iscc_path = find_iscc()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    iss_file = SCRIPTS_DIR / "installer.iss"
    run_cmd(
        f'"{iscc_path}" /Qp "{iss_file}"',
        desc="Compilando instalador executável (Inno Setup)",
    )

    setup_file = DIST_DIR / "RSAC-Setup.exe"
    print("\n" + "═" * 65)
    print("🎉 SUCESSO! O instalador autônomo está pronto para distribuição:")
    print(f"  📦 {setup_file}")
    print("═" * 65 + "\n")


if __name__ == "__main__":
    main()
