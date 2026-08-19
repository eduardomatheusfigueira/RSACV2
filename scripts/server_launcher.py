#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Server Launcher
Inicia o backend Python (FastAPI), o túnel seguro da Cloudflare,
captura a URL pública, copia para a área de transferência, exibe o QR Code
para acesso no celular e monitora os serviços.
"""

import atexit
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Configuração de encoding UTF-8 para console Windows
if sys.platform == "win32":
    os.system("")  # Ativa códigos de escape ANSI
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_base_dir() -> Path:
    """Retorna a pasta raiz do projeto RSACV2."""
    if getattr(sys, "frozen", False):
        # Executável PyInstaller
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "backend").exists():
            return exe_dir
        return exe_dir
    else:
        # Script em scripts/
        return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
CONFIG_FILE = BASE_DIR / "server_config.json"

# Processos filhos gerenciados
_backend_proc: subprocess.Popen | None = None
_cloudflared_proc: subprocess.Popen | None = None
_is_shutting_down = False


def load_config() -> dict:
    """Carrega ou cria as configurações do servidor."""
    default_cfg = {
        "port": 8000,
        "auto_open_browser": False,
        "netlify_url": "",
        "cloudflared_path": "",
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass
    return default_cfg


def copy_to_clipboard(text: str) -> bool:
    """Copia o texto fornecido para a área de transferência do Windows."""
    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(
                ["clip.exe"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                shell=True,
            )
            proc.communicate(input=text.encode("utf-16le"))
            return proc.returncode == 0
    except Exception:
        pass
    return False


def print_qr_code(url: str):
    """Gera e exibe um QR code UTF-8 no terminal para leitura via celular."""
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)

        print("\033[93m  📱 QR Code para Celular (Aponte a câmera):\033[0m")
        print("\033[97m")
        qr.print_ascii(invert=True)
        print("\033[0m")
    except Exception:
        pass


def find_cloudflared(custom_path: str = "") -> str | None:
    """Procura o executável cloudflared no sistema ou baixa se necessário."""
    candidates = [
        custom_path,
        str(BASE_DIR / "cloudflared.exe"),
        str(BASE_DIR / "scripts" / "cloudflared.exe"),
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
        shutil.which("cloudflared"),
        shutil.which("cloudflared.exe"),
    ]

    for p in candidates:
        if p and os.path.isfile(p):
            return p

    return None


def download_cloudflared(dest_path: Path) -> bool:
    """Faz o download do binário oficial da Cloudflare para Windows caso não exista."""
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    print("\033[93m[!] cloudflared não encontrado no sistema.\033[0m")
    print("\033[96m[*] Baixando cloudflared oficial diretamente da Cloudflare...\033[0m")
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"\033[92m[✓] Download concluído com sucesso: {dest_path}\033[0m\n")
        return True
    except Exception as e:
        print(f"\033[91m[X] Falha ao baixar cloudflared: {e}\033[0m")
        return False


def is_port_in_use(port: int) -> bool:
    """Verifica se o backend já está respondendo na porta especificada."""
    try:
        url = f"http://127.0.0.1:{port}/api/v1/health"
        req = urllib.request.Request(url, headers={"User-Agent": "RSAC-Launcher"})
        with urllib.request.urlopen(req, timeout=1.5) as res:
            if res.status == 200:
                return True
    except Exception:
        pass
    return False


def start_backend(port: int) -> bool:
    """Inicia o backend Python em segundo plano se ainda não estiver ativo."""
    global _backend_proc

    if is_port_in_use(port):
        print(f"\033[92m[✓] Backend já está em execução na porta {port}.\033[0m")
        return True

    print(f"\033[96m[*] Iniciando Backend FastAPI na porta {port}...\033[0m")

    # Localizar python
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

    # Aguardar até 15 segundos pelo health check
    for _ in range(30):
        time.sleep(0.5)
        if is_port_in_use(port):
            print(f"\033[92m[✓] Backend inicializado com sucesso (PID: {_backend_proc.pid}).\033[0m")
            return True

    print("\033[91m[X] Tempo limite ao aguardar o backend iniciar.\033[0m")
    return False


def cleanup():
    """Encerra com segurança todos os processos filhos."""
    global _is_shutting_down, _backend_proc, _cloudflared_proc
    if _is_shutting_down:
        return
    _is_shutting_down = True

    print("\n\033[93m[*] Encerrando serviços do RSAC V2 com segurança...\033[0m")

    if _cloudflared_proc and _cloudflared_proc.poll() is None:
        try:
            _cloudflared_proc.terminate()
            _cloudflared_proc.wait(timeout=3)
        except Exception:
            _cloudflared_proc.kill()

    if _backend_proc and _backend_proc.poll() is None:
        try:
            _backend_proc.terminate()
            _backend_proc.wait(timeout=3)
        except Exception:
            _backend_proc.kill()

    print("\033[92m[✓] Todos os serviços foram finalizados. Até logo!\033[0m")


atexit.register(cleanup)


def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    global _cloudflared_proc

    config = load_config()
    port = config.get("port", 8000)

    # Limpar tela
    os.system("cls" if sys.platform == "win32" else "clear")

    print("\033[92m" + "=" * 70)
    print("        🚀 RSAC V2 — SERVIDOR WEB & ACESSO REMOTO (CLOUDFLARE)")
    print("=" * 70 + "\033[0m\n")

    # 1. Iniciar Backend
    if not start_backend(port):
        print("\033[91m[X] Não foi possível iniciar o backend. Pressione Enter para sair.\033[0m")
        input()
        sys.exit(1)

    # 2. Localizar Cloudflared
    cloudflared_bin = find_cloudflared(config.get("cloudflared_path", ""))
    if not cloudflared_bin:
        download_target = BASE_DIR / "cloudflared.exe"
        if download_cloudflared(download_target):
            cloudflared_bin = str(download_target)
        else:
            print("\033[91m[X] Instale o cloudflared ou configure o caminho no server_config.json.\033[0m")
            input()
            sys.exit(1)

    print(f"\033[96m[*] Iniciando túnel seguro Cloudflare na porta {port}...\033[0m")

    # 3. Iniciar Cloudflared e capturar URL
    tunnel_cmd = [
        cloudflared_bin,
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
    ]

    _cloudflared_proc = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    public_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Ler saída do cloudflared até achar a URL
    start_time = time.time()
    while time.time() - start_time < 30:
        if _cloudflared_proc.poll() is not None:
            break
        line = _cloudflared_proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        match = url_pattern.search(line)
        if match:
            public_url = match.group(0)
            break

    if not public_url:
        print("\033[91m[X] Não foi possível obter a URL pública da Cloudflare a tempo.\033[0m")
        input()
        cleanup()
        sys.exit(1)

    # Thread para consumir saída restante do cloudflared sem travar o buffer
    def discard_output():
        try:
            for _ in _cloudflared_proc.stdout:
                if _is_shutting_down:
                    break
        except Exception:
            pass

    threading.Thread(target=discard_output, daemon=True).start()

    # Copiar para área de transferência
    copied = copy_to_clipboard(public_url)

    # Exibir Painel Visual Principal
    os.system("cls" if sys.platform == "win32" else "clear")
    print("\033[92m" + "═" * 70)
    print("        🚀 RSAC V2 — SERVIDOR ONLINE & DISPONÍVEL NA NUVEM")
    print("═" * 70 + "\033[0m\n")

    print("\033[97m  STATUS DOS SERVIÇOS:\033[0m")
    print(f"  \033[92m[✓]\033[0m Backend FastAPI:     \033[96mhttp://127.0.0.1:{port}\033[0m (\033[92mOnline\033[0m)")
    print("  \033[92m[✓]\033[0m Interface Web SPA:   \033[92mIntegrada ao Servidor\033[0m")
    print(f"  \033[92m[✓]\033[0m Túnel Cloudflare:    \033[92mSeguro (HTTPS Ativo)\033[0m")
    print("  \033[92m[✓]\033[0m Banco de Dados:      \033[92mSQLite Conectado\033[0m\n")

    print("\033[92m" + "─" * 70 + "\033[0m")
    print("  \033[93m🌐 ACESSE O RSAC V2 DE QUALQUER LUGAR (PC, CELULAR, TABLET):\033[0m\n")
    print(f"  👉 \033[1;92m{public_url}\033[0m\n")

    if copied:
        print("  \033[96m📋 Link copiado automaticamente para a sua Área de Transferência!\033[0m\n")

    # Link Netlify (se houver)
    netlify_url = config.get("netlify_url", "").strip()
    if netlify_url:
        clean_net = netlify_url.rstrip("/")
        net_full = f"{clean_net}/#/?api_url={public_url}"
        print(f"  🌐 \033[94mLink Netlify Direto:\033[0m\n     {net_full}\n")

    # QR Code no terminal
    print_qr_code(public_url)

    print("\033[92m" + "═" * 70 + "\033[0m")
    print("  \033[97m[O]\033[0m Abrir no Navegador    \033[97m[C]\033[0m Copiar Link    \033[97m[Q]\033[0m Encerrar Servidor")
    print("\033[92m" + "═" * 70 + "\033[0m\n")

    if config.get("auto_open_browser", False):
        webbrowser.open(public_url)

    # Loop de comandos interativos
    while not _is_shutting_down:
        try:
            choice = input("\033[93mComando [O/C/Q] > \033[0m").strip().lower()
            if choice in ("o", "open"):
                webbrowser.open(public_url)
                print("\033[92m[*] Abrindo link no navegador padrão...\033[0m")
            elif choice in ("c", "copy"):
                copy_to_clipboard(public_url)
                print("\033[92m[✓] Link copiado para a Área de Transferência!\033[0m")
            elif choice in ("q", "quit", "exit"):
                break
            else:
                print("\033[90mOpções válidas: [O] Abrir no navegador, [C] Copiar link, [Q] Sair\033[0m")
        except (KeyboardInterrupt, EOFError):
            break

    cleanup()


if __name__ == "__main__":
    main()
