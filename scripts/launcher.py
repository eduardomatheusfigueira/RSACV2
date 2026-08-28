#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Launcher Principal
Inicia o backend FastAPI localmente e abre a interface em janela dedicada
de aplicativo Desktop (Chrome/Edge App Mode ou Navegador Padrão).
"""

import atexit
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Configuração UTF-8 para console Windows
if sys.platform == "win32":
    os.system("")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_base_dir() -> Path:
    """Retorna a pasta raiz do projeto RSACV2."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "backend").exists():
            return exe_dir
        return exe_dir
    else:
        return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
CONFIG_FILE = BASE_DIR / "server_config.json"

_backend_proc: subprocess.Popen | None = None
_browser_proc: subprocess.Popen | None = None
_is_shutting_down = False


def ensure_frontend_build() -> bool:
    """Garante que a interface web compilada exista antes de iniciar."""
    dist_index = FRONTEND_DIR / "dist" / "index.html"
    if dist_index.exists():
        return True

    print("\033[93m[*] Interface compilada não encontrada. Gerando build...\033[0m")
    try:
        npm_bin = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        proc = subprocess.run(
            f'"{npm_bin}" run build:web',
            cwd=str(FRONTEND_DIR),
            shell=True,
            capture_output=True,
            text=True,
        )
        if dist_index.exists():
            print("\033[92m[✓] Build concluído com sucesso!\033[0m\n")
            return True
        else:
            print(f"\033[91m[X] Falha no build do frontend:\n{proc.stderr or proc.stdout}\033[0m\n")
            return False
    except Exception as e:
        print(f"\033[91m[X] Erro ao invocar build do frontend: {e}\033[0m\n")
        return False


def is_port_in_use(port: int) -> bool:
    """Verifica se o backend já está respondendo na porta."""
    try:
        url = f"http://127.0.0.1:{port}/api/v1/health"
        req = urllib.request.Request(url, headers={"User-Agent": "Revsist-Launcher"})
        with urllib.request.urlopen(req, timeout=1.5) as res:
            if res.status == 200:
                return True
    except Exception:
        pass
    return False


def start_backend(port: int) -> bool:
    """Inicia o backend Python se necessário."""
    global _backend_proc

    if is_port_in_use(port):
        print(f"\033[92m[✓] Backend já ativo na porta {port}.\033[0m")
        return True

    print(f"\033[96m[*] Iniciando Backend FastAPI na porta {port}...\033[0m")

    python_exe = sys.executable
    if getattr(sys, "frozen", False):
        system_python = shutil.which("python") or shutil.which("python3")
        if not system_python:
            common_pythons = [
                r"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe",
                r"C:\Program Files\Python312\python.exe",
                r"C:\Python312\python.exe",
            ]
            for cp in common_pythons:
                if os.path.isfile(cp):
                    system_python = cp
                    break
        python_exe = system_python or "python"

    run_script = BACKEND_DIR / "run.py"
    if not run_script.exists():
        print(f"\033[91m[X] Arquivo backend/run.py não encontrado em {run_script}\033[0m")
        return False

    cmd = [
        python_exe,
        str(run_script),
        "--port",
        str(port),
    ]

    _backend_proc = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    for _ in range(30):
        time.sleep(0.5)
        if is_port_in_use(port):
            print(f"\033[92m[✓] Backend inicializado com sucesso (PID: {_backend_proc.pid}).\033[0m")
            return True

    print("\033[91m[X] Tempo limite ao aguardar o backend iniciar.\033[0m")
    return False


def open_app_window(url: str):
    """Abre o aplicativo em janela dedicada (estilo Desktop) via Edge ou Chrome."""
    global _browser_proc

    browsers = [
        # Microsoft Edge (nativo no Windows)
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        # Google Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]

    for browser in browsers:
        if os.path.isfile(browser):
            try:
                _browser_proc = subprocess.Popen(
                    [browser, f"--app={url}", "--window-size=1400,900"],
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                return True
            except Exception:
                pass

    # Fallback para navegador padrão
    webbrowser.open(url)
    return True


def cleanup():
    """Encerra processos filhos com segurança."""
    global _is_shutting_down, _backend_proc, _browser_proc
    if _is_shutting_down:
        return
    _is_shutting_down = True

    print("\n\033[93m[*] Encerrando Revsist...\033[0m")

    if _backend_proc and _backend_proc.poll() is None:
        try:
            _backend_proc.terminate()
            _backend_proc.wait(timeout=3)
        except Exception:
            _backend_proc.kill()

    print("\033[92m[✓] Encerrado com sucesso.\033[0m")


atexit.register(cleanup)


def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_local_token() -> str | None:
    """Lê o token local gerado pelo backend."""
    data_dir = os.getenv("RSAC_DATA_DIR")
    paths = []
    if data_dir:
        paths.append(Path(data_dir) / "runtime_token")
    if sys.platform == "win32":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            paths.append(Path(local_app_data) / "RSAC" / "runtime_token")
    paths.append(Path.home() / ".rsac" / "runtime_token")
    paths.append(BACKEND_DIR / "data" / "runtime_token")

    for p in paths:
        if p.exists():
            try:
                token = p.read_text(encoding="utf-8").strip()
                if token:
                    return token
            except Exception:
                pass
    return None


def main():
    port = 8000
    local_url = f"http://127.0.0.1:{port}"

    os.system("cls" if sys.platform == "win32" else "clear")

    print("\033[92m" + "═" * 70)
    print("        🚀 Revsist — APLICATIVO DESKTOP")
    print("═" * 70 + "\033[0m\n")

    ensure_frontend_build()

    if not start_backend(port):
        print("\033[91m[X] Falha ao iniciar o backend. Pressione Enter para sair.\033[0m")
        input()
        sys.exit(1)

    local_token = get_local_token()
    app_url = f"{local_url}?local_token={local_token}" if local_token else local_url

    print(f"\033[96m[*] Abrindo interface em janela de aplicativo ({local_url})...\033[0m")
    open_app_window(app_url)

    os.system("cls" if sys.platform == "win32" else "clear")
    print("\033[92m" + "═" * 70)
    print("        🚀 Revsist — APLICATIVO EM EXECUÇÃO")
    print("═" * 70 + "\033[0m\n")

    print(f"  \033[92m[✓]\033[0m Backend Local:    \033[96m{local_url}\033[0m (\033[92mOnline\033[0m)")
    print("  \033[92m[✓]\033[0m Interface Desktop: \033[92mAtiva em Janela Nativa\033[0m")
    print("  \033[92m[✓]\033[0m Banco de Dados:    \033[92mSQLite Conectado\033[0m\n")

    print("\033[92m" + "─" * 70 + "\033[0m")
    print("  \033[97m[O]\033[0m Abrir Novamente no Navegador    \033[97m[Q]\033[0m Encerrar Aplicativo")
    print("\033[92m" + "═" * 70 + "\033[0m\n")

    while not _is_shutting_down:
        try:
            choice = input("\033[93mComando [O/Q] > \033[0m").strip().lower()
            if choice in ("o", "open"):
                webbrowser.open(local_url)
                print("\033[92m[*] Abrindo no navegador...\033[0m")
            elif choice in ("q", "quit", "exit"):
                break
            else:
                print("\033[90mOpções válidas: [O] Abrir no navegador, [Q] Sair\033[0m")
        except (KeyboardInterrupt, EOFError):
            break

    cleanup()


if __name__ == "__main__":
    main()
